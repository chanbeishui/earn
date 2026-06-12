"""回测 API"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from core import storage

router = APIRouter(prefix="/api/backtest", tags=["回测"])

# 内存缓存最近回测结果（简化方案）
_results_cache = {}


class BacktestRequest(BaseModel):
    strategy_id: int
    start_date: str = "2020-01-01"
    end_date: str = "2025-12-31"
    initial_capital: float = 1_000_000
    commission: float = 0.00025
    stamp_duty: float = 0.001
    benchmark: str = "000300.SH"


@router.post("/run")
def run_backtest(body: BacktestRequest):
    """提交回测任务（同步执行，小规模回测通常 < 10 秒）"""
    from backtest.engine import BacktestEngine
    try:
        engine = BacktestEngine({
            "start_date": body.start_date,
            "end_date": body.end_date,
            "initial_capital": body.initial_capital,
            "commission": body.commission,
            "stamp_duty": body.stamp_duty,
            "benchmark": body.benchmark,
        }, storage)

        engine.load_strategy_by_id(body.strategy_id)
        result = engine.run()

        if "error" in result and not result.get("summary"):
            return {"code": 400, "msg": result["error"]}

        # 缓存结果
        import uuid
        task_id = str(uuid.uuid4())[:8]
        _results_cache[task_id] = {
            "config": body.model_dump(),
            "summary": result["summary"],
            "daily_returns": result.get("daily_returns", []),
            "monthly_returns": result.get("monthly_returns", []),
            "trades": result.get("trades", []),
        }

        return {
            "code": 200,
            "msg": "回测完成",
            "data": {"task_id": task_id, "summary": result["summary"]}
        }
    except Exception as e:
        return {"code": 500, "msg": f"回测失败: {str(e)}"}


@router.get("/{task_id}")
def get_backtest_result(task_id: str):
    """查询回测结果详情"""
    if task_id not in _results_cache:
        return {"code": 404, "msg": "回测结果不存在或已过期"}

    return {"code": 200, "data": _results_cache[task_id]}


@router.get("/history")
def get_backtest_history():
    """历史回测记录（暂返回缓存中的所有记录）"""
    history = []
    for tid, data in _results_cache.items():
        s = data.get("summary", {})
        history.append({
            "task_id": tid,
            "strategy_id": data.get("config", {}).get("strategy_id"),
            "total_return": s.get("total_return_pct"),
            "sharpe": s.get("sharpe_ratio"),
            "max_drawdown": s.get("max_drawdown_pct"),
            "trades": s.get("total_trades"),
        })
    return {"code": 200, "data": history}
