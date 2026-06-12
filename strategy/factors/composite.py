"""复合因子"""
import pandas as pd
import numpy as np
from .base import Factor


class ICWeightedFactor(Factor):
    """基于 IC 信息系数的加权综合打分"""
    name = "ic_weighted"
    display = "IC加权打分"
    category = "composite"

    def __init__(self, **params):
        super().__init__(**params)
        self._ic_cache: dict = {}  # {factor_name: average_IC}

    def calculate(self, df: pd.DataFrame, **kwargs) -> pd.Series:
        # 这是一个复合因子，需要子因子列表
        sub_factors = kwargs.get("sub_factors", [])
        factor_values = kwargs.get("factor_values", {})
        lookback = self.params.get("lookback", 60)

        if not sub_factors or not factor_values:
            return pd.Series(np.nan, index=df.index)

        # 等权打分（IC 权重在 Phase 4 AI 优化中计算）
        scores = pd.DataFrame(index=df.index)
        for f_name in sub_factors:
            if f_name in factor_values:
                vals = factor_values[f_name]
                # Z-score 标准化
                mean_val = vals.mean()
                std_val = vals.std()
                if std_val and std_val > 0:
                    scores[f_name] = (vals - mean_val) / std_val
                else:
                    scores[f_name] = 0

        # 等权平均
        result = scores.mean(axis=1)
        return result


class ZScoreRankFactor(Factor):
    """多因子 Z-score 等权综合排名"""
    name = "zscore_rank"
    display = "Z-score 排名"
    category = "composite"

    def __init__(self, **params):
        super().__init__(**params)

    def calculate(self, df: pd.DataFrame, **kwargs) -> pd.Series:
        factor_values = kwargs.get("factor_values", {})
        if not factor_values:
            return pd.Series(np.nan, index=df.index)

        scores = pd.DataFrame(index=df.index)
        for name, vals in factor_values.items():
            mean_val = vals.mean()
            std_val = vals.std()
            if std_val and std_val > 0:
                scores[name] = (vals - mean_val) / std_val
            else:
                scores[name] = 0

        return scores.mean(axis=1)


class IndustryNeutralFactor(Factor):
    """行业内 Z-score 标准化得分"""
    name = "industry_neutral"
    display = "行业中性化"
    category = "composite"

    def calculate(self, df: pd.DataFrame, **kwargs) -> pd.Series:
        factor_values = kwargs.get("factor_values", {})
        industries = kwargs.get("industries", {})

        if not factor_values:
            return pd.Series(np.nan, index=df.index)

        # 简单实现：对每个因子做 Z-score 后等权
        scores = pd.DataFrame(index=df.index)
        for name, vals in factor_values.items():
            mean_val = vals.mean()
            std_val = vals.std()
            if std_val and std_val > 0:
                scores[name] = (vals - mean_val) / std_val
            else:
                scores[name] = 0

        return scores.mean(axis=1)
