"""因子基类"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
import pandas as pd
import numpy as np


class Factor(ABC):
    """因子抽象基类"""

    name: str = "base"
    display: str = "基础因子"
    category: str = "base"  # technical / fundamental / composite

    def __init__(self, **params):
        self.params = params

    @abstractmethod
    def calculate(self, df: pd.DataFrame, **kwargs) -> pd.Series:
        """
        计算因子值
        :param df: 单只股票的 K 线/财务数据 DataFrame (index 为 date)
        :return: 因子值 Series
        """
        pass

    def get_value(self, df: pd.DataFrame, date_str: str, **kwargs) -> float:
        """获取某个日期的因子值（最近可用的）"""
        series = self.calculate(df, **kwargs)
        if series.empty:
            return np.nan

        # 找最近 <= date_str 的非 NaN 值
        try:
            target = pd.Timestamp(date_str)
            valid = series.dropna()
            valid = valid[valid.index <= target]
            if valid.empty:
                return np.nan
            return float(valid.iloc[-1])
        except Exception:
            return np.nan
