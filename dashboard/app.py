"""Streamlit Dashboard 主入口"""
import streamlit as st
import importlib
import traceback

st.set_page_config(
    page_title="Earn 量化交易系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 直接导入所有页面模块
from dashboard.pages import overview
from dashboard.pages import data_center
from dashboard.pages import strategy_builder
from dashboard.pages import strategy_list
from dashboard.pages import backtest_view
from dashboard.pages import ai_optimize
from dashboard.pages import pool


def main():
    st.sidebar.title("📈 Earn 量化交易系统")

    page = st.sidebar.radio(
        "导航",
        [
            "🏠 系统总览",
            "📥 数据中心",
            "🧩 策略构建器",
            "📋 策略列表",
            "📊 回测中心",
            "🧠 AI 优化",
            "⭐ 股票池",
        ],
        key="nav",
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("© 2025 Earn Quant System")
    st.sidebar.markdown(f"🔌 API: `http://127.0.0.1:8000`")

    # 路由
    pages = {
        "🏠 系统总览": overview,
        "📥 数据中心": data_center,
        "🧩 策略构建器": strategy_builder,
        "📋 策略列表": strategy_list,
        "📊 回测中心": backtest_view,
        "🧠 AI 优化": ai_optimize,
        "⭐ 股票池": pool,
    }

    page_module = pages.get(page)
    if page_module:
        try:
            page_module.show()
        except Exception as e:
            st.error(f"**页面加载失败**: {e}")
            with st.expander("详细错误信息"):
                st.code(traceback.format_exc())
    else:
        overview.show()


if __name__ == "__main__":
    main()
