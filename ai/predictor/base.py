"""预测器基类"""
from abc import ABC, abstractmethod


class BasePredictor(ABC):
    """深度学习预测器抽象基类"""

    @abstractmethod
    def train(self, *args, **kwargs) -> dict:
        pass

    @abstractmethod
    def predict(self, *args, **kwargs):
        pass
