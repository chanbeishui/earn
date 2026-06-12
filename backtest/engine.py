"""事件驱动回测引擎"""
from typing import Dict, List, Optional, Callable
from collections import defaultdict
from datetime import datetime
import pandas as pd
import numpy as np

from .broker import Broker, BrokerConfig, Order, Fill
from .portfolio import Portfolio
from .analyzer import Analyzer
from data.storage import DataStorage
from strategy.config_strategy import ConfigStrategy
from strategy.factors.manager import FactorManager


class BacktestEngine:
    """事件驱动回测引擎"""

    def __init__(self, config: dict, storage: DataStorage):
        """
        :param config: 回测配置
            - start_date, end_date
            - initial_capital, commission, stamp_duty
            - benchmark (如 000300.SH)
        :param storage: DataStorage 实例
        """
        self.config = config
        self.storage = storage

        # 券商
        broker_cfg = BrokerConfig(
            commission_rate=config.get("commission", 0.00025),
            stamp_duty_rate=config.get("stamp_duty", 0.001),
            slippage=config.get("slippage", 0.0001),
        )
        self.broker = Broker(broker_cfg)

        # 组合
        self.portfolio = Portfolio(config.get("initial_capital", 1_000_000))

        # 基准
        self.benchmark_code = config.get("benchmark", "000300.SH")

        # 状态
        self.trades: List[dict] = []
        self.daily_signals: List[dict] = []
        self._strategy = None
        self._stock_codes = []
        self._kline_cache: Dict[str, pd.DataFrame] = {}

    def load_strategy(self, strategy_config: dict):
        """加载策略"""
        self._strategy = ConfigStrategy(strategy_config, storage=self.storage)

    def load_strategy_by_id(self, strategy_id: int):
        """从数据库加载策略"""
        crud = self.storage.strategy_crud()
        sd = crud.get(strategy_id)
        if not sd:
            raise ValueError(f"策略 {strategy_id} 不存在")
        self.load_strategy(sd["config"])

    def set_stock_pool(self, codes: List[str]):
        """设置候选股池"""
        self._stock_codes = codes

    def run(self, progress_callback: Optional[Callable] = None) -> dict:
        """
        运行回测
        :param progress_callback: 进度回调 (current, total, date_str)
        :return: 回测结果 dict
        """
        if self._strategy is None:
            raise ValueError("请先调用 load_strategy()")

        sdate = self.config["start_date"]
        edate = self.config["end_date"]

        # 1. 获取股票池
        if not self._stock_codes:
            self._stock_codes = self.storage.get_stock_codes(exclude_st=True)

        # 2. 预加载所有 K 线数据
        self._preload_kline(sdate, edate)

        # 3. 获取交易日列表
        if not self._stock_codes:
            return self._empty_result("没有可交易的股票")

        # 用第一只股票的日期作为交易日历
        first_code = self._stock_codes[0]
        if first_code not in self._kline_cache:
            return self._empty_result("没有K线数据")

        trade_dates = self._kline_cache[first_code].index
        trade_dates = trade_dates[(trade_dates >= sdate) & (trade_dates <= edate)]
        total_days = len(trade_dates)

        # 4. 事件驱动主循环
        for i, date_obj in enumerate(trade_dates):
            date_str = date_obj.strftime("%Y-%m-%d")

            # 获取当天行情快照
            snapshot = self._get_snapshot(date_obj)

            # === 卖出流程 ===
            self._process_sells(snapshot, date_str)

            # === 买入流程 ===
            self._process_buys(snapshot, date_str)

            # === 更新持仓市值 ===
            prices = {code: snap.get("close", 0) for code, snap in snapshot.items()}
            if self.portfolio.get_available_codes():
                self.portfolio.update_market_prices(prices)

            # 记录快照
            self.portfolio.snapshot(date_str)

            if progress_callback and i % 10 == 0:
                progress_callback(i + 1, total_days, date_str)

        # 5. 分析结果
        result = self._analyze()
        result["trades"] = self.trades
        return result

    def _preload_kline(self, sdate: str, edate: str):
        """预加载所有股票的 K 线"""
        lookback = (pd.Timestamp(sdate) - pd.Timedelta(days=365)).strftime("%Y-%m-%d")
        for code in self._stock_codes:
            df = self.storage.load_kline(code, freq="daily", start=lookback, end=edate)
            if not df.empty:
                self._kline_cache[code] = df

    def _get_snapshot(self, date_obj: pd.Timestamp) -> dict:
        """获取当天所有股票的行情快照 {code: {open, high, low, close, volume}}"""
        snapshot = {}
        for code in self._stock_codes:
            if code not in self._kline_cache:
                continue
            df = self._kline_cache[code]
            if date_obj not in df.index:
                continue
            row = df.loc[date_obj]
            snapshot[code] = {
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
                "amount": float(row.get("amount", 0)),
            }
        return snapshot

    def _process_sells(self, snapshot: dict, date_str: str):
        """处理卖出"""
        held = list(self.portfolio.positions.keys())
        for code in held:
            if code not in snapshot:
                continue

            df = self._kline_cache.get(code)
            if df is None:
                continue

            # 检查卖出信号
            sell_signals = self._strategy.sell_signals if self._strategy else []
            should_sell = False

            for sig in sell_signals:
                if sig.type == "stop_loss":
                    # 止损：计算持仓盈亏
                    pos = self.portfolio.positions.get(code)
                    if pos:
                        current = snapshot[code]["close"]
                        pnl_pct = (current - pos.avg_cost) / pos.avg_cost * 100
                        percent = sig.params.get("percent", -8)
                        if pnl_pct <= percent:
                            should_sell = True
                elif sig.type == "take_profit":
                    pos = self.portfolio.positions.get(code)
                    if pos:
                        current = snapshot[code]["close"]
                        pnl_pct = (current - pos.avg_cost) / pos.avg_cost * 100
                        percent = sig.params.get("percent", 20)
                        if pnl_pct >= percent:
                            should_sell = True
                else:
                    # 技术信号
                    date_idx = self._get_date_idx(df, date_str)
                    if date_idx >= 0 and sig.check(df, date_idx):
                        should_sell = True

            if should_sell:
                pos = self.portfolio.positions.get(code)
                if pos:
                    bar = snapshot[code]
                    order = Order(
                        code=code, direction="sell", price=bar["open"],
                        volume=pos.volume, date=date_str
                    )
                    fill = self.broker.execute_order(order, bar)
                    if fill:
                        self.portfolio.apply_fill(fill, date_str)
                        self.trades.append({
                            "date": date_str, "code": code, "direction": "sell",
                            "price": fill.price, "volume": fill.volume,
                            "amount": fill.amount, "commission": fill.commission,
                            "stamp_duty": fill.stamp_duty,
                        })

    def _process_buys(self, snapshot: dict, date_str: str):
        """处理买入 — 每日选股"""
        # 计算选股
        available_codes = [c for c in self._stock_codes if c in snapshot]
        if not available_codes:
            return

        # 选股（用策略打分）
        selections = self._strategy.select_stocks(available_codes, date_str)
        scores = {s["code"]: s["score"] for s in selections}

        # 按得分排序，买 TOP N
        max_stocks = self._strategy.position_rule.get("max_stocks", 10)
        buy_candidates = sorted(selections, key=lambda x: x["score"], reverse=True)

        # 已持仓的不再买
        held = set(self.portfolio.get_available_codes())
        to_buy = [s for s in buy_candidates if s["code"] not in held]

        # 计算可买数量
        slots = max_stocks - len(held)
        if slots <= 0:
            return

        for s in to_buy[:slots]:
            code = s["code"]
            bar = snapshot[code]
            price = bar["open"]

            # 等权分配
            available_cash = self.portfolio.cash / max(slots, 1)
            volume = int(available_cash / price / 100) * 100
            if volume < 100:
                continue

            # 检查资金
            if not self.portfolio.can_buy(price, volume):
                continue

            order = Order(
                code=code, direction="buy", price=price,
                volume=volume, date=date_str
            )
            fill = self.broker.execute_order(order, bar)
            if fill:
                self.portfolio.apply_fill(fill, date_str)
                self.trades.append({
                    "date": date_str, "code": code, "direction": "buy",
                    "price": fill.price, "volume": fill.volume,
                    "amount": fill.amount, "commission": fill.commission,
                    "stamp_duty": 0,
                    "score": s.get("score"),
                })
                slots -= 1
                if slots <= 0:
                    break

    def _get_date_idx(self, df: pd.DataFrame, date_str: str) -> int:
        """获取 DataFrame 中指定日期的位置索引"""
        try:
            dt = pd.Timestamp(date_str)
            if dt in df.index:
                return list(df.index).index(dt)
        except Exception:
            pass
        return -1

    def _analyze(self) -> dict:
        """分析回测结果"""
        df = self.portfolio.get_history_df()
        if df.empty:
            return self._empty_result("没有交易记录")

        # 基准收益
        bench_return = 0.0
        bench_df = self.storage.load_kline(self.benchmark_code, freq="daily",
                                            start=df.index[0].strftime("%Y-%m-%d"),
                                            end=df.index[-1].strftime("%Y-%m-%d"))
        if not bench_df.empty:
            bench_start = bench_df["close"].iloc[0]
            bench_end = bench_df["close"].iloc[-1]
            if bench_start > 0:
                bench_return = (bench_end - bench_start) / bench_start * 100

        analyzer = Analyzer(df, self.portfolio, self.trades)
        return analyzer.analyze(bench_return)

    def _empty_result(self, msg: str = "无数据") -> dict:
        return {
            "error": msg,
            "summary": {},
            "trades": [],
            "daily_returns": [],
        }
