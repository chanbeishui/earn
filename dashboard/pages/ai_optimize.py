"""AI 优化中心页面"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import json

API_BASE = "http://127.0.0.1:8000"


def show():
    st.title("🧠 AI 优化中心")
    st.markdown("参数优化（Optuna / 遗传算法）和深度学习预测训练")

    tab1, tab2, tab3 = st.tabs(["🎯 参数优化", "🧠 深度学习", "📋 任务历史"])

    with tab1:
        _show_optimize_tab()
    with tab2:
        _show_train_tab()
    with tab3:
        _show_history_tab()


def _show_optimize_tab():
    st.subheader("🎯 参数优化")
    st.caption("自动搜索策略的最优参数组合")

    # 加载策略
    strategies = _load_strategies()
    if not strategies:
        return

    strategy_name = st.selectbox("选择策略", options=list(strategies.keys()), key="ai_opt_strategy")
    method = st.radio("优化方法", ["optuna", "genetic"],
                      format_func=lambda x: "🔬 Optuna TPE 贝叶斯优化 (推荐)" if x == "optuna" else "🧬 遗传算法",
                      horizontal=True)
    n_trials = st.slider("试验次数", 50, 500, 100, 50)

    # 参数空间
    with st.expander("参数搜索空间（留空自动推断）"):
        st.caption("自定义参数空间: JSON 格式 {param_name: {type, low, high}}")
        param_text = st.text_area("参数空间", value="", height=100,
                                  placeholder='{"factors[0].weight": {"type":"float","low":0.1,"high":0.9}}')
        params = {}
        if param_text.strip():
            try:
                params = json.loads(param_text)
            except json.JSONDecodeError:
                st.error("JSON 格式错误")

    if st.button("🚀 开始优化", type="primary", use_container_width=True):
        sid = strategies[strategy_name]
        with st.spinner(f"优化中 ({method}, {n_trials} 轮)..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/ai/optimize",
                    json={
                        "strategy_id": sid,
                        "method": method,
                        "n_trials": n_trials,
                        "params": params,
                    },
                    timeout=600,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    task_id = data["data"]["task_id"]

                    # 获取详细结果
                    resp2 = requests.get(f"{API_BASE}/api/ai/optimize/{task_id}")
                    if resp2.status_code == 200:
                        result = resp2.json()["data"]
                        _show_optimize_result(result)
                else:
                    st.error(resp.json().get("msg", "优化失败"))
            except Exception as e:
                st.error(f"优化失败: {e}")


def _show_optimize_result(result: dict):
    """展示优化结果"""
    st.success("✅ 优化完成!")
    st.markdown("---")

    best = result.get("best_params", {})
    best_score = result.get("best_score", 0)
    history = result.get("history", [])
    importances = result.get("param_importances", {})

    # 最优参数
    st.subheader("🏆 最优参数")
    cols = st.columns(min(len(best), 4))
    for i, (k, v) in enumerate(best.items()):
        cols[i % 4].metric(k, f"{v}")

    st.metric("最优得分 (夏普)", f"{best_score:.4f}")

    # 参数重要性
    if importances:
        st.subheader("📊 参数重要性")
        fig = go.Figure(go.Bar(
            x=list(importances.values()),
            y=list(importances.keys()),
            orientation="h",
        ))
        fig.update_layout(height=200, xaxis_title="重要性")
        st.plotly_chart(fig, use_container_width=True)

    # 优化历史
    if history:
        st.subheader("📈 优化历史")
        hdf = pd.DataFrame(history)
        if "score" in hdf.columns:
            fig2 = go.Figure()
            if "generation" in hdf.columns:
                fig2.add_trace(go.Scatter(
                    x=hdf.index, y=hdf["score"], mode="markers",
                    marker=dict(color=hdf["generation"], colorscale="Viridis"),
                    text=[f"Gen:{g}" for g in hdf.get("generation", [])],
                ))
            else:
                fig2.add_trace(go.Scatter(
                    x=hdf.index, y=hdf["score"], mode="markers",
                    name="每次试验得分",
                ))
            # 累积最优
            cummax = hdf["score"].cummax()
            fig2.add_trace(go.Scatter(
                x=hdf.index, y=cummax, mode="lines",
                name="累积最优", line=dict(color="red", dash="dash"),
            ))
            fig2.update_layout(height=400, xaxis_title="试验", yaxis_title="得分(夏普)")
            st.plotly_chart(fig2, use_container_width=True)


def _show_train_tab():
    st.subheader("🧠 深度学习训练")
    st.caption("训练 LSTM / Transformer 预测模型")

    model_type = st.selectbox("模型", ["lstm", "transformer"],
                              format_func=lambda x: "LSTM (推荐)" if x == "lstm" else "Transformer")

    col1, col2, col3 = st.columns(3)
    with col1:
        lookback = st.number_input("回溯天数", 20, 200, 60, 10)
    with col2:
        forecast = st.number_input("预测天数", 1, 30, 5)
    with col3:
        epochs = st.number_input("训练轮数", 10, 200, 50, 10)

    batch_size = st.slider("Batch Size", 16, 256, 64, 16)

    col4, col5 = st.columns(2)
    with col4:
        start_date = st.date_input("训练起始", value=pd.Timestamp("2020-01-01"), key="dl_start")
    with col5:
        end_date = st.date_input("训练截止", value=pd.Timestamp("2025-01-01"), key="dl_end")

    if st.button("🚀 开始训练", type="primary", use_container_width=True):
        with st.spinner(f"训练 {model_type.upper()} 中..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/ai/train",
                    json={
                        "model": model_type,
                        "lookback": lookback,
                        "forecast": forecast,
                        "epochs": epochs,
                        "batch_size": batch_size,
                        "start_date": str(start_date),
                        "end_date": str(end_date),
                    },
                    timeout=600,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    task_id = data["data"]["task_id"]
                    resp2 = requests.get(f"{API_BASE}/api/ai/train/{task_id}")
                    if resp2.status_code == 200:
                        result = resp2.json()["data"]
                        _show_train_result(result)
                else:
                    st.error(resp.json().get("msg", "训练失败"))
            except Exception as e:
                st.error(f"训练失败: {e}")


def _show_train_result(result: dict):
    """展示训练结果"""
    st.success("✅ 训练完成!")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    col1.metric("训练轮数", result.get("epochs_trained", 0))
    col2.metric("最佳验证Loss", f"{result.get('best_val_loss', 0):.4f}")
    col3.metric("样本数", result.get("n_samples", 0))

    # Loss 曲线
    train_loss = result.get("train_loss", [])
    val_loss = result.get("val_loss", [])
    if train_loss:
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=train_loss, mode="lines", name="训练Loss"))
        if val_loss:
            fig.add_trace(go.Scatter(y=val_loss, mode="lines", name="验证Loss"))
        fig.update_layout(height=400, xaxis_title="Epoch", yaxis_title="Loss",
                          title="训练 Loss 曲线")
        st.plotly_chart(fig, use_container_width=True)


def _show_history_tab():
    st.subheader("📋 任务历史")
    try:
        resp = requests.get(f"{API_BASE}/api/ai/tasks", timeout=5)
        if resp.status_code == 200:
            tasks = resp.json()["data"]
            if tasks:
                tdf = pd.DataFrame(tasks)
                st.dataframe(tdf, use_container_width=True, hide_index=True)
            else:
                st.info("暂无 AI 任务记录")
    except Exception:
        pass


def _load_strategies() -> dict:
    try:
        resp = requests.get(f"{API_BASE}/api/strategies", timeout=5)
        if resp.status_code == 200:
            return {s["name"]: s["id"] for s in resp.json()["data"]}
    except Exception:
        pass
    st.warning("请先在策略管理页面创建策略")
    return {}
