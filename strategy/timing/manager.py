"""择时管理器 — 根据类型创建信号实例"""
from typing import Type, Dict, Optional, List
from .base import TimingSignal
from .signals import (
    MACrossSignal, MACDCrossSignal, RSISignal,
    BollSignal, StopLossSignal, TakeProfitSignal,
)


class TimingManager:
    """择时信号工厂"""

    _registry: Dict[str, Type[TimingSignal]] = {
        "ma_cross": MACrossSignal,
        "macd_golden_cross": MACDCrossSignal,
        "macd_death_cross": MACDCrossSignal,
        "rsi_oversold": RSISignal,
        "rsi_overbought": RSISignal,
        "boll_lower": BollSignal,
        "boll_upper": BollSignal,
        "stop_loss": StopLossSignal,
        "take_profit": TakeProfitSignal,
    }

    @classmethod
    def create(cls, signal_type: str, **params) -> Optional[TimingSignal]:
        """根据信号类型创建实例"""
        sig_cls = cls._registry.get(signal_type)
        if sig_cls is None:
            print(f"[TimingManager] 未知信号类型: {signal_type}")
            return None
        return sig_cls(**params)

    @classmethod
    def create_signals(cls, signal_configs: List[dict]) -> List[TimingSignal]:
        """批量创建信号"""
        signals = []
        for cfg in signal_configs:
            sig = cls.create(cfg["type"], **cfg.get("params", {}))
            if sig:
                signals.append(sig)
        return signals

    @classmethod
    def list_by_direction(cls, direction: str = "buy") -> list:
        """列出某方向的信号"""
        result = []
        seen = set()
        for t, cls_obj in cls._registry.items():
            # 根据 type 推断方向
            if direction == "buy":
                if t in ("ma_cross", "macd_golden_cross", "rsi_oversold", "boll_lower"):
                    name = t
                    display = {"ma_cross": "均线金叉", "macd_golden_cross": "MACD金叉",
                               "rsi_oversold": "RSI超卖", "boll_lower": "布林下轨突破"}.get(t, t)
                    if name not in seen:
                        seen.add(name)
                        result.append({"type": name, "display": display})
            else:
                if t in ("ma_cross", "macd_death_cross", "rsi_overbought", "boll_upper",
                         "stop_loss", "take_profit"):
                    name = t
                    display = {"ma_cross": "均线死叉", "macd_death_cross": "MACD死叉",
                               "rsi_overbought": "RSI超买", "boll_upper": "布林上轨突破",
                               "stop_loss": "固定止损", "take_profit": "固定止盈"}.get(t, t)
                    if name not in seen:
                        seen.add(name)
                        result.append({"type": name, "display": display})
        return result
