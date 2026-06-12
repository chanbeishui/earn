"""定时任务调度器 — 基于 APScheduler"""
from datetime import datetime
from typing import Optional, Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .downloader import DataDownloader
from .storage import DataStorage
from config import AppConfig


class DataScheduler:
    """数据下载定时调度器"""

    def __init__(self, config: AppConfig, storage: DataStorage,
                 downloader: DataDownloader):
        self.config = config
        self.storage = storage
        self.downloader = downloader
        self._scheduler: Optional[BackgroundScheduler] = None
        self._progress_callback: Optional[Callable] = None
        self._current_progress = {"running": False, "current": 0, "total": 0, "msg": ""}

    def set_progress_callback(self, callback: Callable):
        """设置进度回调（供 API 层轮询）"""
        self._progress_callback = callback

    def get_progress(self) -> dict:
        """获取当前下载进度"""
        return dict(self._current_progress)

    def start(self):
        """启动定时调度"""
        if self._scheduler:
            return

        self._scheduler = BackgroundScheduler()

        # 解析下载时间
        dl_time = self.config.scheduler.download_time.split(":")
        hour, minute = int(dl_time[0]), int(dl_time[1])

        # 每日定时下载（仅交易日执行）
        self._scheduler.add_job(
            self._daily_update,
            CronTrigger(day_of_week="mon-fri", hour=hour, minute=minute),
            id="daily_download",
            name="每日数据下载",
        )

        # 每周六更新财务数据
        self._scheduler.add_job(
            self._weekly_financial_update,
            CronTrigger(day_of_week="sat", hour=9, minute=0),
            id="weekly_financial",
            name="每周财务数据更新",
        )

        self._scheduler.start()
        print(f"[DataScheduler] 定时调度已启动, 每日下载时间: {dl_time}")

    def stop(self):
        """停止定时调度"""
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None

    def _daily_update(self):
        """每日增量更新"""
        print(f"[DataScheduler] 开始每日数据更新: {datetime.now()}")
        self._update_progress(True, 0, 1, "正在下载今日数据...")

        try:
            codes = self.storage.get_stock_codes()
            if not codes:
                # 先下载股票列表
                self._update_progress(True, 0, 1, "下载股票列表...")
                log_id = self.storage.create_download_log("stock_basic")
                count = self.downloader.download_all_stocks_basic()
                self.storage.update_download_log(log_id, "done", count, count)
                codes = self.storage.get_stock_codes()

            # 增量下载日K线
            log_id = self.storage.create_download_log("daily_kline")
            self.downloader.download_all_daily_kline(codes, self._on_progress)
            self.storage.update_download_log(log_id, "done", len(codes), len(codes))

            self._update_progress(True, 1, 1, "下载完成")
        except Exception as e:
            print(f"[DataScheduler] 每日更新失败: {e}")
        finally:
            self._update_progress(False, 0, 0, "")

    def _weekly_financial_update(self):
        """每周财务数据更新"""
        print(f"[DataScheduler] 开始财务数据更新: {datetime.now()}")
        try:
            codes = self.storage.get_stock_codes()
            log_id = self.storage.create_download_log("financial")
            count = self.downloader.download_all_financial(codes)
            self.storage.update_download_log(log_id, "done", len(codes), count)
        except Exception as e:
            print(f"[DataScheduler] 财务更新失败: {e}")

    def _on_progress(self, current, total, code):
        self._update_progress(True, current, total, f"下载中: {code}")

    def _update_progress(self, running: bool, current: int, total: int, msg: str):
        self._current_progress = {
            "running": running, "current": current, "total": total, "msg": msg
        }

    def run_now(self, data_type: str = "daily_kline") -> int:
        """手动触发立即下载"""
        log_id = self.storage.create_download_log(data_type)

        if data_type == "stock_basic":
            count = self.downloader.download_all_stocks_basic()
            self.storage.update_download_log(log_id, "done", count, count)
            return log_id

        elif data_type == "daily_kline":
            codes = self.storage.get_stock_codes()
            if not codes:
                codes_df = self.downloader.download_stock_list()
                if not codes_df.empty:
                    self.storage.save_stocks_basic(codes_df.to_dict(orient="records"))
                    codes = self.storage.get_stock_codes()

            self._update_progress(True, 0, len(codes), "开始下载...")
            result = self.downloader.download_all_daily_kline(codes, self._on_progress)
            self.storage.update_download_log(
                log_id, "done", result["total"], result["success"]
            )
            self._update_progress(False, 0, 0, "")
            return log_id

        elif data_type == "financial":
            codes = self.storage.get_stock_codes()
            self._update_progress(True, 0, len(codes), "下载财务数据...")
            count = self.downloader.download_all_financial(codes)
            self.storage.update_download_log(
                log_id, "done", len(codes), count
            )
            self._update_progress(False, 0, 0, "")
            return log_id

        return log_id
