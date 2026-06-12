"""数据中心页面"""
import streamlit as st
import requests
import pandas as pd
from datetime import datetime

API_BASE = "http://127.0.0.1:8000"


def show():
    st.title("📥 数据中心")
    st.markdown("管理数据下载、查看数据概览和下载日志")

    tab1, tab2, tab3 = st.tabs(["📥 下载管理", "📋 下载日志", "📊 数据概览"])

    with tab1:
        _show_download_tab()
    with tab2:
        _show_logs_tab()
    with tab3:
        _show_overview_tab()


def _show_download_tab():
    st.subheader("数据下载")

    col1, col2 = st.columns([2, 1])

    with col1:
        data_type = st.selectbox(
            "选择下载内容",
            options=["daily_kline", "stock_basic", "financial"],
            format_func=lambda x: {
                "daily_kline": "日K线数据",
                "stock_basic": "股票基本信息",
                "financial": "财务数据",
            }.get(x, x),
        )

        if st.button("🚀 开始下载", type="primary", use_container_width=True):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/data/download",
                    params={"data_type": data_type}
                )
                if resp.status_code == 200:
                    st.success(f"下载任务已启动 (日志ID: {resp.json()['data']['log_id']})")
                    st.rerun()
                else:
                    st.error(f"请求失败: {resp.text}")
            except Exception as e:
                st.error(f"无法连接后端服务: {e}")
                st.info("请先启动 FastAPI 后端: `uvicorn api.server:app --port 8000`")

    with col2:
        st.subheader("⏳ 下载进度")
        try:
            resp = requests.get(f"{API_BASE}/api/data/status", timeout=3)
            if resp.status_code == 200:
                progress = resp.json()["data"]
                if progress.get("running"):
                    total = progress.get("total", 1) or 1
                    current = progress.get("current", 0)
                    st.progress(current / total)
                    st.caption(progress.get("msg", ""))
                else:
                    st.info("当前无下载任务")
        except Exception:
            st.info("无法获取进度")

    st.markdown("---")
    st.subheader("⚙️ 下载配置")

    col_a, col_b = st.columns(2)
    with col_a:
        st.checkbox("日K线下载", value=True, disabled=True)
        st.checkbox("分钟线下载", value=False, disabled=True)
        st.selectbox("分钟线频率", ["1min", "5min", "15min", "30min", "60min"],
                     disabled=True)
    with col_b:
        st.checkbox("财务数据", value=True, disabled=True)
        st.number_input("分钟线保留年数", value=3, disabled=True)
        st.text_input("定时下载时间", value="15:30", disabled=True)
    st.caption("配置功能将在后续版本中开放编辑")


def _show_logs_tab():
    st.subheader("下载日志")

    try:
        resp = requests.get(f"{API_BASE}/api/data/logs", params={"limit": 50}, timeout=5)
        if resp.status_code == 200:
            logs = resp.json()["data"]
            if logs:
                df = pd.DataFrame(logs)
                df["data_type"] = df["data_type"].replace({
                    "daily_kline": "日K线", "stock_basic": "股票列表", "financial": "财务数据"
                })
                df["status"] = df["status"].replace({
                    "done": "✅ 完成", "running": "⏳ 运行中", "failed": "❌ 失败", "pending": "⏸️ 等待"
                })
                st.dataframe(
                    df[["id", "data_type", "status", "total_count", "success_count", "start_time", "end_time"]],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("暂无下载日志")
    except Exception as e:
        st.warning(f"无法获取下载日志: {e}")


def _show_overview_tab():
    st.subheader("数据概览")

    try:
        resp = requests.get(f"{API_BASE}/api/data/overview", timeout=5)
        if resp.status_code == 200:
            data = resp.json()["data"]
        else:
            data = {}
    except Exception:
        data = {}

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("已下载股票", data.get("stock_count", 0))
    with col2:
        st.metric("数据最早日期", data.get("daily_start", "无"))
    with col3:
        st.metric("数据最新日期", data.get("daily_end", "无"))

    st.markdown("---")

    try:
        resp = requests.get(f"{API_BASE}/api/data/stocks", timeout=5)
        if resp.status_code == 200:
            stocks = resp.json()["data"]
            if stocks:
                df = pd.DataFrame(stocks)
                st.subheader(f"股票列表 (共 {len(stocks)} 只)")
                st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception:
        pass
