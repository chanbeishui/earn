"""系统总览页面"""
import streamlit as st
import requests
import pandas as pd

API_BASE = "http://127.0.0.1:8000"


def show():
    st.title("🏠 系统总览")
    st.markdown("量化交易系统运行状态一览")

    try:
        resp = requests.get(f"{API_BASE}/api/overview", timeout=5)
        if resp.status_code == 200:
            data = resp.json()["data"]
        else:
            data = {}
    except Exception:
        data = {}

    # 状态卡片
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "📊 已下载股票",
            value=data.get("stock_count", 0),
            delta=None,
        )
    with col2:
        daily_end = data.get("daily_end", "无")
        st.metric("📅 最新数据日期", value=daily_end or "暂无")
    with col3:
        st.metric("🧩 策略数量", value=data.get("strategy_count", 0))
    with col4:
        qmt_ok = "✅ 已连接" if data.get("qmt_available") else "⚠️ 模拟模式"
        st.metric("🔌 QMT 状态", value=qmt_ok)

    st.markdown("---")

    # 数据覆盖情况
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📥 数据覆盖")
        if data.get("daily_start") and data.get("daily_end"):
            st.write(f"日K线: {data['daily_start']} ~ {data['daily_end']}")
        if data.get("data_size_mb"):
            st.write(f"数据总量: {data['data_size_mb']} MB")
        st.write(f"最近下载: {data.get('last_download', '无')}")

    with col_right:
        st.subheader("🚀 快速入口")
        if st.button("📥 前往数据中心", use_container_width=True):
            st.session_state["nav"] = "📥 数据中心"
            st.rerun()
        if st.button("🧩 创建新策略", use_container_width=True):
            st.session_state["nav"] = "🧩 策略构建器"
            st.rerun()
        if st.button("📊 查看回测结果", use_container_width=True):
            st.session_state["nav"] = "📊 回测中心"
            st.rerun()

    # 下载进度
    progress = data.get("download_progress", {})
    if progress.get("running"):
        st.markdown("---")
        st.subheader("⏳ 正在下载...")
        total = progress.get("total", 1) or 1
        current = progress.get("current", 0)
        st.progress(current / total, text=progress.get("msg", ""))
