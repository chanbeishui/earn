"""SQLAlchemy ORM 模型定义"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, Date, Boolean, JSON,
    create_engine, ForeignKey, Index
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session


class Base(DeclarativeBase):
    pass


# ============ 股票基本信息 ============

class StockBasic(Base):
    """股票基本信息表"""
    __tablename__ = "stock_basic"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, comment="股票代码 如 000001.SZ")
    name: Mapped[str] = mapped_column(String(50), comment="股票名称")
    industry: Mapped[str] = mapped_column(String(100), nullable=True, comment="所属行业")
    sector: Mapped[str] = mapped_column(String(100), nullable=True, comment="所属板块")
    market: Mapped[str] = mapped_column(String(4), comment="市场 SH/SZ/BJ")
    list_date: Mapped[datetime] = mapped_column(Date, nullable=True, comment="上市日期")
    is_st: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否ST")
    is_delisted: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否退市")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<StockBasic {self.code} {self.name}>"


# ============ 财务数据 ============

class FinancialData(Base):
    """财务数据表（季报关键指标）"""
    __tablename__ = "financial_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), index=True, comment="股票代码")
    report_date: Mapped[datetime] = mapped_column(Date, index=True, comment="报告期")
    pe_ttm: Mapped[float] = mapped_column(Float, nullable=True, comment="滚动市盈率")
    pb: Mapped[float] = mapped_column(Float, nullable=True, comment="市净率")
    roe: Mapped[float] = mapped_column(Float, nullable=True, comment="净资产收益率(%)")
    revenue_yoy: Mapped[float] = mapped_column(Float, nullable=True, comment="营收同比增速(%)")
    profit_yoy: Mapped[float] = mapped_column(Float, nullable=True, comment="净利润同比增速(%)")
    dividend_yield: Mapped[float] = mapped_column(Float, nullable=True, comment="股息率(%)")
    total_market_cap: Mapped[float] = mapped_column(Float, nullable=True, comment="总市值(亿)")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_code_report", "code", "report_date", unique=True),
    )


# ============ 策略定义 ============

class StrategyDefinition(Base):
    """策略定义表 — 存储 JSON 配置的策略"""
    __tablename__ = "strategy_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, comment="策略名称")
    description: Mapped[str] = mapped_column(Text, nullable=True, comment="策略描述")
    config: Mapped[dict] = mapped_column(JSON, comment="策略JSON配置")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


# ============ 因子值缓存 ============

class FactorValue(Base):
    """每日因子值缓存表"""
    __tablename__ = "factor_values"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), index=True)
    date: Mapped[datetime] = mapped_column(Date, index=True)
    factor_name: Mapped[str] = mapped_column(String(50), index=True)
    value: Mapped[float] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_code_date_factor", "code", "date", "factor_name", unique=True),
    )


# ============ 策略选股结果 ============

class StrategyResult(Base):
    """每日策略选股结果表"""
    __tablename__ = "strategy_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(Integer, index=True, comment="策略ID")
    date: Mapped[datetime] = mapped_column(Date, index=True, comment="选股日期")
    code: Mapped[str] = mapped_column(String(20), comment="股票代码")
    score: Mapped[float] = mapped_column(Float, nullable=True, comment="综合得分")
    factor_scores: Mapped[dict] = mapped_column(JSON, nullable=True, comment="各因子得分")
    signal: Mapped[str] = mapped_column(String(20), default="hold", comment="信号: buy/sell/hold")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_strategy_date", "strategy_id", "date"),
    )


# ============ 回测任务 ============

class BacktestTask(Base):
    """回测任务表"""
    __tablename__ = "backtest_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(Integer, comment="策略ID")
    strategy_name: Mapped[str] = mapped_column(String(100), comment="策略名称（冗余）")
    config: Mapped[dict] = mapped_column(JSON, comment="回测配置快照")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="pending/running/done/failed")
    result: Mapped[dict] = mapped_column(JSON, nullable=True, comment="回测结果汇总")
    trades: Mapped[dict] = mapped_column(JSON, nullable=True, comment="交易明细")
    error_msg: Mapped[str] = mapped_column(Text, nullable=True, comment="错误信息")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_bt_status", "status"),
    )


# ============ AI 任务 ============

class AITask(Base):
    """AI 优化/训练任务表"""
    __tablename__ = "ai_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(String(20), comment="optimize/train")
    strategy_id: Mapped[int] = mapped_column(Integer, nullable=True, comment="关联策略ID")
    config: Mapped[dict] = mapped_column(JSON, comment="任务配置")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="pending/running/done/failed")
    result: Mapped[dict] = mapped_column(JSON, nullable=True, comment="结果数据")
    model_path: Mapped[str] = mapped_column(String(200), nullable=True, comment="模型文件路径")
    error_msg: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_ai_status", "status"),
    )


# ============ 自选股 ============

class WatchlistItem(Base):
    """自选股表"""
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), index=True, comment="股票代码")
    name: Mapped[str] = mapped_column(String(50), comment="股票名称（冗余）")
    tags: Mapped[str] = mapped_column(String(200), nullable=True, comment="标签，逗号分隔")
    note: Mapped[str] = mapped_column(Text, nullable=True, comment="备注")
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ============ 下载日志 ============

class DownloadLog(Base):
    """数据下载日志表"""
    __tablename__ = "download_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_type: Mapped[str] = mapped_column(String(50), comment="数据类型: daily_kline/minute_kline/financial/stock_basic")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="pending/running/done/failed")
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0, comment="总数")
    success_count: Mapped[int] = mapped_column(Integer, default=0, comment="成功数")
    error_msg: Mapped[str] = mapped_column(Text, nullable=True)


# ============ 数据库初始化 ============

def init_db(db_path: str = "data/market.db"):
    """创建数据库和所有表"""
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine) -> Session:
    """获取数据库会话"""
    return Session(engine)
