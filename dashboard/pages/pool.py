"""股票池管理页面"""
import streamlit as st
import requests
import pandas as pd

API_BASE = "http://127.0.0.1:8000"


def show():
    st.title("⭐ 股票池管理")

    tab1, tab2, tab3 = st.tabs(["📊 策略选股池", "⭐ 自选股", "🔀 池操作"])

    with tab1:
        _show_strategy_pool()
    with tab2:
        _show_watchlist()
    with tab3:
        _show_pool_ops()


def _show_strategy_pool():
    st.subheader("📊 策略选股池")
    st.caption("查看策略的每日选股结果")

    # 加载策略列表
    strategies = {}
    try:
        resp = requests.get(f"{API_BASE}/api/strategies", timeout=5)
        if resp.status_code == 200:
            strategies = {s["name"]: s["id"] for s in resp.json()["data"]}
    except Exception:
        pass

    if not strategies:
        st.info("请先在策略管理页面创建并运行策略")
        return

    col1, col2 = st.columns([2, 2])
    with col1:
        strategy_name = st.selectbox("策略", options=list(strategies.keys()), key="pool_strat")
        strategy_id = strategies[strategy_name]
    with col2:
        try:
            resp = requests.get(f"{API_BASE}/api/pool/strategy/dates/{strategy_id}", timeout=5)
            dates = resp.json()["data"] if resp.status_code == 200 else []
        except Exception:
            dates = []
        date = st.selectbox("日期", options=["最新"] + dates, key="pool_date")
        if date == "最新":
            date = ""

    # 加载结果
    try:
        import urllib.parse
        resp = requests.get(
            f"{API_BASE}/api/pool/strategy/pool?strategy_id={strategy_id}&date={date}",
            timeout=5
        )
        if resp.status_code == 200:
            results = resp.json()["data"]
        else:
            results = []
    except Exception:
        results = []

    if not results:
        st.info("该策略没有选股结果，请先运行策略选股")
        return

    st.caption(f"共 {len(results)} 只股票")

    # 表格
    df = pd.DataFrame(results)
    display_cols = ["code", "score", "signal"]
    extra_cols = [c for c in ["strategy_name", "date"] if c in df.columns]
    avail = [c for c in display_cols + extra_cols if c in df.columns]

    st.dataframe(df[avail], use_container_width=True, hide_index=True)

    # 选中股票详情
    if not df.empty:
        selected_code = st.selectbox("查看详情", options=df["code"].tolist())
        if selected_code:
            row = df[df["code"] == selected_code].iloc[0]
            with st.expander(f"{selected_code} 详情"):
                st.metric("综合得分", f'{row.get("score", "-"):.4f}')
                st.metric("信号", row.get("signal", "-"))
                if row.get("factor_scores"):
                    fs = row["factor_scores"]
                    fs_df = pd.DataFrame(list(fs.items()), columns=["因子", "得分"])
                    st.dataframe(fs_df, use_container_width=True, hide_index=True)

    # 批量导入自选
    if st.button("📥 批量导入自选股", use_container_width=True):
        try:
            resp = requests.post(
                f"{API_BASE}/api/pool/watchlist/batch",
                json={"codes": [{"code": r["code"]} for r in results], "tag": "strategy"}
            )
            if resp.status_code == 200:
                st.success(f'已导入 {len(results)} 只股票到自选股')
        except Exception as e:
            st.error(f"导入失败: {e}")


def _show_watchlist():
    st.subheader("⭐ 自选股管理")

    # 添加表单
    with st.expander("➕ 添加自选股"):
        col1, col2 = st.columns(2)
        with col1:
            code = st.text_input("股票代码", placeholder="如 000001.SZ")
        with col2:
            name = st.text_input("股票名称", placeholder="如 平安银行")
        tags = st.text_input("标签", placeholder="用逗号分隔，如: 观察,持有")
        note = st.text_area("备注", placeholder="记录一些笔记...")

        if st.button("添加", type="primary") and code.strip():
            try:
                resp = requests.post(
                    f"{API_BASE}/api/pool/watchlist",
                    json={"code": code.strip(), "name": name, "tags": tags, "note": note}
                )
                if resp.status_code == 200:
                    st.success(f"已添加 {code}")
                    st.rerun()
                else:
                    st.error(resp.json().get("msg", "添加失败"))
            except Exception as e:
                st.error(str(e))

    # 搜索
    search = st.text_input("🔍 搜索（代码/名称）", key="wl_search")

    # 标签过滤
    try:
        resp = requests.get(f"{API_BASE}/api/pool/watchlist/tags", timeout=5)
        all_tags = resp.json()["data"] if resp.status_code == 200 else []
    except Exception:
        all_tags = []

    tag_filter = st.multiselect("标签过滤", options=all_tags, key="wl_tag_filter")

    # 加载自选股
    try:
        if search:
            resp = requests.get(f"{API_BASE}/api/pool/watchlist?search={search}", timeout=5)
        elif tag_filter:
            resp = requests.get(f"{API_BASE}/api/pool/watchlist?tag={tag_filter[0]}", timeout=5)
        else:
            resp = requests.get(f"{API_BASE}/api/pool/watchlist", timeout=5)
        wl = resp.json()["data"] if resp.status_code == 200 else []
    except Exception:
        wl = []

    if not wl:
        st.info("暂无自选股，点击上方「添加」或从策略选股池批量导入")
        return

    wdf = pd.DataFrame(wl)

    # 标签页布局
    if tag_filter:
        filtered = wdf[wdf["tags"].str.contains(tag_filter[0], na=False)]
    else:
        filtered = wdf

    st.caption(f"共 {len(wl)} 只自选股")

    # 表格和操作
    for _, row in filtered.iterrows():
        with st.container(border=True):
            col_main, col_actions = st.columns([4, 1])

            with col_main:
                st.write(f"**{row['code']}** {row.get('name', '')}")
                if row.get("tags"):
                    for t in row["tags"].split(","):
                        t = t.strip()
                        if t:
                            st.badge(t)
                if row.get("note"):
                    st.caption(row["note"])
                st.caption(f"添加于 {row.get('added_at', '')}")

            with col_actions:
                if st.button("编辑", key=f"edit_{row['id']}"):
                    st.session_state[f"edit_wl_{row['id']}"] = True
                if st.button("删除", key=f"del_{row['id']}"):
                    try:
                        resp = requests.delete(
                            f"{API_BASE}/api/pool/watchlist/{row['id']}"
                        )
                        if resp.status_code == 200:
                            st.rerun()
                    except Exception as e:
                        st.error(str(e))

            # 编辑面板
            if st.session_state.get(f"edit_wl_{row['id']}"):
                new_tags = st.text_input("标签", value=row.get("tags", ""), key=f"tags_{row['id']}")
                new_note = st.text_area("备注", value=row.get("note", ""), key=f"note_{row['id']}")
                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.button("保存", key=f"save_{row['id']}"):
                        try:
                            requests.put(
                                f"{API_BASE}/api/pool/watchlist/{row['id']}",
                                json={"tags": new_tags, "note": new_note}
                            )
                            st.session_state[f"edit_wl_{row['id']}"] = False
                            st.rerun()
                        except Exception:
                            pass
                with col_cancel:
                    if st.button("取消", key=f"cancel_{row['id']}"):
                        st.session_state[f"edit_wl_{row['id']}"] = False
                        st.rerun()

    # 导出
    st.markdown("---")
    if st.button("📥 导出 CSV"):
        try:
            resp = requests.get(f"{API_BASE}/api/pool/export/csv", timeout=5)
            if resp.status_code == 200:
                csv = resp.json()["data"]
                st.download_button("下载 CSV", csv, "watchlist.csv", "text/csv")
        except Exception:
            pass


def _show_pool_ops():
    st.subheader("🔀 池操作")
    st.caption("对策略选股池和自选股池做集合运算")

    strategies = {}
    try:
        resp = requests.get(f"{API_BASE}/api/strategies", timeout=5)
        if resp.status_code == 200:
            strategies = {s["name"]: s["id"] for s in resp.json()["data"]}
    except Exception:
        pass

    if not strategies:
        st.info("请先创建策略")
        return

    strategy_name = st.selectbox("策略", options=list(strategies.keys()), key="pool_ops_strat")
    strategy_id = strategies[strategy_name]

    op = st.radio("操作", ["intersection", "union", "difference"],
                  format_func={
                      "intersection": "∩ 交集（既在选股池又在自选池）",
                      "union": "∪ 并集（选股池或自选池中任一）",
                      "difference": "− 差集（仅在选股池中，不在自选池）",
                  }.get)

    if st.button("执行", type="primary"):
        try:
            resp = requests.get(
                f"{API_BASE}/api/pool/ops/{op}?strategy_id={strategy_id}",
                timeout=5
            )
            if resp.status_code == 200:
                results = resp.json()["data"]
                if results:
                    st.success(f"结果: {len(results)} 只股票")
                    rdf = pd.DataFrame(results)
                    st.dataframe(rdf, use_container_width=True, hide_index=True)
                else:
                    st.info("结果为空")
        except Exception as e:
            st.error(str(e))
