"""配置驱动策略引擎 — 读取 JSON 定义，动态组合因子+择时+过滤器+仓位"""
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
import numpy as np

from .factors.manager import FactorManager
from .timing.manager import TimingManager
from .base import Strategy


class ConfigStrategy(Strategy):
    """
    配置驱动策略
    从 JSON 配置动态构建可执行策略，支持：
    - 多因子加权打分
    - 多条件择时信号
    - 股票过滤器
    - 仓位分配规则
    """

    def __init__(self, config: dict, storage=None):
        """
        :param config: 策略 JSON 配置
        :param storage: DataStorage 实例（用于访问数据库）
        """
        self.config = config
        self.name = config.get("name", "未命名策略")
        self.description = config.get("description", "")
        self.storage = storage

        # 构建因子列表
        self.factors = []
        for fc in config.get("factors", []):
            f = FactorManager.create(fc["name"], **fc.get("params", {}))
            if f:
                self.factors.append({
                    "factor": f,
                    "weight": fc.get("weight", 0),
                    "name": fc["name"],
                })

        # 构建择时信号
        timing = config.get("timing", {})
        self.buy_signals = TimingManager.create_signals(
            timing.get("buy_signals", [])
        )
        self.sell_signals = TimingManager.create_signals(
            timing.get("sell_signals", [])
        )

        # 过滤器
        self.filters = config.get("filters", [])

        # 仓位规则
        self.position_rule = config.get("position", {"type": "equal_weight", "max_stocks": 10})

        # 状态
        self._factor_cache: Dict[str, pd.DataFrame] = {}

    def select_stocks(self, stock_codes: List[str], date_str: str,
                      lookback: int = 120) -> List[dict]:
        """
        执行选股
        :param stock_codes: 候选股票代码列表
        :param date_str: 选股日期
        :param lookback: 计算因子回溯天数
        :return: 选股结果列表 [{code, score, factor_scores, signal, ...}]
        """
        if not self.storage:
            return []

        results = []
        # 批量加载 K 线
        kline_dict = self.storage.batch_load_kline(
            stock_codes, date_str, freq="daily", lookback=lookback
        )

        # 加载财务数据
        financial_df = self.storage.get_latest_financial(stock_codes)

        for code in stock_codes:
            if code not in kline_dict:
                continue

            df = kline_dict[code]
            if df.empty or len(df) < 20:
                continue

            # 1. 应用过滤器
            if not self._pass_filters(code, df, financial_df):
                continue

            # 2. 计算各因子得分
            code_fin = financial_df[financial_df["code"] == code] if not financial_df.empty else pd.DataFrame()
            factor_scores = {}
            total_score = 0
            total_weight = 0

            for fw in self.factors:
                factor = fw["factor"]
                weight = fw["weight"]
                if weight == 0:
                    continue

                try:
                    val = factor.get_value(df, date_str, financial_df=code_fin)
                    if np.isnan(val):
                        continue
                    factor_scores[fw["name"]] = val
                    # 对于越低越好的因子(PE/PB)，取倒数
                    if fw["name"] in ("pe_ttm", "pb"):
                        val = -val
                    total_score += val * weight
                    total_weight += abs(weight)
                except Exception as e:
                    continue

            if total_weight == 0:
                continue

            # 归一化得分
            final_score = total_score / total_weight

            # 3. 确定信号
            signal = "hold"
            if self.buy_signals:
                if any(s.check(df) for s in self.buy_signals):
                    signal = "buy"
            if self.sell_signals:
                if any(s.check(df) for s in self.sell_signals):
                    signal = "sell"

            results.append({
                "code": code,
                "score": round(final_score, 4),
                "factor_scores": {k: round(v, 4) for k, v in factor_scores.items()},
                "signal": signal,
            })

        # 4. 按得分排序
        results.sort(key=lambda x: x["score"], reverse=True)

        # 5. 应用仓位规则
        max_stocks = self.position_rule.get("max_stocks", 10)
        results = results[:max_stocks]

        return results

    def _pass_filters(self, code: str, df: pd.DataFrame,
                      financial_df: pd.DataFrame) -> bool:
        """检查是否通过所有过滤器"""
        for f in self.filters:
            ftype = f.get("type", "")
            params = f.get("params", {})

            if ftype == "exclude_st":
                # 通过股票名称判断（简化）
                if self.storage:
                    stocks_df = self.storage.get_stocks()
                    if not stocks_df.empty:
                        match = stocks_df[stocks_df["code"] == code]
                        if not match.empty:
                            name = match.iloc[0].get("name", "")
                            if "ST" in name:
                                return False

            elif ftype == "market_cap_min":
                min_cap = float(params.get("value", 50))
                if not financial_df.empty:
                    fin = financial_df[financial_df["code"] == code]
                    if not fin.empty:
                        cap = fin.iloc[0].get("total_market_cap", 0)
                        if cap and cap < min_cap:
                            return False

            elif ftype == "volume_min":
                min_vol = float(params.get("value", 1000))
                avg_amount = df["amount"].tail(20).mean()
                if avg_amount < min_vol * 10000:  # 万元转元
                    return False

            elif ftype == "price_min":
                min_price = float(params.get("value", 3.0))
                last_close = df["close"].iloc[-1]
                if last_close < min_price:
                    return False

        return True

    def to_dict(self) -> dict:
        """导出为可存储的字典"""
        return {
            "name": self.name,
            "description": self.description,
            "config": self.config,
        }
