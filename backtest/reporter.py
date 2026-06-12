"""报告生成 — Plotly 图表"""
from typing import Dict, List
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


class Reporter:
    """回测报告生成器"""

    @staticmethod
    def equity_curve(daily_returns: List[dict], benchmark_code: str = "000300.SH") -> go.Figure:
        """累计收益曲线"""
        if not daily_returns:
            return go.Figure()

        df = pd.DataFrame(daily_returns)
        df["date"] = pd.to_datetime(df["date"])

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["cum_return"],
            mode="lines", name="策略收益(%)",
            line=dict(color="#1f77b4", width=2),
            fill="tozeroy",
            fillcolor="rgba(31, 119, 180, 0.1)",
        ))
        fig.update_layout(
            title="累计收益率曲线",
            xaxis_title="日期",
            yaxis_title="累计收益 (%)",
            hovermode="x unified",
            height=400,
        )
        return fig

    @staticmethod
    def monthly_heatmap(monthly: List[dict]) -> go.Figure:
        """月度收益热力图"""
        if not monthly:
            return go.Figure()

        df = pd.DataFrame(monthly)
        pivot = df.pivot(index="year", columns="month", values="return_pct")

        months = ["1月", "2月", "3月", "4月", "5月", "6月",
                   "7月", "8月", "9月", "10月", "11月", "12月"]

        # 确保所有列存在
        for m in range(1, 13):
            if m not in pivot.columns:
                pivot[m] = None
        pivot = pivot[sorted(pivot.columns)]

        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=months[:len(pivot.columns)],
            y=[str(y) for y in pivot.index],
            text=[[f"{v:.1f}%" if pd.notna(v) else "" for v in row] for row in pivot.values],
            texttemplate="%{text}",
            colorscale="RdYlGn",
            zmid=0,
        ))
        fig.update_layout(
            title="月度收益热力图 (%)",
            height=300,
        )
        return fig

    @staticmethod
    def returns_distribution(daily_returns: List[dict]) -> go.Figure:
        """日收益分布直方图"""
        if len(daily_returns) < 2:
            return go.Figure()

        df = pd.DataFrame(daily_returns)
        # 计算日变化
        returns = []
        prev = None
        for _, row in df.iterrows():
            if prev is not None and prev > 0:
                returns.append((row["total_value"] - prev) / prev * 100)
            prev = row["total_value"]

        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=returns, nbinsx=30,
            marker_color="#1f77b4",
            name="日收益分布"
        ))
        fig.update_layout(
            title="日收益分布",
            xaxis_title="日收益 (%)",
            yaxis_title="频次",
            height=300,
        )
        return fig

    @staticmethod
    def drawdown_chart(daily_returns: List[dict]) -> go.Figure:
        """回撤曲线"""
        if not daily_returns:
            return go.Figure()

        df = pd.DataFrame(daily_returns)
        cummax = df["total_value"].cummax()
        drawdown = (df["total_value"] - cummax) / cummax * 100

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(df["date"]), y=drawdown,
            mode="lines", name="回撤(%)",
            line=dict(color="#d62728", width=1),
            fill="tozerox",
            fillcolor="rgba(214, 39, 40, 0.2)",
        ))
        fig.update_layout(
            title="回撤曲线",
            xaxis_title="日期",
            yaxis_title="回撤 (%)",
            height=300,
        )
        return fig

    @staticmethod
    def summary_cards(summary: dict) -> str:
        """生成指标卡片的 HTML"""
        if not summary:
            return ""
        return summary  # Streamlit 直接渲染 metric
