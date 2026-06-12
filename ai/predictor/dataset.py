"""PyTorch Dataset — 时序数据预处理"""
import torch
from torch.utils.data import Dataset
import pandas as pd
import numpy as np
from typing import List, Tuple, Optional


class KlineDataset(Dataset):
    """
    K 线时序预测数据集
    输入: lookback 天的 [open, high, low, close, volume]
    输出: forecast 天后涨跌方向 (二分类) 或 收益率 (回归)
    """

    def __init__(self, df: pd.DataFrame, lookback: int = 60, forecast: int = 5,
                 target_type: str = "direction",  # direction / return
                 normalize: bool = True):
        """
        :param df: 单只股票的 K 线 DataFrame (index=date, columns=[open,high,low,close,volume])
        """
        self.lookback = lookback
        self.forecast = forecast
        self.target_type = target_type

        # 提取特征
        feature_cols = ["open", "high", "low", "close", "volume"]
        data = df[feature_cols].values.astype(np.float64)

        # 归一化
        if normalize:
            self.mean = data.mean(axis=0)
            self.std = data.std(axis=0)
            self.std[self.std == 0] = 1.0
            data = (data - self.mean) / self.std
        else:
            self.mean = np.zeros(data.shape[1])
            self.std = np.ones(data.shape[1])

        self.feature_dim = len(feature_cols)

        # 构建 X, y
        self.X = []
        self.y = []
        self.dates = []

        close_prices = df["close"].values

        for i in range(lookback, len(data) - forecast):
            self.X.append(data[i - lookback:i])
            self.dates.append(df.index[i])

            future_price = close_prices[i + forecast]
            current_price = close_prices[i]

            if target_type == "direction":
                self.y.append(1 if future_price > current_price else 0)
            else:
                self.y.append((future_price - current_price) / current_price)

        self.X = np.array(self.X, dtype=np.float32)
        self.y = np.array(self.y, dtype=np.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return (
            torch.tensor(self.X[idx], dtype=torch.float32),
            torch.tensor(self.y[idx], dtype=torch.float32),
        )

    def inverse_transform_features(self, data: np.ndarray) -> np.ndarray:
        """反归一化特征"""
        return data * self.std + self.mean


class MultiStockDataset(Dataset):
    """多股票数据集 — 从 DataStorage 批量构建"""

    def __init__(self, storage, codes: List[str], lookback: int = 60,
                 forecast: int = 5, target_type: str = "direction",
                 start_date: str = "2020-01-01", end_date: str = "2025-01-01"):
        all_X, all_y = [], []

        for code in codes:
            df = storage.load_kline(code, freq="daily", start=start_date, end=end_date)
            if df.empty or len(df) < lookback + forecast + 10:
                continue

            try:
                ds = KlineDataset(df, lookback, forecast, target_type)
                if len(ds) > 0:
                    all_X.append(ds.X)
                    all_y.append(ds.y)
            except Exception:
                continue

        if all_X:
            self.X = np.concatenate(all_X, axis=0)
            self.y = np.concatenate(all_y, axis=0)
        else:
            self.X = np.empty((0, lookback, 5), dtype=np.float32)
            self.y = np.empty((0,), dtype=np.float32)

        self.X = torch.tensor(self.X, dtype=torch.float32)
        self.y = torch.tensor(self.y, dtype=torch.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]
