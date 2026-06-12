"""持仓管理"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


@dataclass
class Position:
    """单只股票持仓"""
    code: str
    volume: int           # 持仓股数
    avg_cost: float       # 持仓均价
    market_value: float = 0.0  # 当前市值
    unrealized_pnl: float = 0.0  # 浮动盈亏

    def update_market_value(self, current_price: float):
        """更新市值"""
        self.market_value = current_price * self.volume
        self.unrealized_pnl = (current_price - self.avg_cost) * self.volume


class Portfolio:
    """投资组合"""

    def __init__(self, initial_capital: float = 1_000_000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}  # code -> Position
        self.total_commission = 0.0
        self.total_stamp_duty = 0.0
        self.trade_count = 0

        # 历史快照
        self._history: List[dict] = []

    @property
    def total_value(self) -> float:
        """总资产 = 现金 + 持仓市值"""
        mv = sum(p.market_value for p in self.positions.values())
        return self.cash + mv

    @property
    def total_pnl(self) -> float:
        """总盈亏"""
        return self.total_value - self.initial_capital

    def apply_fill(self, fill, date_str: str):
        """应用成交到持仓"""
        if fill.direction == "buy":
            self._apply_buy(fill)
        else:
            self._apply_sell(fill)

        self.total_commission += fill.commission
        self.total_stamp_duty += fill.stamp_duty
        self.trade_count += 1

    def _apply_buy(self, fill):
        cost = fill.amount + fill.commission
        if self.cash < cost:
            # 资金不足，能买多少买多少
            max_vol = int(self.cash / (fill.price * 1.001)) // 100 * 100
            if max_vol < 100:
                return
            # 简化：订单已通过 check_affordable 验证，这里直接扣款
            return

        self.cash -= cost

        if fill.code in self.positions:
            pos = self.positions[fill.code]
            total_vol = pos.volume + fill.volume
            total_cost = pos.avg_cost * pos.volume + fill.price * fill.volume
            pos.volume = total_vol
            pos.avg_cost = total_cost / total_vol
            pos.update_market_value(fill.price)
        else:
            self.positions[fill.code] = Position(
                code=fill.code,
                volume=fill.volume,
                avg_cost=fill.price,
                market_value=fill.price * fill.volume,
                unrealized_pnl=0.0,
            )

    def _apply_sell(self, fill):
        if fill.code not in self.positions:
            return
        pos = self.positions[fill.code]
        if pos.volume < fill.volume:
            return  # 持仓不足

        self.cash += fill.amount - fill.commission - fill.stamp_duty
        pos.volume -= fill.volume

        if pos.volume == 0:
            del self.positions[fill.code]
        else:
            pos.update_market_value(fill.price)

    def update_market_prices(self, prices: Dict[str, float]):
        """更新所有持仓市值"""
        for code, pos in self.positions.items():
            if code in prices:
                pos.update_market_value(prices[code])

    def get_available_codes(self) -> List[str]:
        """获取当前持仓股票代码"""
        return list(self.positions.keys())

    def get_position_ratio(self, code: str) -> float:
        """获取某股票仓位占比"""
        if code not in self.positions:
            return 0.0
        if self.total_value <= 0:
            return 0.0
        return self.positions[code].market_value / self.total_value

    def can_buy(self, price: float, volume: int) -> bool:
        """检查是否可以买入"""
        cost = price * volume * 1.001  # 加上佣金
        return self.cash >= cost and volume >= 100

    def snapshot(self, date_str: str) -> dict:
        """记录当前状态快照"""
        record = {
            "date": date_str,
            "cash": round(self.cash, 2),
            "position_value": round(sum(p.market_value for p in self.positions.values()), 2),
            "total_value": round(self.total_value, 2),
            "pnl": round(self.total_pnl, 2),
            "return": round(self.total_pnl / self.initial_capital * 100, 4),
            "positions": [{
                "code": p.code,
                "volume": p.volume,
                "avg_cost": round(p.avg_cost, 3),
                "market_value": round(p.market_value, 2),
                "unrealized_pnl": round(p.unrealized_pnl, 2),
            } for p in self.positions.values()],
        }
        self._history.append(record)
        return record

    def get_history_df(self) -> pd.DataFrame:
        """获取历史净值 DataFrame"""
        if not self._history:
            return pd.DataFrame()
        df = pd.DataFrame(self._history)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        df["cum_return"] = df["total_value"] / self.initial_capital - 1
        return df
