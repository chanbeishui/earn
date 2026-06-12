"""核心组件 — 全局单例，避免循环导入"""
from config import config
from data.storage import DataStorage
from data.downloader import DataDownloader
from data.scheduler import DataScheduler

# 初始化全局实例
storage = DataStorage(config.storage)
downloader = DataDownloader(config, storage)
scheduler = DataScheduler(config, storage, downloader)
