"""股票池管理器 — 统一管理所有股票池"""
from typing import List, Dict, Optional, Set
import pandas as pd
from datetime import datetime

from .strategy_pool import StrategyPool
from .watchlist import Watchlist
from data.storage import DataStorage


class PoolManager:
    """股票池统一管理器"""

    def __init__(self, storage: DataStorage):
        self.storage = storage
        self.strategy_pool = StrategyPool(storage)
        self.watchlist = Watchlist(storage)

    # ====== 策略选股池 ======

    def get_strategy_results(self, strategy_id: Optional[int] = None,
                             date_str: Optional[str] = None) -> List[dict]:
        """获取策略选股结果"""
        return self.strategy_pool.get_results(strategy_id, date_str)

    def get_strategy_pool_codes(self, strategy_id: int,
                                date_str: Optional[str] = None) -> Set[str]:
        """获取策略选股池的股票代码集合"""
        results = self.strategy_pool.get_results(strategy_id, date_str)
        return {r["code"] for r in results}

    def get_all_strategy_pool_codes(self, date_str: Optional[str] = None) -> Set[str]:
        """获取所有已启用策略的选股并集"""
        return self.strategy_pool.get_all_enabled_codes(date_str)

    def get_strategy_pool_df(self, strategy_id: int,
                             date_str: Optional[str] = None) -> pd.DataFrame:
        """获取策略选股池 DataFrame（含得分详情）"""
        results = self.strategy_pool.get_results(strategy_id, date_str)
        if not results:
            return pd.DataFrame()
        return pd.DataFrame(results)

    # ====== 自选股 ======

    def get_watchlist(self) -> pd.DataFrame:
        """获取自选股"""
        return self.watchlist.get_all()

    def add_to_watchlist(self, code: str, name: str = "",
                         tags: str = "", note: str = "") -> int:
        """手动添加自选股"""
        return self.watchlist.add(code, name, tags, note)

    def update_watchlist_item(self, item_id: int, **kwargs) -> bool:
        """更新自选股"""
        return self.watchlist.update(item_id, **kwargs)

    def remove_from_watchlist(self, item_id: int) -> bool:
        """删除自选股"""
        return self.watchlist.delete(item_id)

    def add_batch_to_watchlist(self, codes: List[dict], tag: str = ""):
        """批量添加自选股（从策略选股结果）"""
        for c in codes:
            existing = self.watchlist.find_by_code(c["code"])
            if not existing:
                tags = tag
                if tags:
                    tags += ",imported"
                else:
                    tags = "imported"
                self.watchlist.add(c["code"], c.get("name", ""), tags)

    def get_watchlist_codes(self) -> Set[str]:
        """获取自选股代码集合"""
        wl = self.watchlist.get_all()
        if wl.empty:
            return set()
        return set(wl["code"].tolist())

    # ====== 池操作 ======

    def pool_intersection(self, strategy_id: int,
                          date_str: Optional[str] = None) -> List[dict]:
        """选股池 ∩ 自选池"""
        strategy_codes = self.get_strategy_pool_codes(strategy_id, date_str)
        watchlist_codes = self.get_watchlist_codes()
        intersection = strategy_codes & watchlist_codes

        results = self.strategy_pool.get_results(strategy_id, date_str)
        return [r for r in results if r["code"] in intersection]

    def pool_union(self, strategy_id: int,
                   date_str: Optional[str] = None) -> List[dict]:
        """选股池 ∪ 自选池"""
        strategy_codes = self.get_strategy_pool_codes(strategy_id, date_str)
        watchlist_codes = self.get_watchlist_codes()
        union = strategy_codes | watchlist_codes

        results = self.strategy_pool.get_results(strategy_id, date_str)
        result_codes = {r["code"] for r in results}
        union_results = [r for r in results if r["code"] in union]

        # 自选股中不在策略结果中的
        wl = self.watchlist.get_all()
        if not wl.empty:
            for _, row in wl.iterrows():
                if row["code"] not in result_codes and row["code"] in union:
                    union_results.append({
                        "code": row["code"], "score": 0,
                        "signal": "hold", "source": "watchlist",
                    })
        return union_results

    def pool_difference(self, strategy_id: int,
                        date_str: Optional[str] = None) -> List[dict]:
        """选股池 - 自选池（仅在策略选中的不在自选中的）"""
        strategy_codes = self.get_strategy_pool_codes(strategy_id, date_str)
        watchlist_codes = self.get_watchlist_codes()
        diff = strategy_codes - watchlist_codes

        results = self.strategy_pool.get_results(strategy_id, date_str)
        return [r for r in results if r["code"] in diff]

    # ====== 标签管理 ======

    def get_all_tags(self) -> List[str]:
        """获取所有已使用的标签"""
        return self.watchlist.get_all_tags()

    def add_tag(self, item_id: int, tag: str) -> bool:
        """给自选股添加标签"""
        item = self.watchlist.get(item_id)
        if item is None:
            return False
        current = item.get("tags", "")
        if current:
            tags = set(t.strip() for t in current.split(",") if t.strip())
        else:
            tags = set()
        tags.add(tag)
        return self.watchlist.update(item_id, tags=",".join(sorted(tags)))

    def remove_tag(self, item_id: int, tag: str) -> bool:
        """移除标签"""
        item = self.watchlist.get(item_id)
        if item is None:
            return False
        current = item.get("tags", "")
        tags = set(t.strip() for t in current.split(",") if t.strip())
        tags.discard(tag)
        return self.watchlist.update(item_id, tags=",".join(sorted(tags)))

    # ====== 导出 ======

    def export_watchlist_csv(self) -> str:
        """导出自选股为 CSV 字符串"""
        df = self.watchlist.get_all()
        if df.empty:
            return "code,name,tags\n"
        return df.to_csv(index=False)

    def sync_to_qmt(self):
        """同步自选股到 QMT 客户端（需要 QMT 运行时）"""
        # QMT 自选板块同步 (API: xtdata.add_self_sector)
        try:
            from xtquant import xtdata
            codes = list(self.get_watchlist_codes())
            # 创建/更新自选板块
            xtdata.add_self_sector("earn_watchlist", codes)
            return True, f"已同步 {len(codes)} 只自选股到 QMT"
        except ImportError:
            return False, "QMT xtquant 未安装"
        except Exception as e:
            return False, str(e)
