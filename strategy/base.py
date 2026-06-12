"""策略基类"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class Strategy(ABC):
    """策略抽象基类 — 同时兼容回测和实盘"""

    name: str = "base"
    description: str = ""

    @abstractmethod
    def select_stocks(self, stock_codes: List[str], date_str: str,
                      lookback: int = 120) -> List[dict]:
        """
        执行选股
        :param stock_codes: 候选股票代码
        :param date_str: 选股日期
        :param lookback: 回溯天数
        :return: [{code, score, factor_scores, signal}]
        """
        pass

    def on_bar(self, bar_data: dict):
        """
        实盘 Bar 回调（预留接口）
        回测时由 Engine 模拟驱动，实盘时由 xtquant 回调
        """
        pass

    def on_signal(self, signal: dict):
        """
        信号回调（预留接口）
        """
        pass
