# Earn 量化交易系统

基于 QMT (xtquant) 的 A 股量化投研平台。五大模块：数据下载、策略选股、回测、AI 优化、股票池。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

- ta-lib 需要先安装 C 库: [下载 ta-lib](https://github.com/TA-Lib/ta-lib-python)
- xtquant 随 QMT 客户端提供，安装后在 QMT 安装目录找到 `xtquant` 复制到 site-packages 或通过 pip 安装

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env 填入 QMT 路径和账号
```

编辑 `config/settings.yaml` 按需调整参数。

### 3. 启动后端

```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

访问 http://localhost:8000/docs 查看 API 文档。

### 4. 启动前端

```bash
streamlit run dashboard/app.py
```

访问 http://localhost:8501 

### 5. 命令行脚本

```bash
# 仅下载数据
python scripts/download_data.py

# 全流程
python scripts/run_all.py
```

## 项目结构

```
earn/
├── config/          # 配置（settings.yaml + 因子注册表）
├── data/            # 模块一：数据下载+存储
├── strategy/        # 模块二：策略选股（因子+择时）
├── backtest/        # 模块三：回测引擎
├── ai/              # 模块四：AI 优化（Optuna + PyTorch）
├── pool/            # 模块五：股票池管理
├── api/             # FastAPI 后端路由
├── dashboard/       # Streamlit 前端页面
├── scripts/         # CLI 脚本
└── tests/           # 测试
```

## 开发状态

- [x] Phase 1: 基础设施 + 数据下载
- [ ] Phase 2: 策略框架 + 可视化构建
- [ ] Phase 3: 回测引擎
- [ ] Phase 4: AI 优化
- [ ] Phase 5: 股票池 + 集成
