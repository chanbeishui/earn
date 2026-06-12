"""策略管理 API"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from core import storage
from strategy.selector import StockSelector
from strategy.composer import StrategyComposer

router = APIRouter(prefix="/api/strategies", tags=["策略管理"])


class StrategyCreate(BaseModel):
    name: str
    config: dict
    description: str = ""


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[dict] = None
    description: Optional[str] = None


@router.get("")
def list_strategies():
    crud = storage.strategy_crud()
    return {"code": 200, "data": crud.list()}


@router.get("/{strategy_id}")
def get_strategy(strategy_id: int):
    crud = storage.strategy_crud()
    data = crud.get(strategy_id)
    if not data:
        return {"code": 404, "msg": "策略不存在"}
    return {"code": 200, "data": data}


@router.post("")
def create_strategy(body: StrategyCreate):
    ok, msg = StrategyComposer.validate_config(body.config)
    if not ok:
        return {"code": 400, "msg": msg}
    crud = storage.strategy_crud()
    sid = crud.create(body.name, body.config, body.description)
    return {"code": 200, "msg": "创建成功", "data": {"id": sid}}


@router.put("/{strategy_id}")
def update_strategy(strategy_id: int, body: StrategyUpdate):
    if body.config:
        ok, msg = StrategyComposer.validate_config(body.config)
        if not ok:
            return {"code": 400, "msg": msg}
    crud = storage.strategy_crud()
    updates = body.model_dump(exclude_none=True)
    ok = crud.update(strategy_id, **updates)
    if not ok:
        return {"code": 404, "msg": "策略不存在"}
    return {"code": 200, "msg": "更新成功"}


@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: int):
    crud = storage.strategy_crud()
    ok = crud.delete(strategy_id)
    if not ok:
        return {"code": 404, "msg": "策略不存在"}
    return {"code": 200, "msg": "删除成功"}


@router.post("/{strategy_id}/toggle")
def toggle_strategy(strategy_id: int):
    crud = storage.strategy_crud()
    new_state = crud.toggle(strategy_id)
    if new_state is None:
        return {"code": 404, "msg": "策略不存在"}
    return {"code": 200, "msg": "状态已切换", "data": {"is_enabled": new_state}}


@router.post("/{strategy_id}/run")
def run_strategy(strategy_id: int, date: str = ""):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    selector = StockSelector(storage)
    results = selector.run_strategy(strategy_id, date)
    return {
        "code": 200,
        "msg": f"选股完成，共 {len(results)} 只",
        "data": {"strategy_id": strategy_id, "date": date, "results": results}
    }


@router.get("/{strategy_id}/results")
def get_strategy_results(strategy_id: int, date: str = ""):
    crud = storage.strategy_crud()
    results = crud.get_results(strategy_id, date if date else None)
    return {"code": 200, "data": results}

