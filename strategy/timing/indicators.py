"""技术指标计算工具函数"""
import pandas as pd
import numpy as np


def calc_ma(df: pd.DataFrame, period: int) -> pd.Series:
    return df["close"].rolling(window=period).mean()


def calc_ema(df: pd.DataFrame, period: int) -> pd.Series:
    return df["close"].ewm(span=period, adjust=False).mean()


def calc_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
    """返回 (DIF, DEA, MACD柱)"""
    ema_fast = calc_ema(df, fast)
    ema_slow = calc_ema(df, slow)
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd_bar = (dif - dea) * 2
    return dif, dea, macd_bar


def calc_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    close = df["close"]
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_boll(df: pd.DataFrame, period: int = 20, std: float = 2.0):
    """返回 (upper, middle, lower)"""
    close = df["close"]
    middle = close.rolling(window=period).mean()
    std_val = close.rolling(window=period).std()
    upper = middle + std * std_val
    lower = middle - std * std_val
    return upper, middle, lower


def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.DataFrame({
        "hl": high - low,
        "hc": abs(high - prev_close),
        "lc": abs(low - prev_close),
    }).max(axis=1)
    return tr.rolling(window=period).mean()
