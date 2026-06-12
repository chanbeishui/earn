"""自选股管理"""
from typing import List, Optional, Dict
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session
from data.schema import WatchlistItem
from data.storage import DataStorage


class Watchlist:
    """自选股 CRUD"""

    def __init__(self, storage: DataStorage):
        self.storage = storage

    def get_all(self) -> pd.DataFrame:
        """获取所有自选股"""
        with self.storage.get_session() as session:
            rows = session.query(WatchlistItem).order_by(
                WatchlistItem.added_at.desc()
            ).all()

        if not rows:
            return pd.DataFrame(columns=["id", "code", "name", "tags", "note", "added_at"])

        return pd.DataFrame([{
            "id": r.id, "code": r.code, "name": r.name,
            "tags": r.tags, "note": r.note,
            "added_at": r.added_at.strftime("%Y-%m-%d %H:%M") if r.added_at else "",
        } for r in rows])

    def get(self, item_id: int) -> Optional[dict]:
        """获取单个自选股"""
        with self.storage.get_session() as session:
            r = session.query(WatchlistItem).filter_by(id=item_id).first()
            if not r:
                return None
            return {"id": r.id, "code": r.code, "name": r.name,
                    "tags": r.tags, "note": r.note}

    def find_by_code(self, code: str) -> Optional[dict]:
        """按代码查找"""
        with self.storage.get_session() as session:
            r = session.query(WatchlistItem).filter_by(code=code).first()
            if not r:
                return None
            return {"id": r.id, "code": r.code, "name": r.name,
                    "tags": r.tags, "note": r.note}

    def add(self, code: str, name: str = "",
            tags: str = "", note: str = "") -> int:
        """添加自选股"""
        with self.storage.get_session() as session:
            # 去重
            existing = session.query(WatchlistItem).filter_by(code=code).first()
            if existing:
                return existing.id

            item = WatchlistItem(
                code=code, name=name, tags=tags, note=note
            )
            session.add(item)
            session.commit()
            return item.id

    def update(self, item_id: int, **kwargs) -> bool:
        """更新自选股"""
        with self.storage.get_session() as session:
            r = session.query(WatchlistItem).filter_by(id=item_id).first()
            if not r:
                return False
            for k, v in kwargs.items():
                if hasattr(r, k):
                    setattr(r, k, v)
            session.commit()
            return True

    def delete(self, item_id: int) -> bool:
        """删除自选股"""
        with self.storage.get_session() as session:
            r = session.query(WatchlistItem).filter_by(id=item_id).first()
            if not r:
                return False
            session.delete(r)
            session.commit()
            return True

    def get_all_tags(self) -> List[str]:
        """获取所有已使用的标签"""
        df = self.get_all()
        if df.empty:
            return []
        all_tags = set()
        for tags_str in df["tags"].dropna():
            for t in tags_str.split(","):
                t = t.strip()
                if t:
                    all_tags.add(t)
        return sorted(all_tags)

    def get_by_tag(self, tag: str) -> pd.DataFrame:
        """按标签筛选"""
        df = self.get_all()
        if df.empty:
            return df
        return df[df["tags"].str.contains(tag, na=False)]

    def search(self, keyword: str) -> pd.DataFrame:
        """搜索（按代码或名称模糊匹配）"""
        df = self.get_all()
        if df.empty or not keyword:
            return df
        kw = keyword.lower()
        mask = df["code"].str.lower().str.contains(kw, na=False) | \
               df["name"].str.lower().str.contains(kw, na=False)
        return df[mask]
