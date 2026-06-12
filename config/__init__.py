import os
from pathlib import Path
from dotenv import load_dotenv
import yaml
from pydantic import BaseModel
from typing import List, Optional


class QMTConfig(BaseModel):
    data_dir: str
    account_id: str = ""


class StorageConfig(BaseModel):
    db_path: str = "data/market.db"
    kline_dir: str = "data/kline"
    financial_dir: str = "data/financial"


class DownloadConfig(BaseModel):
    daily_kline: bool = True
    minute_freqs: List[int] = [1, 5, 15, 30, 60]
    minute_years: int = 3
    financial: bool = True


class StrategyConfig(BaseModel):
    enabled: List[str] = []
    stock_pool: str = "000300.SH"


class BacktestConfig(BaseModel):
    start_date: str = "2020-01-01"
    end_date: str = "2025-12-31"
    initial_capital: float = 1_000_000
    commission: float = 0.00025
    stamp_duty: float = 0.001
    benchmark: str = "000300.SH"


class AIOptimizerConfig(BaseModel):
    method: str = "optuna"
    n_trials: int = 500


class AIPredictorConfig(BaseModel):
    model: str = "lstm"
    lookback: int = 60
    forecast: int = 5
    epochs: int = 100
    batch_size: int = 64


class AIConfig(BaseModel):
    optimizer: AIOptimizerConfig = AIOptimizerConfig()
    predictor: AIPredictorConfig = AIPredictorConfig()


class SchedulerConfig(BaseModel):
    download_time: str = "15:30"
    strategy_time: str = "16:00"


class AppConfig(BaseModel):
    qmt: QMTConfig
    storage: StorageConfig = StorageConfig()
    download: DownloadConfig = DownloadConfig()
    strategies: StrategyConfig = StrategyConfig()
    backtest: BacktestConfig = BacktestConfig()
    ai: AIConfig = AIConfig()
    scheduler: SchedulerConfig = SchedulerConfig()


def _expand_env(value: str) -> str:
    """替换 ${VAR} 为环境变量值"""
    import re
    def replacer(match):
        return os.getenv(match.group(1), "")
    return re.sub(r'\$\{(\w+)\}', replacer, value)


def _expand_dict(obj):
    """递归展开配置中的环境变量"""
    if isinstance(obj, dict):
        return {k: _expand_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_expand_dict(item) for item in obj]
    elif isinstance(obj, str):
        return _expand_env(obj)
    return obj


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    加载配置文件
    优先级: 环境变量 > YAML 配置 > Pydantic 默认值
    """
    load_dotenv()

    if config_path is None:
        config_path = Path(__file__).parent / "settings.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    raw = _expand_dict(raw)
    return AppConfig(**raw)


# 全局配置实例
config = load_config()
