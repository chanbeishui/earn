"""择时信号实现"""
import pandas as pd
import numpy as np
from .base import TimingSignal


class MACrossSignal(TimingSignal):
    """均线交叉信号"""
    type = "ma_cross"

    def __init__(self, **params):
        super().__init__(**params)
        self.display = "均线金叉" if params.get("direction", "up") == "up" else "均线死叉"
        self.direction = "buy" if params.get("direction", "up") == "up" else "sell"

    def check(self, df: pd.DataFrame, date_idx: int = -1) -> bool:
        fast = int(self.params.get("fast", 5))
        slow = int(self.params.get("slow", 20))
        direction = self.params.get("direction", "up")

        if date_idx < slow:
            return False

        close = df["close"]
        ma_fast = close.rolling(fast).mean()
        ma_slow = close.rolling(slow).mean()

        if direction == "up":
            # 金叉: 快线上穿慢线
            return (ma_fast.iloc[date_idx] > ma_slow.iloc[date_idx] and
                    ma_fast.iloc[date_idx - 1] <= ma_slow.iloc[date_idx - 1])
        else:
            # 死叉: 快线下穿慢线
            return (ma_fast.iloc[date_idx] < ma_slow.iloc[date_idx] and
                    ma_fast.iloc[date_idx - 1] >= ma_slow.iloc[date_idx - 1])


class MACDCrossSignal(TimingSignal):
    """MACD 交叉信号"""
    type = "macd_golden_cross"

    def __init__(self, **params):
        super().__init__(**params)
        is_buy = params.get("direction", "golden") in ("golden", "up")
        self.display = "MACD金叉" if is_buy else "MACD死叉"
        self.direction = "buy" if is_buy else "sell"

    def check(self, df: pd.DataFrame, date_idx: int = -1) -> bool:
        fast = int(self.params.get("fast", 12))
        slow = int(self.params.get("slow", 26))
        signal = int(self.params.get("signal", 9))
        direction = self.params.get("direction", "golden")

        if date_idx < slow + signal:
            return False

        close = df["close"]
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()

        if direction in ("golden", "up"):
            return (dif.iloc[date_idx] > dea.iloc[date_idx] and
                    dif.iloc[date_idx - 1] <= dea.iloc[date_idx - 1])
        else:
            return (dif.iloc[date_idx] < dea.iloc[date_idx] and
                    dif.iloc[date_idx - 1] >= dea.iloc[date_idx - 1])


class RSISignal(TimingSignal):
    """RSI 超买超卖信号"""
    type = "rsi_oversold"

    def __init__(self, **params):
        super().__init__(**params)
        is_buy = params.get("direction", "cross_above") == "cross_above"
        threshold = params.get("threshold", 30)
        if is_buy:
            self.display = f"RSI超卖({threshold})"
            self.direction = "buy"
        else:
            self.display = f"RSI超买({threshold})"
            self.direction = "sell"

    def check(self, df: pd.DataFrame, date_idx: int = -1) -> bool:
        period = int(self.params.get("period", 14))
        threshold = int(self.params.get("threshold", 30))
        direction = self.params.get("direction", "cross_above")

        if date_idx < period + 1:
            return False

        close = df["close"]
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        if direction == "cross_above":
            # 从下方上穿阈值
            return (rsi.iloc[date_idx] > threshold and
                    rsi.iloc[date_idx - 1] <= threshold)
        else:
            # 从上方下穿阈值
            return (rsi.iloc[date_idx] < threshold and
                    rsi.iloc[date_idx - 1] >= threshold)


class BollSignal(TimingSignal):
    """布林带突破信号"""
    type = "boll_lower"

    def __init__(self, **params):
        super().__init__(**params)
        direction = params.get("direction", "lower")
        self.display = "布林下轨突破" if direction == "lower" else "布林上轨突破"
        self.direction = "buy" if direction == "lower" else "sell"

    def check(self, df: pd.DataFrame, date_idx: int = -1) -> bool:
        period = int(self.params.get("period", 20))
        std_mul = float(self.params.get("std", 2.0))
        direction = self.params.get("direction", "lower")

        if date_idx < period + 1:
            return False

        close = df["close"]
        middle = close.rolling(period).mean()
        std = close.rolling(period).std()
        upper = middle + std_mul * std
        lower = middle - std_mul * std

        if direction == "lower":
            # 价格跌破下轨后回升（买入）
            return (close.iloc[date_idx] > lower.iloc[date_idx] and
                    close.iloc[date_idx - 1] <= lower.iloc[date_idx - 1])
        else:
            # 价格突破上轨后回落（卖出）
            return (close.iloc[date_idx] < upper.iloc[date_idx] and
                    close.iloc[date_idx - 1] >= upper.iloc[date_idx - 1])


class StopLossSignal(TimingSignal):
    """固定止损信号"""
    type = "stop_loss"

    def __init__(self, **params):
        super().__init__(**params)
        self.display = f"止损({params.get('percent', -8)}%)"
        self.direction = "sell"

    def check(self, df: pd.DataFrame, date_idx: int = -1) -> bool:
        """止损需要持仓成本信息，这里仅作占位"""
        percent = float(self.params.get("percent", -8))
        # 需要外部传入 buy_price 和 current_price
        buy_price = self.params.get("_buy_price")
        if buy_price is None:
            return False
        current = df["close"].iloc[date_idx]
        return (current - buy_price) / buy_price * 100 <= percent

    def check_with_cost(self, buy_price: float, current_price: float) -> bool:
        percent = float(self.params.get("percent", -8))
        return (current_price - buy_price) / buy_price * 100 <= percent


class TakeProfitSignal(TimingSignal):
    """固定止盈信号"""
    type = "take_profit"

    def __init__(self, **params):
        super().__init__(**params)
        self.display = f"止盈({params.get('percent', 20)}%)"
        self.direction = "sell"

    def check(self, df: pd.DataFrame, date_idx: int = -1) -> bool:
        percent = float(self.params.get("percent", 20))
        buy_price = self.params.get("_buy_price")
        if buy_price is None:
            return False
        current = df["close"].iloc[date_idx]
        return (current - buy_price) / buy_price * 100 >= percent

    def check_with_cost(self, buy_price: float, current_price: float) -> bool:
        percent = float(self.params.get("percent", 20))
        return (current_price - buy_price) / buy_price * 100 >= percent
