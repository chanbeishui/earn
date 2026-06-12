"""数据下载 API"""
from fastapi import APIRouter
from core import storage, downloader, scheduler

router = APIRouter(prefix="/api/data", tags=["数据中心"])


@router.post("/download")
def trigger_download(data_type: str = "daily_kline"):
    """触发数据下载"""
    log_id = scheduler.run_now(data_type)
    return {"code": 200, "msg": "下载任务已启动", "data": {"log_id": log_id}}


@router.get("/status")
def get_progress():
    """查询下载进度"""
    return {"code": 200, "data": scheduler.get_progress()}


@router.get("/logs")
def get_logs(limit: int = 50):
    """获取下载日志"""
    return {"code": 200, "data": storage.get_download_logs(limit)}


@router.get("/overview")
def get_overview():
    """数据概览"""
    return {"code": 200, "data": storage.get_overview()}


@router.get("/stocks")
def get_stocks():
    """获取股票列表"""
    df = storage.get_stocks()
    return {"code": 200, "data": df.to_dict(orient="records")}


@router.get("/factors")
def get_factors():
    """获取可用因子列表"""
    import yaml
    from pathlib import Path
    registry_path = Path(__file__).parent.parent.parent / "config" / "factor_registry.yaml"
    with open(registry_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {
        "code": 200,
        "data": {
            "factors": data.get("factors", []),
            "buy_signals": data.get("timing_signals", {}).get("buy", []),
            "sell_signals": data.get("timing_signals", {}).get("sell", []),
            "filters": data.get("filters", []),
            "position_rules": data.get("position_rules", []),
        }
    }


@router.get("/timing/types")
def get_timing_types():
    """获取可用择时信号类型"""
    import yaml
    from pathlib import Path
    registry_path = Path(__file__).parent.parent.parent / "config" / "factor_registry.yaml"
    with open(registry_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {
        "code": 200,
        "data": {
            "buy": data.get("timing_signals", {}).get("buy", []),
            "sell": data.get("timing_signals", {}).get("sell", []),
        }
    }
