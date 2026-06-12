"""回测中心页面"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import json

API_BASE = "http://127.0.0.1:8000"


def show():
    st.title("📊 回测中心")

    # 初始化 session state
    if "bt_task_id" not in st.session_state:
        st.session_state.bt_task_id = None
    if "bt_result" not in st.session_state:
        st.session_state.bt_result = None

    col_config, col_result = st.columns([1, 2])

    with col_config:
        _show_config_panel()

    with col_result:
        if st.session_state.bt_result:
            _show_results(st.session_state.bt_result)
        else:
            st.info("👈 配置回测参数后点击「运行回测」")
            _show_history()


def _show_config_panel():
    """回测配置面板"""
    st.subheader("⚙️ 回测配置")

    # 加载策略列表
    strategies = []
    try:
        resp = requests.get(f"{API_BASE}/api/strategies", timeout=5)
        if resp.status_code == 200:
            strategies = resp.json()["data"]
    except Exception:
        pass

    strategy_options = {s["name"]: s["id"] for s in strategies}
    if not strategy_options:
        st.warning("请先在策略管理页面创建策略")
        return

    selected_name = st.selectbox("选择策略", options=list(strategy_options.keys()))
    strategy_id = strategy_options[selected_name]

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", value=pd.Timestamp("2020-01-01"))
    with col2:
        end_date = st.date_input("结束日期", value=pd.Timestamp("2025-12-31"))

    initial_capital = st.number_input(
        "初始资金", value=1_000_000, step=100000, format="%d"
    )

    col3, col4 = st.columns(2)
    with col3:
        commission = st.number_input("佣金费率", value=0.00025, format="%.5f",
                                     help="默认万2.5")
    with col4:
        stamp_duty = st.number_input("印花税", value=0.001, format="%.4f",
                                     help="卖出时千1")

    if st.button("🚀 运行回测", type="primary", use_container_width=True):
        with st.spinner("回测运行中..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/backtest/run",
                    json={
                        "strategy_id": strategy_id,
                        "start_date": str(start_date),
                        "end_date": str(end_date),
                        "initial_capital": initial_capital,
                        "commission": commission,
                        "stamp_duty": stamp_duty,
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    task_id = data["data"]["task_id"]

                    # 获取详细结果
                    resp2 = requests.get(f"{API_BASE}/api/backtest/{task_id}")
                    if resp2.status_code == 200:
                        st.session_state.bt_result = resp2.json()["data"]
                        st.session_state.bt_task_id = task_id
                        st.rerun()
                else:
                    st.error(resp.json().get("msg", "回测失败"))
            except Exception as e:
                st.error(f"无法连接后端: {e}")


def _show_results(data: dict):
    """展示回测结果"""
    summary = data.get("summary", {})
    daily = data.get("daily_returns", [])
    monthly = data.get("monthly_returns", [])
    trades = data.get("trades", [])

    st.subheader("📈 回测结果")

    # === 指标卡片 ===
    cols = st.columns(5)
    metrics = [
        ("累计收益", f"{summary.get('total_return_pct', 0):.2f}%"),
        ("年化收益", f"{summary.get('annual_return_pct', 0):.2f}%"),
        ("夏普比率", f"{summary.get('sharpe_ratio', 0):.3f}"),
        ("最大回撤", f"{summary.get('max_drawdown_pct', 0):.2f}%"),
        ("胜率", f"{summary.get('win_rate_pct', 0):.1f}%"),
    ]
    for i, (label, value) in enumerate(metrics):
        cols[i].metric(label, value)

    cols2 = st.columns(5)
    metrics2 = [
        ("超额收益", f"{summary.get('excess_return_pct', 0):.2f}%"),
        ("基准收益", f"{summary.get('benchmark_return_pct', 0):.2f}%"),
        ("交易次数", f"{summary.get('total_trades', 0)}"),
        ("最终资产", f"{summary.get('final_value', 0):,.0f}"),
        ("换手率", f"{summary.get('turnover', 0):.2f}"),
    ]
    for i, (label, value) in enumerate(metrics2):
        cols2[i].metric(label, value)

    st.markdown("---")

    # === 收益曲线 ===
    st.subheader("📈 累计收益曲线")
    if daily:
        df = pd.DataFrame(daily)
        df["date"] = pd.to_datetime(df["date"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["cum_return"],
            mode="lines", name="策略收益(%)",
            line=dict(color="#1f77b4", width=2),
            fill="tozeroy", fillcolor="rgba(31,119,180,0.1)",
        ))
        fig.update_layout(height=400, hovermode="x unified",
                          xaxis_title="日期", yaxis_title="累计收益(%)")
        st.plotly_chart(fig, use_container_width=True)

    # === 回撤 + 月度热力图 ===
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("📉 回撤曲线")
        if daily:
            df = pd.DataFrame(daily)
            df["date"] = pd.to_datetime(df["date"])
            cummax = df["total_value"].cummax()
            drawdown = (df["total_value"] - cummax) / cummax * 100
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df["date"], y=drawdown, mode="lines",
                line=dict(color="#d62728", width=1),
                fill="tozerox", fillcolor="rgba(214,39,40,0.2)",
            ))
            fig2.update_layout(height=300, xaxis_title="日期", yaxis_title="回撤(%)")
            st.plotly_chart(fig2, use_container_width=True)

    with col_b:
        st.subheader("🗓️ 月度收益热力图")
        if monthly:
            mdf = pd.DataFrame(monthly)
            pivot = mdf.pivot(index="year", columns="month", values="return_pct")
            # 确保所有月份
            for m in range(1, 13):
                if m not in pivot.columns:
                    pivot[m] = 0
            pivot = pivot[sorted(pivot.columns)]
            months = ["1月","2月","3月","4月","5月","6月",
                      "7月","8月","9月","10月","11月","12月"]
            fig3 = go.Figure(data=go.Heatmap(
                z=pivot.values, x=months, y=[str(y) for y in pivot.index],
                text=[[f"{v:.1f}%" if v != 0 else "" for v in row] for row in pivot.values],
                texttemplate="%{text}", colorscale="RdYlGn", zmid=0,
            ))
            fig3.update_layout(height=300)
            st.plotly_chart(fig3, use_container_width=True)

    # === 交易明细 ===
    st.markdown("---")
    st.subheader("📋 交易明细")
    if trades:
        tdf = pd.DataFrame(trades)
        display_cols = ["date", "code", "direction", "price", "volume", "amount", "commission"]
        avail = [c for c in display_cols if c in tdf.columns]
        if "direction" in tdf.columns:
            tdf["direction"] = tdf["direction"].replace({"buy": "🟢买入", "sell": "🔴卖出"})
        st.dataframe(tdf[avail], use_container_width=True, hide_index=True)

        # 导出 CSV
        csv = tdf.to_csv(index=False).encode("utf-8")
        st.download_button("📥 导出交易明细 CSV", csv, "trades.csv", "text/csv")
    else:
        st.caption("无交易记录")


def _show_history():
    """历史回测记录"""
    st.markdown("---")
    st.subheader("🏆 历史回测记录")
    try:
        resp = requests.get(f"{API_BASE}/api/backtest/history", timeout=5)
        if resp.status_code == 200:
            history = resp.json()["data"]
            if history:
                hdf = pd.DataFrame(history)
                st.dataframe(hdf, use_container_width=True, hide_index=True)
            else:
                st.caption("暂无历史记录，运行一次回测后这里会显示")
    except Exception:
        pass
