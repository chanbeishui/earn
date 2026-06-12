"""策略构建器 — 可视化组装量化策略"""
import streamlit as st
import requests
import json
import copy

API_BASE = "http://127.0.0.1:8000"


def show():
    st.title("🧩 策略构建器")
    st.markdown("可视化组装你的量化策略：选择因子 → 配置择时 → 设置仓位 → 保存运行")

    # 初始化 session state
    defaults = {
        "strategy_name": "",
        "strategy_desc": "",
        "selected_factors": {},  # {name: {display, weight, params}}
        "buy_signals": [],        # [{type, params}]
        "sell_signals": [],       # [{type, params}]
        "filters": [],            # [{type, params}]
        "position_type": "equal_weight",
        "position_max_stocks": 10,
        "editing_id": None,       # 编辑模式下的策略 ID
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # 加载注册表
    registry = _load_registry()
    if not registry:
        st.error("无法加载因子注册表，请确认 API 后端已启动")
        return

    # 三列布局
    left, right = st.columns([3, 2])

    with left:
        _show_factor_section(registry)
        st.markdown("---")
        _show_signal_section(registry)
        st.markdown("---")
        _show_filter_section(registry)
        st.markdown("---")
        _show_position_section(registry)

    with right:
        _show_preview()
        st.markdown("---")
        _show_save_section()


def _load_registry():
    """加载因子注册表"""
    try:
        resp = requests.get(f"{API_BASE}/api/data/factors", timeout=5)
        if resp.status_code == 200:
            return resp.json()["data"]
    except Exception:
        pass
    return None


def _show_factor_section(registry):
    """因子选择区"""
    st.subheader("📊 因子选择")
    st.caption("勾选要使用的因子，设置权重（权重和自动归一化）")

    factors = registry.get("factors", [])
    categories = {"technical": "🔧 技术因子", "fundamental": "📈 基本面因子", "composite": "🧩 复合因子"}

    for cat, label in categories.items():
        cat_factors = [f for f in factors if f.get("category") == cat]
        if not cat_factors:
            continue

        with st.expander(label, expanded=(cat == "technical")):
            for f in cat_factors:
                name = f["name"]
                display = f.get("display", name)
                key = f"factor_{name}"

                cols = st.columns([2, 2])
                with cols[0]:
                    checked = st.checkbox(display, key=key, value=name in st.session_state.selected_factors)
                with cols[1]:
                    st.caption(f.get("description", ""))
                with cols[2]:
                    weight = st.number_input(
                        "权重", min_value=0.0, max_value=1.0, value=0.3, step=0.05,
                        key=f"weight_{name}",
                        disabled=not checked
                    )

                if checked:
                    if name not in st.session_state.selected_factors:
                        st.session_state.selected_factors[name] = {
                            "name": name, "display": display,
                            "weight": weight, "params": {}
                        }
                    else:
                        st.session_state.selected_factors[name]["weight"] = weight
                else:
                    st.session_state.selected_factors.pop(name, None)


def _show_signal_section(registry):
    """择时信号区"""
    st.subheader("📈 择时规则")

    # 买入信号
    st.markdown("##### 🟢 买入信号")
    buy_types = registry.get("buy_signals", [])
    _render_signal_config("buy", buy_types)

    st.markdown("---")

    # 卖出信号
    st.markdown("##### 🔴 卖出信号")
    sell_types = registry.get("sell_signals", [])
    _render_signal_config("sell", sell_types)


def _render_signal_config(direction, signal_types):
    """渲染信号配置表单"""
    existing = st.session_state.buy_signals if direction == "buy" else st.session_state.sell_signals
    key_prefix = f"{direction}_sig"

    # 已有信号
    for idx, sig in enumerate(existing):
        with st.container(border=True):
            cols = st.columns([3, 1])
            with cols[0]:
                sig_type = sig.get("type", "")
                st.caption(f"信号 {idx + 1}: **{sig_type}**")
                for pname, pval in sig.get("params", {}).items():
                    new_val = st.text_input(
                        f"{pname}", value=str(pval),
                        key=f"{key_prefix}_{idx}_{pname}"
                    )
                    try:
                        existing[idx]["params"][pname] = float(new_val) if "." in new_val else int(new_val)
                    except ValueError:
                        existing[idx]["params"][pname] = new_val
            with cols[1]:
                if st.button("删除", key=f"del_{key_prefix}_{idx}"):
                    existing.pop(idx)
                    st.rerun()

    # 添加新信号
    if signal_types:
        sig_names = [s["type"] for s in signal_types]
        sig_displays = {s["type"]: f"{s['display']}" for s in signal_types}
        selected = st.selectbox(
            f"添加{'买入' if direction == 'buy' else '卖出'}信号",
            options=[""] + sig_names,
            format_func=lambda x: "选择信号类型..." if x == "" else sig_displays.get(x, x),
            key=f"add_{key_prefix}"
        )
        if selected:
            info = next((s for s in signal_types if s["type"] == selected), None)
            if info:
                new_sig = {"type": selected, "params": {}}
                for p in info.get("params", []):
                    new_sig["params"][p["name"]] = p.get("default", 0)
                existing.append(new_sig)
                st.rerun()


def _show_filter_section(registry):
    """过滤器区"""
    st.subheader("🔍 过滤器")
    st.caption("排除不符合条件的股票")

    filters = registry.get("filters", [])
    existing = st.session_state.filters

    for f in filters:
        ftype = f["type"]
        display = f.get("display", ftype)
        active_types = [x["type"] for x in existing]
        checked = ftype in active_types

        new_checked = st.checkbox(display, value=checked, key=f"filter_{ftype}")

        if new_checked and ftype not in active_types:
            new_filter = {"type": ftype, "params": {}}
            for p in f.get("params", []):
                new_filter["params"][p["name"]] = p.get("default", 0)
            existing.append(new_filter)
        elif not new_checked and ftype in active_types:
            existing[:] = [x for x in existing if x["type"] != ftype]

        # 参数
        if new_checked:
            current = next((x for x in existing if x["type"] == ftype), None)
            if current:
                for p in f.get("params", []):
                    val = st.number_input(
                        p.get("display", p["name"]),
                        value=float(current["params"].get(p["name"], p.get("default", 0))),
                        key=f"filter_param_{ftype}_{p['name']}",
                        step=10.0 if p.get("type") == "float" else 1.0
                    )
                    current["params"][p["name"]] = val


def _show_position_section(registry):
    """仓位规则区"""
    st.subheader("💰 仓位规则")

    rules = registry.get("position_rules", [])
    rule_types = [r["type"] for r in rules]
    rule_labels = {r["type"]: r["display"] for r in rules}

    current = st.session_state.position_type
    selected = st.selectbox(
        "仓位分配方式",
        options=rule_types,
        format_func=lambda x: rule_labels.get(x, x),
        index=rule_types.index(current) if current in rule_types else 0,
        key="position_rule_select"
    )
    st.session_state.position_type = selected

    st.session_state.position_max_stocks = st.slider(
        "最大持仓数", min_value=1, max_value=50,
        value=st.session_state.position_max_stocks
    )


def _show_preview():
    """实时 JSON 预览"""
    st.subheader("👁️ 配置预览")

    config = _build_config()
    st.code(json.dumps(config, ensure_ascii=False, indent=2), language="json")

    # 验证
    if config["factors"]:
        total_w = sum(f["weight"] for f in config["factors"])
        if total_w > 0:
            st.caption(f"因子权重总和: {total_w:.2f}")
        else:
            st.warning("⚠️ 因子权重总和为 0，请调整权重")


def _build_config():
    """根据 session state 构建策略 JSON"""
    factors = []
    for name, info in st.session_state.selected_factors.items():
        factors.append({
            "name": name,
            "weight": info.get("weight", 0),
            "params": info.get("params", {}),
        })

    # 归一化权重
    total = sum(f["weight"] for f in factors)
    if total > 0:
        for f in factors:
            f["weight"] = round(f["weight"] / total, 4)

    config = {
        "name": st.session_state.strategy_name or "未命名策略",
        "description": st.session_state.strategy_desc,
        "factors": factors,
        "timing": {
            "buy_signals": copy.deepcopy(st.session_state.buy_signals),
            "sell_signals": copy.deepcopy(st.session_state.sell_signals),
        },
        "filters": copy.deepcopy(st.session_state.filters),
        "position": {
            "type": st.session_state.position_type,
            "max_stocks": st.session_state.position_max_stocks,
        }
    }
    return config


def _show_save_section():
    """保存操作区"""
    st.subheader("💾 保存策略")

    st.session_state.strategy_name = st.text_input(
        "策略名称", value=st.session_state.strategy_name, placeholder="输入策略名称"
    )
    st.session_state.strategy_desc = st.text_area(
        "策略描述", value=st.session_state.strategy_desc, placeholder="简要描述策略逻辑"
    )

    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("💾 保存策略", type="primary", use_container_width=True):
            config = _build_config()
            name = st.session_state.strategy_name.strip()
            if not name:
                st.error("请输入策略名称")
                return

            # 验证
            from strategy.composer import StrategyComposer
            ok, msg = StrategyComposer.validate_config(config)
            if not ok:
                st.error(f"配置无效: {msg}")
                return

            try:
                resp = requests.post(
                    f"{API_BASE}/api/strategies",
                    json={"name": name, "config": config,
                          "description": st.session_state.strategy_desc}
                )
                if resp.status_code == 200:
                    sid = resp.json()["data"]["id"]
                    st.success(f"策略已保存 (ID: {sid})")
                    st.session_state.editing_id = sid
                else:
                    st.error(f"保存失败: {resp.json().get('msg', resp.text)}")
            except Exception as e:
                st.error(f"无法连接后端: {e}")

    with col_b:
        if st.button("🧹 清空重来", use_container_width=True):
            for k in list(st.session_state.keys()):
                if k in ("selected_factors", "buy_signals", "sell_signals",
                         "filters", "strategy_name", "strategy_desc",
                         "editing_id", "position_type", "position_max_stocks"):
                    if isinstance(st.session_state[k], dict):
                        st.session_state[k] = {}
                    elif isinstance(st.session_state[k], list):
                        st.session_state[k] = []
                    else:
                        st.session_state[k] = "" if isinstance(st.session_state[k], str) else (
                            10 if k == "position_max_stocks" else "equal_weight" if k == "position_type" else None
                        )
            st.rerun()

    # 快速回测入口
    if st.session_state.get("editing_id"):
        st.markdown("---")
        if st.button("🧪 快速回测", use_container_width=True):
            st.session_state["nav"] = "📊 回测中心"
            st.rerun()
