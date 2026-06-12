"""择时信号基类"""
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
import numpy as np


class TimingSignal(ABC):
    """择时信号抽象基类"""

    type: str = "base"
    display: str = "基础信号"
    direction: str = "buy"  # buy / sell

    def __init__(self, **params):
        self.params = params

    @abstractmethod
    def check(self, df: pd.DataFrame, date_idx: int = -1) -> bool:
        """
        检查在指定位置是否触发信号
        :param df: K 线 DataFrame (index 为整数或 date)
        :param date_idx: 检查第几个位置（默认最后一个）
        :return: True=触发信号
        """
        pass

    def scan(self, df: pd.DataFrame) -> pd.Series:
        """
        扫描全部数据，返回信号序列 (True/False)
        """
        signals = pd.Series(False, index=df.index)
        for i in range(1, len(df)):
            try:
                signals.iloc[i] = self.check(df, i)
            except Exception:
                pass
        return signals
