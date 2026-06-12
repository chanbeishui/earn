"""策略列表页面 — Phase 2 完整实现"""
import streamlit as st
import requests
import pandas as pd

API_BASE = "http://127.0.0.1:8000"


def show():
    st.title("📋 策略列表")
    st.markdown("管理所有已保存的量化策略")

    # 加载策略列表
    try:
        resp = requests.get(f"{API_BASE}/api/strategies", timeout=5)
        if resp.status_code == 200:
            strategies = resp.json()["data"]
        else:
            strategies = []
    except Exception:
        strategies = []

    # 新建策略按钮
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("➕ 新建策略", type="primary", use_container_width=True):
            st.session_state["nav"] = "🧩 策略构建器"
            st.rerun()

    if not strategies:
        st.info("还没有策略，点击「新建策略」开始创建你的第一个量化策略！")
        return

    # 策略表格
    for s in strategies:
        with st.expander(f"{'✅' if s['is_enabled'] else '⭕'} {s['name']}  (ID:{s['id']})"):
            col_a, col_b, col_c = st.columns([3, 1, 1])

            with col_a:
                if s.get("description"):
                    st.caption(s["description"])
                st.caption(f"创建时间: {s.get('created_at', '未知')}")

            with col_b:
                btn_text = "停用" if s["is_enabled"] else "启用"
                if st.button(btn_text, key=f"toggle_{s['id']}"):
                    try:
                        requests.post(f"{API_BASE}/api/strategies/{s['id']}/toggle")
                        st.rerun()
                    except Exception:
                        st.error("操作失败")

            with col_c:
                if st.button("删除", key=f"del_{s['id']}"):
                    try:
                        requests.delete(f"{API_BASE}/api/strategies/{s['id']}")
                        st.rerun()
                    except Exception:
                        st.error("删除失败")

            # 显示因子
            if s.get("config"):
                config = s["config"]
                factors = config.get("factors", [])
                if factors:
                    factor_names = [f"{f['name']}({f.get('weight', 0)})" for f in factors]
                    st.text("因子: " + ", ".join(factor_names))
