"""策略选股池"""
from typing import List, Set, Optional
from datetime import datetime
from data.storage import DataStorage


class StrategyPool:
    """策略选股结果管理"""

    def __init__(self, storage: DataStorage):
        self.storage = storage

    def get_results(self, strategy_id: Optional[int] = None,
                    date_str: Optional[str] = None) -> List[dict]:
        """获取策略选股结果"""
        crud = self.storage.strategy_crud()

        if strategy_id:
            return crud.get_results(strategy_id, date_str)
        else:
            # 所有已启用策略的最新结果
            all_strategies = crud.list()
            results = []
            for s in all_strategies:
                if s.get("is_enabled"):
                    r = crud.get_results(s["id"], date_str)
                    for item in r:
                        item["strategy_name"] = s["name"]
                        item["strategy_id"] = s["id"]
                    results.extend(r)
            return results

    def get_all_enabled_codes(self, date_str: Optional[str] = None) -> Set[str]:
        """获取所有启用策略的选股并集"""
        results = self.get_results(strategy_id=None, date_str=date_str)
        return {r["code"] for r in results}

    def get_dates(self, strategy_id: int) -> List[str]:
        """获取某策略的所有选股日期"""
        crud = self.storage.strategy_crud()
        results = crud.get_results(strategy_id)
        dates = sorted(set(r.get("date", "0") for r in results), reverse=True)
        return dates
