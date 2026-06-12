"""数据存储层 — SQLite + Parquet 读写"""
import os
from pathlib import Path
from datetime import datetime, date
from typing import List, Optional, Dict
import pandas as pd
from sqlalchemy import create_engine, Engine, func
from sqlalchemy.orm import Session

from .schema import (
    Base, StockBasic, FinancialData,
    StrategyDefinition, FactorValue, StrategyResult,
    BacktestTask, AITask, WatchlistItem, DownloadLog,
)
from config import StorageConfig


class DataStorage:
    """数据存储管理器"""

    def __init__(self, config: StorageConfig):
        self.config = config
        self._ensure_dirs()
        self.engine: Engine = create_engine(
            f"sqlite:///{config.db_path}", echo=False
        )
        Base.metadata.create_all(self.engine)

    def _ensure_dirs(self):
        """确保数据目录存在"""
        Path(self.config.kline_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.financial_dir).mkdir(parents=True, exist_ok=True)

    def get_session(self) -> Session:
        return Session(self.engine)

    # ====== K线数据 (Parquet) ======

    def _kline_path(self, code: str, freq: str = "daily") -> str:
        """获取某只股票的 K 线 Parquet 文件路径"""
        subdir = "daily" if freq == "daily" else f"minute_{freq}min"
        d = os.path.join(self.config.kline_dir, subdir)
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, f"{code}.parquet")

    def save_kline(self, code: str, df: pd.DataFrame, freq: str = "daily"):
        """保存一只股票的 K 线数据到 Parquet（增量合并去重）"""
        path = self._kline_path(code, freq)
        df = df.copy()
        df["code"] = code

        if os.path.exists(path):
            existing = pd.read_parquet(path)
            combined = pd.concat([existing, df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["date"], keep="last")
            combined = combined.sort_values("date")
        else:
            combined = df

        combined.to_parquet(path, index=False)

    def load_kline(self, code: str, freq: str = "daily",
                   start: Optional[str] = None, end: Optional[str] = None) -> pd.DataFrame:
        """加载一只股票的 K 线数据"""
        path = self._kline_path(code, freq)
        if not os.path.exists(path):
            return pd.DataFrame()

        df = pd.read_parquet(path)
        # 将 date 列转为 datetime 并设为索引
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
        if start:
            df = df[df.index >= start]
        if end:
            df = df[df.index <= end]
        return df

    def get_kline_date_range(self, freq: str = "daily") -> tuple:
        """获取 K 线数据的最早和最晚日期"""
        subdir = "daily" if freq == "daily" else f"minute_{freq}min"
        d = os.path.join(self.config.kline_dir, subdir)
        if not os.path.exists(d):
            return None, None

        all_dates = []
        for f in Path(d).glob("*.parquet"):
            df = pd.read_parquet(f)
            if not df.empty and "date" in df.columns:
                all_dates.append(df["date"].min())
                all_dates.append(df["date"].max())

        if not all_dates:
            return None, None
        return min(all_dates), max(all_dates)

    def get_kline_stock_count(self, freq: str = "daily") -> int:
        """获取已下载 K 线数据的股票数量"""
        subdir = "daily" if freq == "daily" else f"minute_{freq}min"
        d = os.path.join(self.config.kline_dir, subdir)
        if not os.path.exists(d):
            return 0
        return len(list(Path(d).glob("*.parquet")))

    def batch_load_kline(self, codes: List[str], date_str: str,
                         freq: str = "daily", lookback: int = 60) -> Dict[str, pd.DataFrame]:
        """批量加载多只股票指定日期附近的 K 线数据"""
        start = pd.Timestamp(date_str) - pd.Timedelta(days=lookback * 2)
        result = {}
        for code in codes:
            df = self.load_kline(code, freq, start=str(start.date()), end=date_str)
            if not df.empty:
                result[code] = df
        return result

    # ====== 股票基本信息 ======

    def save_stocks_basic(self, stocks: List[dict]):
        """批量保存股票基本信息（upsert）"""
        from datetime import date as date_type
        with self.get_session() as session:
            for s in stocks:
                # 转换 list_date 字符串为 date 对象
                clean = dict(s)
                ld = clean.get("list_date")
                if ld and isinstance(ld, str):
                    try:
                        clean["list_date"] = date_type.fromisoformat(ld)
                    except (ValueError, TypeError):
                        clean["list_date"] = None

                existing = session.query(StockBasic).filter_by(code=clean["code"]).first()
                if existing:
                    for k, v in clean.items():
                        setattr(existing, k, v)
                else:
                    session.add(StockBasic(**clean))
            session.commit()

    def get_stocks(self, exclude_st: bool = True) -> pd.DataFrame:
        """获取股票列表"""
        with self.get_session() as session:
            q = session.query(StockBasic)
            if exclude_st:
                q = q.filter(StockBasic.is_st == False)
            q = q.filter(StockBasic.is_delisted == False)
            rows = q.all()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([{
            "code": r.code, "name": r.name, "industry": r.industry,
            "market": r.market, "list_date": r.list_date
        } for r in rows])

    def get_stock_codes(self, exclude_st: bool = True) -> List[str]:
        """获取所有股票代码列表"""
        df = self.get_stocks(exclude_st)
        if df.empty:
            return []
        return df["code"].tolist()

    # ====== 财务数据 ======

    def save_financial(self, rows: List[dict]):
        """批量保存财务数据（upsert）"""
        with self.get_session() as session:
            for r in rows:
                existing = session.query(FinancialData).filter_by(
                    code=r["code"], report_date=r["report_date"]
                ).first()
                if existing:
                    for k, v in r.items():
                        setattr(existing, k, v)
                else:
                    session.add(FinancialData(**r))
            session.commit()

    def get_latest_financial(self, codes: Optional[List[str]] = None) -> pd.DataFrame:
        """获取每只股票最新一期的财务数据"""
        with self.get_session() as session:
            subq = session.query(
                FinancialData.code,
                func.max(FinancialData.report_date).label("max_date")
            ).group_by(FinancialData.code).subquery()

            q = session.query(FinancialData).join(
                subq,
                (FinancialData.code == subq.c.code) &
                (FinancialData.report_date == subq.c.max_date)
            )
            if codes:
                q = q.filter(FinancialData.code.in_(codes))
            rows = q.all()

        return pd.DataFrame([{
            "code": r.code, "report_date": r.report_date,
            "pe_ttm": r.pe_ttm, "pb": r.pb, "roe": r.roe,
            "revenue_yoy": r.revenue_yoy, "profit_yoy": r.profit_yoy,
            "dividend_yield": r.dividend_yield, "total_market_cap": r.total_market_cap,
        } for r in rows])

    # ====== 因子值 ======

    def save_factor_values(self, rows: List[dict]):
        """批量保存因子值（upsert）"""
        with self.get_session() as session:
            for r in rows:
                existing = session.query(FactorValue).filter_by(
                    code=r["code"], date=r["date"], factor_name=r["factor_name"]
                ).first()
                if existing:
                    existing.value = r["value"]
                else:
                    session.add(FactorValue(**r))
            session.commit()

    def get_factor_values(self, factor_name: str, date_str: str,
                          codes: Optional[List[str]] = None) -> pd.DataFrame:
        """获取某日某因子的值"""
        with self.get_session() as session:
            q = session.query(FactorValue).filter_by(
                factor_name=factor_name, date=date_str
            )
            if codes:
                q = q.filter(FactorValue.code.in_(codes))
            rows = q.all()
        return pd.DataFrame([{"code": r.code, "value": r.value} for r in rows])

    # ====== 策略 ======

    def strategy_crud(self):
        """返回策略 CRUD 操作对象"""
        return _StrategyCRUD(self)

    # ====== 下载日志 ======

    def create_download_log(self, data_type: str) -> int:
        """创建下载日志，返回日志ID"""
        with self.get_session() as session:
            log = DownloadLog(data_type=data_type, status="running")
            session.add(log)
            session.commit()
            return log.id

    def update_download_log(self, log_id: int, status: str,
                            total: int = 0, success: int = 0, error: str = None):
        """更新下载日志"""
        with self.get_session() as session:
            log = session.query(DownloadLog).filter_by(id=log_id).first()
            if log:
                log.status = status
                log.total_count = total
                log.success_count = success
                if error:
                    log.error_msg = error
                if status in ("done", "failed"):
                    log.end_time = datetime.now()
                session.commit()

    def get_download_logs(self, limit: int = 50) -> list:
        """获取最近下载日志"""
        with self.get_session() as session:
            logs = session.query(DownloadLog).order_by(
                DownloadLog.start_time.desc()
            ).limit(limit).all()
            return [{
                "id": l.id, "data_type": l.data_type, "status": l.status,
                "start_time": l.start_time, "end_time": l.end_time,
                "total_count": l.total_count, "success_count": l.success_count,
                "error_msg": l.error_msg
            } for l in logs]

    # ====== 数据概览 ======

    def get_overview(self) -> dict:
        """获取数据概览统计"""
        daily_start, daily_end = self.get_kline_date_range("daily")
        stock_count = self.get_kline_stock_count("daily")

        with self.get_session() as session:
            db_size = os.path.getsize(self.config.db_path) if os.path.exists(self.config.db_path) else 0
            strategy_count = session.query(StrategyDefinition).count()
            last_download = session.query(DownloadLog).order_by(
                DownloadLog.start_time.desc()
            ).first()

        total_size = db_size
        kline_dir = os.path.join(self.config.kline_dir, "daily")
        if os.path.exists(kline_dir):
            for f in Path(kline_dir).glob("*.parquet"):
                total_size += os.path.getsize(f)

        return {
            "stock_count": stock_count,
            "daily_start": str(daily_start) if daily_start else None,
            "daily_end": str(daily_end) if daily_end else None,
            "strategy_count": strategy_count,
            "data_size_mb": round(total_size / 1024 / 1024, 2),
            "last_download": last_download.start_time.isoformat() if last_download else None,
        }


class _StrategyCRUD:
    """策略 CRUD 操作（内部类，通过 DataStorage.strategy_crud() 访问）"""

    def __init__(self, storage: DataStorage):
        self.storage = storage

    def list(self) -> list:
        with self.storage.get_session() as session:
            rows = session.query(StrategyDefinition).order_by(
                StrategyDefinition.updated_at.desc()
            ).all()
            return [{
                "id": r.id, "name": r.name, "description": r.description,
                "config": r.config, "is_enabled": r.is_enabled,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            } for r in rows]

    def get(self, strategy_id: int) -> Optional[dict]:
        with self.storage.get_session() as session:
            r = session.query(StrategyDefinition).filter_by(id=strategy_id).first()
            if not r:
                return None
            return {
                "id": r.id, "name": r.name, "description": r.description,
                "config": r.config, "is_enabled": r.is_enabled,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }

    def create(self, name: str, config: dict, description: str = "") -> int:
        with self.storage.get_session() as session:
            s = StrategyDefinition(
                name=name, description=description, config=config
            )
            session.add(s)
            session.commit()
            return s.id

    def update(self, strategy_id: int, **kwargs) -> bool:
        with self.storage.get_session() as session:
            s = session.query(StrategyDefinition).filter_by(id=strategy_id).first()
            if not s:
                return False
            for k, v in kwargs.items():
                if hasattr(s, k):
                    setattr(s, k, v)
            s.updated_at = datetime.now()
            session.commit()
            return True

    def delete(self, strategy_id: int) -> bool:
        with self.storage.get_session() as session:
            s = session.query(StrategyDefinition).filter_by(id=strategy_id).first()
            if not s:
                return False
            session.delete(s)
            session.commit()
            return True

    def toggle(self, strategy_id: int) -> Optional[bool]:
        """切换启用状态，返回新状态"""
        with self.storage.get_session() as session:
            s = session.query(StrategyDefinition).filter_by(id=strategy_id).first()
            if not s:
                return None
            s.is_enabled = not s.is_enabled
            s.updated_at = datetime.now()
            session.commit()
            return s.is_enabled

    def save_results(self, strategy_id: int, date_str: str, results: list):
        """保存策略选股结果"""
        from datetime import date as date_type
        dt = date_type.fromisoformat(date_str) if isinstance(date_str, str) else date_str
        with self.storage.get_session() as session:
            # 先删除当天的旧结果
            session.query(StrategyResult).filter_by(
                strategy_id=strategy_id, date=dt
            ).delete()
            # 插入新结果
            for r in results:
                session.add(StrategyResult(
                    strategy_id=strategy_id, date=dt,
                    code=r["code"], score=r.get("score"),
                    factor_scores=r.get("factor_scores"),
                    signal=r.get("signal", "hold"),
                ))
            session.commit()

    def get_results(self, strategy_id: int, date_str: str = None) -> list:
        """获取策略选股结果"""
        from datetime import date as date_type
        with self.storage.get_session() as session:
            q = session.query(StrategyResult).filter_by(strategy_id=strategy_id)
            if date_str:
                dt = date_type.fromisoformat(date_str) if isinstance(date_str, str) else date_str
                q = q.filter_by(date=dt)
            else:
                # 最新日期
                latest = session.query(func.max(StrategyResult.date)).filter_by(
                    strategy_id=strategy_id
                ).scalar()
                if latest:
                    q = q.filter_by(date=latest)
            rows = q.order_by(StrategyResult.score.desc()).all()
            return [{
                "code": r.code, "score": r.score,
                "factor_scores": r.factor_scores,
                "signal": r.signal, "date": str(r.date),
            } for r in rows]
