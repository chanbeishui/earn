"""FastAPI 入口"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core import storage, downloader, scheduler
from api.routes.data import router as data_router
from api.routes.strategy import router as strategy_router
from api.routes.backtest import router as backtest_router
from api.routes.ai import router as ai_router
from api.routes.pool import router as pool_router

# 启动定时调度
scheduler.start()

app = FastAPI(
    title="Earn 量化交易系统",
    description="基于 QMT 的 A 股量化投研平台",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data_router)
app.include_router(strategy_router)
app.include_router(backtest_router)
app.include_router(ai_router)
app.include_router(pool_router)


@app.get("/")
def root():
    return {"name": "Earn 量化交易系统", "version": "0.1.0", "status": "running"}


@app.get("/api/overview")
def overview():
    return {
        "code": 200,
        "data": {
            **storage.get_overview(),
            "qmt_available": downloader.is_available,
            "download_progress": scheduler.get_progress(),
        }
    }
