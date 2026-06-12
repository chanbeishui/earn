# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 启动命令

```bash
# 后端 (Python 3.11 — QMT xtquant 依赖)
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

# 前端
streamlit run dashboard/app.py --server.headless true

# 仅下载数据
python scripts/download_data.py
```

API 文档自动生成在 http://localhost:8000/docs。

## 架构概览

```
core.py                 # 全局单例: storage, downloader, scheduler
config/__init__.py      # Pydantic Settings 加载 settings.yaml + .env
config/factor_registry.yaml  # 因子/择时/过滤器/仓位规则的元数据注册表

data/                   # 模块一: 数据
  downloader.py         #   QMT xtquant 封装 (不可用时自动 mock)
  storage.py            #   SQLite + Parquet 读写层
  scheduler.py          #   APScheduler 定时任务
  schema.py             #   SQLAlchemy ORM 模型 (8张表)

strategy/               # 模块二: 策略
  config_strategy.py    #   ConfigStrategy: 读取 JSON 配置, 动态组合因子+择时
  composer.py           #   StrategyComposer: 表单→JSON + 验证
  selector.py           #   StockSelector: 执行选股, 保存结果
  factors/manager.py    #   FactorManager 工厂 (17个注册因子)
  timing/manager.py     #   TimingManager 工厂 (10种注册信号)

backtest/               # 模块三: 回测
  engine.py             #   事件驱动主循环 (卖出→买入→更新持仓→快照)
  broker.py             #   佣金万2.5 + 印花税千1 + 滑点
  portfolio.py          #   持仓 + 资金管理
  analyzer.py           #   夏普/回撤/胜率/IC

ai/                     # 模块四: AI
  optimizer/optuna_optimizer.py  # TPE 贝叶斯参数搜索
  predictor/trainer.py           # LSTM/Transformer 训练管理器

pool/manager.py         # 模块五: 股票池 (选股池 + 自选股 + 集合运算)

dashboard/pages/        # Streamlit 前端 (7个页面)
  strategy_builder.py   #   核心: 可视化策略组装
  backtest_view.py      #   回测配置+结果
  ai_optimize.py        #   参数优化+深度学习
  pool.py               #   选股池+自选股
```

## 关键设计

1. **策略是 JSON 配置，不是 Python 代码**。用户在 `strategy_builder.py` 前端勾选因子/择时/过滤器，生成 JSON 存入 `strategy_definitions` 表，运行时由 `ConfigStrategy` 解析执行。验证用 `StrategyComposer.validate_config()`。

2. **全局实例**。`core.py` 创建 `storage`/`downloader`/`scheduler` 单例，所有 API 路由通过 `from core import storage` 引用，避免循环导入。

3. **懒加载 AI 模块**。`api/routes/ai.py` 和 `api/routes/backtest.py` 中的 `import optuna/torch/scipy` 都在函数内执行，不在模块顶层导入——因为 PyTorch 太大且不是启动必须。

4. **QMT xtquant 依赖 Python 3.11**。`.pyd` 文件最高支持 cp311。`DataDownloader._init_xtquant()` 在 xtquant 不可用时自动降级为 mock 模式。QMT 客户端必须**正在运行**才能获取真实数据（xtquant 连接到运行中的客户端）。

5. **Streamlit 直接导入页面模块**。`dashboard/app.py` 在顶部导入所有 7 个页面模块，使用侧边栏 `st.radio` 切换。

## 数据库

SQLite (`data/market.db`) + Parquet (`data/kline/`)。K 线按股票代码分文件存储。`DataStorage` 封装所有读写，`_StrategyCRUD` 内部类处理策略的增删改查。

## 策略 JSON 结构

```json
{
  "name": "...",
  "factors": [{"name": "rsi", "weight": 0.5, "params": {}}],
  "timing": {
    "buy_signals": [{"type": "ma_cross", "params": {"fast": 5, "slow": 20, "direction": "up"}}],
    "sell_signals": [{"type": "stop_loss", "params": {"percent": -8}}]
  },
  "filters": [{"type": "exclude_st", "params": {}}],
  "position": {"type": "equal_weight", "max_stocks": 10}
}
```

## 修改策略构建器注意事项

`strategy_builder.py` 是核心前端页面，session_state 状态复杂：
- `selected_factors` — `{name: {weight, params}}`
- `buy_signals`, `sell_signals` — `[{type, params}]` 列表
- `filters` — `[{type, params}]` 列表
- 不要用空的 `st.checkbox("")` / 空的 `with st.columns:` 块，会导致 Streamlit 警告或 IndentationError
