"""股票池 API"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from core import storage
from pool.manager import PoolManager
from pool.watchlist import Watchlist

router = APIRouter(prefix="/api/pool", tags=["股票池"])
pool_manager = PoolManager(storage)


class WatchlistCreate(BaseModel):
    code: str
    name: str = ""
    tags: str = ""
    note: str = ""


class WatchlistUpdate(BaseModel):
    name: Optional[str] = None
    tags: Optional[str] = None
    note: Optional[str] = None


class BatchAddRequest(BaseModel):
    codes: List[dict]
    tag: str = ""


# ====== 策略选股池 ======

@router.get("/strategy/pool")
def get_strategy_pool(strategy_id: Optional[int] = None, date: str = ""):
    """获取策略选股结果"""
    results = pool_manager.get_strategy_results(
        strategy_id, date if date else None
    )
    return {"code": 200, "data": results}


@router.get("/strategy/dates/{strategy_id}")
def get_strategy_dates(strategy_id: int):
    """获取策略的选股日期列表"""
    dates = pool_manager.strategy_pool.get_dates(strategy_id)
    return {"code": 200, "data": dates}


# ====== 自选股 ======

@router.get("/watchlist")
def get_watchlist(tag: str = "", search: str = ""):
    """获取自选股列表"""
    wl = pool_manager.watchlist
    if tag:
        df = wl.get_by_tag(tag)
    elif search:
        df = wl.search(search)
    else:
        df = wl.get_all()

    if df.empty:
        return {"code": 200, "data": []}
    return {"code": 200, "data": df.to_dict(orient="records")}


@router.get("/watchlist/{item_id}")
def get_watchlist_item(item_id: int):
    item = pool_manager.watchlist.get(item_id)
    if item is None:
        return {"code": 404, "msg": "不存在"}
    return {"code": 200, "data": item}


@router.post("/watchlist")
def add_watchlist_item(body: WatchlistCreate):
    sid = pool_manager.add_to_watchlist(
        body.code, body.name, body.tags, body.note
    )
    return {"code": 200, "msg": "添加成功", "data": {"id": sid}}


@router.put("/watchlist/{item_id}")
def update_watchlist_item(item_id: int, body: WatchlistUpdate):
    ok = pool_manager.update_watchlist_item(
        item_id, **body.model_dump(exclude_none=True)
    )
    if not ok:
        return {"code": 404, "msg": "不存在"}
    return {"code": 200, "msg": "更新成功"}


@router.delete("/watchlist/{item_id}")
def delete_watchlist_item(item_id: int):
    ok = pool_manager.remove_from_watchlist(item_id)
    if not ok:
        return {"code": 404, "msg": "不存在"}
    return {"code": 200, "msg": "删除成功"}


@router.post("/watchlist/batch")
def batch_add_to_watchlist(body: BatchAddRequest):
    """批量从策略选股结果添加自选"""
    pool_manager.add_batch_to_watchlist(body.codes, body.tag)
    return {"code": 200, "msg": f"已批量添加 {len(body.codes)} 只股票"}


@router.get("/watchlist/tags")
def get_tags():
    """获取所有标签"""
    tags = pool_manager.get_all_tags()
    return {"code": 200, "data": tags}


# ====== 池操作 ======

@router.get("/ops/intersection")
def pool_intersection(strategy_id: int, date: str = ""):
    """选股池 ∩ 自选池"""
    results = pool_manager.pool_intersection(
        strategy_id, date if date else None
    )
    return {"code": 200, "data": results}


@router.get("/ops/union")
def pool_union(strategy_id: int, date: str = ""):
    """选股池 ∪ 自选池"""
    results = pool_manager.pool_union(
        strategy_id, date if date else None
    )
    return {"code": 200, "data": results}


@router.get("/ops/difference")
def pool_difference(strategy_id: int, date: str = ""):
    """选股池 - 自选池"""
    results = pool_manager.pool_difference(
        strategy_id, date if date else None
    )
    return {"code": 200, "data": results}


# ====== 导出 ======

@router.get("/export/csv")
def export_csv():
    """导出自选股 CSV"""
    csv_data = pool_manager.export_watchlist_csv()
    return {"code": 200, "data": csv_data}
