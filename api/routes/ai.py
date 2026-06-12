"""AI 优化 API"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from core import storage

router = APIRouter(prefix="/api/ai", tags=["AI 优化"])

# 结果缓存
_optimize_cache = {}
_train_cache = {}


class OptimizeRequest(BaseModel):
    strategy_id: int
    method: str = "optuna"
    n_trials: int = 100
    params: dict = {}  # 用户指定的参数空间，空则自动推断


class TrainRequest(BaseModel):
    model: str = "lstm"
    lookback: int = 60
    forecast: int = 5
    epochs: int = 50
    batch_size: int = 64
    start_date: str = "2020-01-01"
    end_date: str = "2025-01-01"
    codes: List[str] = []


@router.post("/optimize")
def run_optimize(body: OptimizeRequest):
    """运行参数优化"""
    from backtest.engine import BacktestEngine
    from ai.optimizer.optuna_optimizer import OptunaOptimizer
    from ai.optimizer.genetic_optimizer import GeneticOptimizer

    try:
        crud = storage.strategy_crud()
        sd = crud.get(body.strategy_id)
        if not sd:
            return {"code": 404, "msg": "策略不存在"}

        strategy_config = sd["config"]
        param_space = body.params if body.params else _infer_param_space(strategy_config)

        def backtest_runner(params_config: dict) -> dict:
            engine = BacktestEngine({
                "start_date": "2022-01-01",
                "end_date": "2024-12-31",
                "initial_capital": 1_000_000,
                "benchmark": "000300.SH",
            }, storage)
            engine.load_strategy(params_config)
            return engine.run()

        if body.method == "optuna":
            opt = OptunaOptimizer(strategy_config, param_space, backtest_runner)
        else:
            opt = GeneticOptimizer(strategy_config, param_space, backtest_runner)

        result = opt.optimize(n_trials=body.n_trials)

        import uuid
        task_id = str(uuid.uuid4())[:8]
        _optimize_cache[task_id] = {
            "strategy_id": body.strategy_id,
            "method": body.method,
            "best_params": result["best_params"],
            "best_score": result["best_score"],
            "history": result["history"],
            "param_importances": result.get("param_importances", {}),
        }

        return {
            "code": 200,
            "msg": "优化完成",
            "data": {
                "task_id": task_id,
                "best_params": result["best_params"],
                "best_score": result["best_score"],
            }
        }
    except Exception as e:
        return {"code": 500, "msg": f"优化失败: {str(e)}"}


@router.post("/train")
def run_train(body: TrainRequest):
    """运行深度学习训练"""
    from ai.predictor.trainer import PredictorTrainer

    try:
        codes = body.codes if body.codes else storage.get_stock_codes()[:10]

        trainer = PredictorTrainer(
            model_type=body.model,
            lookback=body.lookback,
            forecast=body.forecast,
            hidden_dim=128,
            num_layers=2,
            dropout=0.2,
            learning_rate=1e-3,
        )
        n_samples = trainer.prepare_data(
            storage, codes, body.start_date, body.end_date
        )
        trainer.build_model()
        result = trainer.train(
            epochs=body.epochs, batch_size=body.batch_size
        )

        import uuid
        task_id = str(uuid.uuid4())[:8]
        _train_cache[task_id] = {
            "model": body.model,
            "n_samples": n_samples,
            **result,
        }

        return {
            "code": 200,
            "msg": "训练完成",
            "data": {
                "task_id": task_id,
                "epochs_trained": result.get("epochs_trained", 0),
                "best_val_loss": result.get("best_val_loss", 0),
            }
        }
    except Exception as e:
        return {"code": 500, "msg": f"训练失败: {str(e)}"}


@router.get("/optimize/{task_id}")
def get_optimize_result(task_id: str):
    """获取优化结果"""
    if task_id not in _optimize_cache:
        return {"code": 404, "msg": "结果不存在"}
    return {"code": 200, "data": _optimize_cache[task_id]}


@router.get("/train/{task_id}")
def get_train_result(task_id: str):
    """获取训练结果"""
    if task_id not in _train_cache:
        return {"code": 404, "msg": "结果不存在"}
    return {"code": 200, "data": _train_cache[task_id]}


@router.get("/tasks")
def get_tasks():
    """获取所有 AI 任务列表"""
    tasks = []
    for tid, data in _optimize_cache.items():
        tasks.append({
            "task_id": tid, "type": "optimize",
            "method": data.get("method", ""),
            "best_score": data.get("best_score"),
        })
    for tid, data in _train_cache.items():
        tasks.append({
            "task_id": tid, "type": "train",
            "model": data.get("model", ""),
            "epochs": data.get("epochs_trained", 0),
            "best_loss": data.get("best_val_loss"),
        })
    return {"code": 200, "data": tasks}


def _infer_param_space(config: dict) -> dict:
    """从策略配置自动推断参数空间"""
    space = {}
    factors = config.get("factors", [])
    for i, f in enumerate(factors):
        name = f.get("name", f"factor_{i}")
        space[f"factors[{i}].weight"] = {"type": "float", "low": 0.05, "high": 0.8}

    timing = config.get("timing", {})
    for direction in ["buy_signals", "sell_signals"]:
        signals = timing.get(direction, [])
        for i, sig in enumerate(signals):
            for pname, pval in sig.get("params", {}).items():
                key = f"timing.{direction}[{i}].params.{pname}"
                if isinstance(pval, float):
                    space[key] = {"type": "float", "low": pval * 0.5, "high": pval * 2}
                elif isinstance(pval, int):
                    space[key] = {"type": "int", "low": max(1, pval // 2), "high": pval * 2}

    return space if space else {"factors[0].weight": {"type": "float", "low": 0.1, "high": 0.9}}
