"""绩效分析器"""
from typing import Dict, List
import pandas as pd
import numpy as np
from scipy import stats


class Analyzer:
    """回测绩效分析"""

    def __init__(self, df: pd.DataFrame, portfolio, trades: List[dict]):
        self.df = df
        self.portfolio = portfolio
        self.trades = trades

    def analyze(self, benchmark_return: float = 0.0) -> dict:
        """执行全面分析"""
        if self.df.empty:
            return {"summary": {}, "trades": []}

        returns = self.df["cum_return"]

        # 总收益
        total_return = returns.iloc[-1] * 100

        # 年化收益率
        days = (self.df.index[-1] - self.df.index[0]).days
        years = max(days / 365, 0.01)
        annual_return = ((1 + total_return / 100) ** (1 / years) - 1) * 100

        # 日收益率序列
        daily_returns = returns.diff().fillna(0)

        # 波动率
        daily_vol = daily_returns.std()
        annual_vol = daily_vol * np.sqrt(252) * 100

        # 夏普比率
        risk_free = 0.02  # 假设无风险利率 2%
        sharpe = (annual_return - risk_free * 100) / annual_vol if annual_vol > 0 else 0

        # 最大回撤
        cummax = returns.cummax()
        drawdowns = returns - cummax
        max_drawdown = drawdowns.min() * 100

        # 最大回撤持续期
        dd_start = None
        dd_end = None
        max_dd = 0
        peak_idx = 0
        for i in range(len(returns)):
            if returns.iloc[i] >= cummax.iloc[i]:
                peak_idx = i
            dd = returns.iloc[i] - cummax.iloc[i]
            if dd < max_dd:
                max_dd = dd
                dd_start = self.df.index[peak_idx]
                dd_end = self.df.index[i]

        # 胜率
        buys = [t for t in self.trades if t["direction"] == "buy"]
        sells = [t for t in self.trades if t["direction"] == "sell"]
        win_count = 0
        total_pairs = 0
        # 简化：按买入卖出配对计算
        if buys and sells:
            # 先进先出配对
            buy_queue = list(buys)
            for sell in sells:
                if buy_queue:
                    buy = buy_queue.pop(0)
                    sell_amt = sell["price"] * sell["volume"]
                    buy_amt = buy["price"] * buy["volume"]
                    if sell_amt > buy_amt:
                        win_count += 1
                    total_pairs += 1
        win_rate = (win_count / total_pairs * 100) if total_pairs > 0 else 0

        # 盈亏比
        total_profit = sum(
            s["price"] * s["volume"] - b["price"] * b["volume"]
            for b, s in zip(buys[:len(sells)], sells[:len(buys)])
            if len(buys) >= len(sells)
        ) if buys else 0

        # 换手率
        total_buy_amount = sum(t["amount"] for t in self.trades if t["direction"] == "buy")
        avg_capital = self.portfolio.initial_capital
        turnover = total_buy_amount / avg_capital if avg_capital > 0 else 0

        # Calmar 比率
        calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

        # 超额收益
        excess_return = total_return - benchmark_return

        summary = {
            "total_return_pct": round(total_return, 2),
            "annual_return_pct": round(annual_return, 2),
            "annual_volatility_pct": round(annual_vol, 2),
            "sharpe_ratio": round(sharpe, 3),
            "calmar_ratio": round(calmar, 3),
            "max_drawdown_pct": round(max_drawdown, 2),
            "max_dd_start": str(dd_start.date()) if dd_start else None,
            "max_dd_end": str(dd_end.date()) if dd_end else None,
            "win_rate_pct": round(win_rate, 1),
            "profit_loss_ratio": round(abs(total_profit / (total_buy_amount - total_profit)), 2) if total_buy_amount > total_profit > 0 else 0,
            "total_trades": len(self.trades),
            "buy_count": len(buys),
            "sell_count": len(sells),
            "turnover": round(turnover, 2),
            "total_commission": round(self.portfolio.total_commission, 2),
            "total_stamp_duty": round(self.portfolio.total_stamp_duty, 2),
            "benchmark_return_pct": round(benchmark_return, 2),
            "excess_return_pct": round(excess_return, 2),
            "initial_capital": self.portfolio.initial_capital,
            "final_value": round(self.portfolio.total_value, 2),
            "start_date": str(self.df.index[0].date()),
            "end_date": str(self.df.index[-1].date()),
        }

        # 日收益率序列（供前端画图）
        daily_list = []
        for idx, row in self.df.iterrows():
            daily_list.append({
                "date": str(idx.date()),
                "total_value": round(row["total_value"], 2),
                "cum_return": round(row["cum_return"] * 100, 4),
                "cash": round(row["cash"], 2),
            })

        # 月度收益
        monthly = self._monthly_returns()

        return {
            "summary": summary,
            "daily_returns": daily_list,
            "monthly_returns": monthly,
            "trades": self.trades,
        }

    def _monthly_returns(self) -> list:
        """计算月度收益率（用于热力图）"""
        if self.df.empty:
            return []

        df = self.df.copy()
        df["month"] = df.index.to_period("M")
        monthly = df.groupby("month")["total_value"].apply(
            lambda x: (x.iloc[-1] - x.iloc[0]) / x.iloc[0] * 100
            if len(x) > 1 and x.iloc[0] > 0 else 0
        ).reset_index()

        results = []
        for _, row in monthly.iterrows():
            results.append({
                "year": row["month"].year,
                "month": row["month"].month,
                "return_pct": round(row["total_value"], 2),
            })
        return results
