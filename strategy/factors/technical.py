"""技术因子"""
import pandas as pd
import numpy as np
from .base import Factor


class RSIFactor(Factor):
    """RSI 相对强弱指标"""
    name = "rsi"
    display = "RSI 相对强弱"
    category = "technical"

    def calculate(self, df: pd.DataFrame, **kwargs) -> pd.Series:
        period = int(self.params.get("period", 14))
        close = df["close"]
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi


class MACDFactor(Factor):
    """MACD 指标（DIF - DEA 差值）"""
    name = "macd_dif"
    display = "MACD 离差值"
    category = "technical"

    def calculate(self, df: pd.DataFrame, **kwargs) -> pd.Series:
        fast = int(self.params.get("fast", 12))
        slow = int(self.params.get("slow", 26))
        signal = int(self.params.get("signal", 9))
        close = df["close"]
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        return dif - dea  # MACD 柱


class BollPositionFactor(Factor):
    """布林带位置（价格在布林带中的相对位置 0~1）"""
    name = "boll_position"
    display = "布林带位置"
    category = "technical"

    def calculate(self, df: pd.DataFrame, **kwargs) -> pd.Series:
        period = int(self.params.get("period", 20))
        std_mul = float(self.params.get("std", 2.0))
        close = df["close"]
        middle = close.rolling(window=period, min_periods=period).mean()
        std = close.rolling(window=period, min_periods=period).std()
        upper = middle + std_mul * std
        lower = middle - std_mul * std
        # 位置 = (close - lower) / (upper - lower)
        pos = (close - lower) / (upper - lower).replace(0, np.nan)
        return pos.clip(0, 1)


class MADeviationFactor(Factor):
    """均线乖离率 (收盘价 - MA_N) / MA_N * 100"""
    name = "ma_dif"
    display = "均线乖离率"
    category = "technical"

    def calculate(self, df: pd.DataFrame, **kwargs) -> pd.Series:
        period = int(self.params.get("period", 20))
        close = df["close"]
        ma = close.rolling(window=period, min_periods=period).mean()
        return (close - ma) / ma * 100


class TurnoverRateFactor(Factor):
    """换手率因子（从 volume 估算）"""
    name = "turnover_rate"
    display = "换手率"
    category = "technical"

    def calculate(self, df: pd.DataFrame, **kwargs) -> pd.Series:
        period = int(self.params.get("period", 5))
        if "turnover" in df.columns:
            return df["turnover"].rolling(window=period, min_periods=period).mean()
        # 不可用时返回 NaN
        return pd.Series(np.nan, index=df.index)


class VolumeRatioFactor(Factor):
    """量比（当日成交量 / N日均量）"""
    name = "volume_ratio"
    display = "量比"
    category = "technical"

    def calculate(self, df: pd.DataFrame, **kwargs) -> pd.Series:
        period = int(self.params.get("period", 5))
        volume = df["volume"]
        avg_vol = volume.rolling(window=period, min_periods=period).mean().shift(1)
        ratio = volume / avg_vol.replace(0, np.nan)
        return ratio


class ATRFactor(Factor):
    """ATR 真实波幅"""
    name = "atr"
    display = "ATR 真实波幅"
    category = "technical"

    def calculate(self, df: pd.DataFrame, **kwargs) -> pd.Series:
        period = int(self.params.get("period", 14))
        high, low, close = df["high"], df["low"], df["close"]
        prev_close = close.shift(1)
        tr = pd.DataFrame({
            "hl": high - low,
            "hc": abs(high - prev_close),
            "lc": abs(low - prev_close),
        }).max(axis=1)
        atr = tr.rolling(window=period, min_periods=period).mean()
        return atr


class MomentumFactor(Factor):
    """动量因子：N 日涨跌幅"""
    name = "momentum"
    display = "动量因子"
    category = "technical"

    def calculate(self, df: pd.DataFrame, **kwargs) -> pd.Series:
        period = int(self.params.get("period", 20))
        close = df["close"]
        return close.pct_change(periods=period)
