"""模拟券商 — 佣金/滑点/印花税"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Order:
    """订单"""
    code: str
    direction: str        # buy / sell
    price: float          # 限价（市价用 next_open）
    volume: int           # 股数（100 的整数倍）
    order_type: str = "market"  # market / limit
    date: str = ""
    strategy_id: str = ""


@dataclass
class Fill:
    """成交单"""
    code: str
    direction: str
    price: float          # 实际成交价
    volume: int
    commission: float     # 佣金
    stamp_duty: float     # 印花税（仅卖出）
    amount: float         # 成交金额
    date: str = ""


@dataclass
class BrokerConfig:
    """券商配置"""
    commission_rate: float = 0.00025    # 万2.5
    min_commission: float = 5.0          # 最低佣金 5 元
    stamp_duty_rate: float = 0.001       # 千1（仅卖出）
    slippage: float = 0.0001             # 滑点万1
    lot_size: int = 100                  # 1手=100股


class Broker:
    """模拟券商"""

    def __init__(self, config: BrokerConfig = None):
        self.config = config or BrokerConfig()

    def execute_order(self, order: Order, bar: dict) -> Fill:
        """
        执行订单
        :param order: 订单
        :param bar: 当前 Bar 数据 (open, high, low, close, volume)
        :return: 成交单
        """
        # 市价单以当前 open 成交 + 滑点
        if order.order_type == "market":
            if order.direction == "buy":
                price = bar["open"] * (1 + self.config.slippage)
            else:
                price = bar["open"] * (1 - self.config.slippage)
        else:
            price = order.price

        # 确保成交量是 100 的整数倍
        volume = (order.volume // self.config.lot_size) * self.config.lot_size
        if volume <= 0:
            return None

        amount = price * volume

        # 佣金（双向）
        commission = max(amount * self.config.commission_rate, self.config.min_commission)

        # 印花税（仅卖出）
        stamp_duty = 0.0
        if order.direction == "sell":
            stamp_duty = amount * self.config.stamp_duty_rate

        return Fill(
            code=order.code,
            direction=order.direction,
            price=round(price, 3),
            volume=volume,
            commission=round(commission, 2),
            stamp_duty=round(stamp_duty, 2),
            amount=round(amount, 2),
            date=order.date,
        )
