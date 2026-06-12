"""因子管理器 — 根据名称创建因子实例"""
from typing import Type, Dict, Optional, List
from .base import Factor
from .technical import (
    RSIFactor, MACDFactor, BollPositionFactor, MADeviationFactor,
    TurnoverRateFactor, VolumeRatioFactor, ATRFactor, MomentumFactor,
)
from .fundamental import (
    PETTMFactor, PBFactor, ROEFactor,
    RevenueYoYFactor, ProfitYoYFactor, DividendYieldFactor,
)
from .composite import ICWeightedFactor, ZScoreRankFactor, IndustryNeutralFactor


class FactorManager:
    """因子工厂"""

    _registry: Dict[str, Type[Factor]] = {
        # 技术因子
        "rsi": RSIFactor,
        "macd_dif": MACDFactor,
        "boll_position": BollPositionFactor,
        "ma_dif": MADeviationFactor,
        "turnover_rate": TurnoverRateFactor,
        "volume_ratio": VolumeRatioFactor,
        "atr": ATRFactor,
        "momentum": MomentumFactor,
        # 基本面因子
        "pe_ttm": PETTMFactor,
        "pb": PBFactor,
        "roe": ROEFactor,
        "revenue_yoy": RevenueYoYFactor,
        "profit_yoy": ProfitYoYFactor,
        "dividend_yield": DividendYieldFactor,
        # 复合因子
        "ic_weighted": ICWeightedFactor,
        "zscore_rank": ZScoreRankFactor,
        "industry_neutral": IndustryNeutralFactor,
    }

    @classmethod
    def create(cls, name: str, **params) -> Optional[Factor]:
        """根据因子名称创建实例"""
        factor_cls = cls._registry.get(name)
        if factor_cls is None:
            print(f"[FactorManager] 未知因子: {name}")
            return None
        return factor_cls(**params)

    @classmethod
    def create_all(cls, factor_configs: List[dict]) -> List[Factor]:
        """批量创建因子"""
        factors = []
        for cfg in factor_configs:
            f = cls.create(cfg["name"], **cfg.get("params", {}))
            if f:
                factors.append(f)
        return factors

    @classmethod
    def list_all(cls) -> list:
        """列出所有注册的因子"""
        return [
            {"name": f.name, "display": f.display, "category": f.category}
            for f in cls._registry.values()
        ]

    @classmethod
    def list_by_category(cls, category: str) -> list:
        """按分类列出因子"""
        return [
            {"name": f.name, "display": f.display}
            for f in cls._registry.values()
            if f.category == category
        ]
