"""综合选股器 — 执行策略选股并汇总结果"""
from typing import List, Optional
from datetime import datetime, timedelta
import pandas as pd

from .config_strategy import ConfigStrategy
from data.storage import DataStorage


class StockSelector:
    """综合选股器"""

    def __init__(self, storage: DataStorage):
        self.storage = storage

    def run_strategy(self, strategy_id: int, date_str: Optional[str] = None) -> List[dict]:
        """
        运行单个策略选股
        :param strategy_id: 策略 ID
        :param date_str: 选股日期（默认最近交易日）
        :return: 选股结果列表
        """
        # 获取策略定义
        crud = self.storage.strategy_crud()
        strategy_data = crud.get(strategy_id)
        if not strategy_data:
            print(f"[StockSelector] 策略 {strategy_id} 不存在")
            return []

        if not strategy_data.get("is_enabled"):
            print(f"[StockSelector] 策略 {strategy_id} 已停用")
            return []

        config = strategy_data.get("config", {})
        strategy = ConfigStrategy(config, storage=self.storage)

        # 获取候选池
        stock_codes = self.storage.get_stock_codes(exclude_st=True)
        if not stock_codes:
            return []

        # 默认选股日期
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        # 执行选股
        results = strategy.select_stocks(stock_codes, date_str)

        # 保存结果
        crud.save_results(strategy_id, date_str, results)

        return results

    def run_all_enabled(self, date_str: Optional[str] = None) -> List[dict]:
        """运行所有已启用策略"""
        crud = self.storage.strategy_crud()
        all_strategies = crud.list()
        enabled = [s for s in all_strategies if s.get("is_enabled")]

        all_results = []
        for s in enabled:
            results = self.run_strategy(s["id"], date_str)
            for r in results:
                r["strategy_id"] = s["id"]
                r["strategy_name"] = s["name"]
            all_results.extend(results)

        return all_results

    def get_latest_results(self, strategy_id: int) -> List[dict]:
        """获取最新选股结果"""
        crud = self.storage.strategy_crud()
        return crud.get_results(strategy_id)
