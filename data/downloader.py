"""QMT 数据下载器 — 封装 xtquant API"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Callable
import pandas as pd

from .storage import DataStorage
from config import AppConfig


class DataDownloader:
    """
    数据下载器
    封装 QMT xtquant SDK，提供全量下载 + 增量更新能力。
    如果 xtquant 不可用，自动降级为模拟模式。
    """

    def __init__(self, config: AppConfig, storage: DataStorage):
        self.config = config
        self.storage = storage
        self.xtdata = None
        self._init_xtquant()

    def _init_xtquant(self):
        """初始化 xtquant 连接（小心处理路径避免污染其他库）"""
        try:
            qmt_dir = Path(self.config.qmt.data_dir)
            if not qmt_dir.exists():
                print(f"[DataDownloader] QMT 路径不存在: {qmt_dir}")
                self.xtdata = None
                return

            import os
            bin_path = str(qmt_dir / "bin.x64")
            xt_path = str(qmt_dir / "bin.x64" / "Lib" / "site-packages")

            # 仅添加 DLL 搜索路径（不污染 sys.path）
            if Path(bin_path).exists() and bin_path not in os.environ.get("PATH", ""):
                os.environ["PATH"] = bin_path + ";" + os.environ.get("PATH", "")

            # 临时加入 xtquant 路径来导入
            if xt_path not in sys.path:
                sys.path.append(xt_path)  # 用 append 而非 insert(0) 避免覆盖系统库

            from xtquant import xtdata

            # 测试连接
            try:
                _ = xtdata.get_stock_list_in_sector("沪深A股")
                self.xtdata = xtdata
                self._qmt_connected = True
                print(f"[DataDownloader] xtquant 连接成功 (QMT 运行中)")
            except Exception as e:
                print(f"[DataDownloader] xtquant 已导入但 QMT 客户端未运行 — {e}")
                self.xtdata = xtdata
                self._qmt_connected = False
        except ImportError as e:
            print(f"[DataDownloader] xtquant 导入失败: {e}，使用模拟模式")
            self.xtdata = None
            self._qmt_connected = False
        except Exception as e:
            print(f"[DataDownloader] xtquant 初始化失败: {e}")
            self.xtdata = None
            self._qmt_connected = False

    @property
    def is_available(self) -> bool:
        return self.xtdata is not None and getattr(self, "_qmt_connected", True)

    def try_reconnect(self) -> bool:
        """尝试重新连接 QMT"""
        if self.xtdata is None:
            self._init_xtquant()
        if self.xtdata:
            try:
                _ = self.xtdata.get_stock_list_in_sector("沪深A股")
                self._qmt_connected = True
                return True
            except Exception:
                self._qmt_connected = False
        return False

    # ====== 股票列表 ======

    def download_stock_list(self) -> pd.DataFrame:
        """下载沪深A股股票列表"""
        if self.xtdata:
            return self._download_stock_list_real()
        return self._download_stock_list_mock()

    def _download_stock_list_real(self) -> pd.DataFrame:
        """从 QMT 获取股票列表"""
        # xtquant 获取 A 股列表
        try:
            # 获取沪深全部A股
            sh_codes = self.xtdata.get_stock_list_in_sector("沪深A股")
            # 获取板块信息
            result = []
            for code in sh_codes:
                detail = self.xtdata.get_instrument_detail(code)
                if detail:
                    result.append({
                        "code": code,
                        "name": detail.get("InstrumentName", ""),
                        "market": code.split(".")[1] if "." in code else "",
                        "list_date": detail.get("OpenDate", None),
                        "is_st": "ST" in detail.get("InstrumentName", ""),
                        "is_delisted": detail.get("DelistedDate", "") != "",
                    })
            return pd.DataFrame(result)
        except Exception as e:
            print(f"[DataDownloader] 获取股票列表失败: {e}")
            return pd.DataFrame()

    def _download_stock_list_mock(self) -> pd.DataFrame:
        """模拟股票列表（用于开发测试）"""
        mock_data = [
            {"code": "000001.SZ", "name": "平安银行", "market": "SZ", "list_date": "1991-04-03", "is_st": False, "is_delisted": False},
            {"code": "000002.SZ", "name": "万科A", "market": "SZ", "list_date": "1991-01-29", "is_st": False, "is_delisted": False},
            {"code": "600000.SH", "name": "浦发银行", "market": "SH", "list_date": "1999-11-10", "is_st": False, "is_delisted": False},
            {"code": "600036.SH", "name": "招商银行", "market": "SH", "list_date": "2002-04-09", "is_st": False, "is_delisted": False},
            {"code": "600519.SH", "name": "贵州茅台", "market": "SH", "list_date": "2001-08-27", "is_st": False, "is_delisted": False},
            {"code": "000858.SZ", "name": "五粮液", "market": "SZ", "list_date": "1998-04-27", "is_st": False, "is_delisted": False},
            {"code": "300750.SZ", "name": "宁德时代", "market": "SZ", "list_date": "2018-06-11", "is_st": False, "is_delisted": False},
            {"code": "601318.SH", "name": "中国平安", "market": "SH", "list_date": "2007-03-01", "is_st": False, "is_delisted": False},
        ]
        return pd.DataFrame(mock_data)

    # ====== 日K线 ======

    def download_daily_kline(self, code: str, start_date: str = "2010-01-01",
                             end_date: str = None) -> pd.DataFrame:
        """下载单只股票日K线（前复权）"""
        if self.xtdata:
            return self._download_daily_kline_real(code, start_date, end_date)
        return self._download_kline_mock(code, start_date, end_date, "daily")

    def _download_daily_kline_real(self, code: str, start_date: str,
                                   end_date: Optional[str]) -> pd.DataFrame:
        try:
            if end_date is None:
                end_date = datetime.now().strftime("%Y%m%d")

            # xtquant 下载历史数据
            self.xtdata.download_history_data(code, period="1d", start_time=start_date, end_time=end_date)
            data = self.xtdata.get_market_data_ex(
                field_list=["open", "high", "low", "close", "volume", "amount"],
                stock_list=[code],
                period="1d",
                start_time=start_date,
                end_time=end_date,
                fill_type="up",  # 前复权
            )

            if not data or code not in data:
                return pd.DataFrame()

            # data 结构: {code: {field: [values]}}
            df = pd.DataFrame(data[code])
            df.index.name = "date"
            df = df.reset_index()
            df.rename(columns={
                "open": "open", "high": "high", "low": "low",
                "close": "close", "volume": "volume", "amount": "amount"
            }, inplace=True)

            # 确保日期格式为字符串
            if "date" in df.columns:
                df["date"] = df["date"].astype(str)
            elif df.index.name == "date":
                df["date"] = df.index.astype(str)
                df = df.reset_index(drop=True)

            return df
        except Exception as e:
            print(f"[DataDownloader] 下载 {code} 日K线失败: {e}")
            return pd.DataFrame()

    def _download_kline_mock(self, code: str, start_date: str,
                             end_date: Optional[str], freq: str) -> pd.DataFrame:
        """生成模拟K线数据（开发测试用）"""
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        dates = pd.date_range(start=start_date, end=end_date, freq="B")
        if len(dates) == 0:
            return pd.DataFrame()

        np = __import__("numpy")
        # 用股票代码的哈希值作为随机种子，确保同一只股票数据一致
        seed = sum(ord(c) for c in code)
        rng = np.random.default_rng(seed)

        n = len(dates)
        # 随机游走生成价格
        changes = rng.normal(0.0005, 0.015, n)  # 日均收益~0.05%, 波动~1.5%
        returns = np.cumprod(1 + changes)
        base_price = 10 + (seed % 90)  # 不同股票不同起步价
        close = base_price * returns

        high = close * (1 + np.abs(rng.normal(0, 0.01, n)))
        low = close * (1 - np.abs(rng.normal(0, 0.01, n)))
        open_price = close * (1 + rng.normal(0, 0.005, n))
        volume = rng.integers(1000000, 50000000, n).astype(float)
        amount = close * volume

        df = pd.DataFrame({
            "date": dates.strftime("%Y-%m-%d"),
            "open": open_price, "high": high, "low": low,
            "close": close, "volume": volume, "amount": amount,
        })
        return df

    # ====== 分钟K线 ======

    def download_minute_kline(self, code: str, period: int = 5,
                              start_date: str = None,
                              end_date: str = None) -> pd.DataFrame:
        """下载分钟K线"""
        if self.xtdata:
            return self._download_minute_kline_real(code, period, start_date, end_date)
        return self._download_kline_mock(code, start_date or "2023-01-01", end_date, f"min{period}")

    def _download_minute_kline_real(self, code: str, period: int,
                                    start_date: Optional[str],
                                    end_date: Optional[str]) -> pd.DataFrame:
        try:
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
            if end_date is None:
                end_date = datetime.now().strftime("%Y%m%d")

            period_str = f"{period}min"
            self.xtdata.download_history_data(code, period=period_str,
                                               start_time=start_date, end_time=end_date)
            data = self.xtdata.get_market_data_ex(
                field_list=["open", "high", "low", "close", "volume", "amount"],
                stock_list=[code],
                period=period_str,
                start_time=start_date,
                end_time=end_date,
                fill_type="up",
            )
            if not data or code not in data:
                return pd.DataFrame()
            df = pd.DataFrame(data[code])
            df = df.reset_index()
            return df
        except Exception as e:
            print(f"[DataDownloader] 下载 {code} 分钟线失败: {e}")
            return pd.DataFrame()

    # ====== 财务数据 ======

    def download_financial(self, codes: list) -> list:
        """下载财务数据"""
        if self.xtdata:
            return self._download_financial_real(codes)
        return self._download_financial_mock(codes)

    def _download_financial_real(self, codes: list) -> list:
        results = []
        try:
            for code in codes:
                fin = self.xtdata.get_download_financial_data([code])
                if fin and code in fin:
                    df = pd.DataFrame(fin[code])
                    if not df.empty:
                        for _, row in df.iterrows():
                            results.append({
                                "code": code,
                                "report_date": str(row.get("reportDate", "")),
                                "pe_ttm": row.get("pe_ttm"),
                                "pb": row.get("pb"),
                                "roe": row.get("roe"),
                                "revenue_yoy": row.get("revenueYoy"),
                                "profit_yoy": row.get("profitYoy"),
                                "dividend_yield": row.get("dividendYield"),
                                "total_market_cap": row.get("totalMarketCap"),
                            })
        except Exception as e:
            print(f"[DataDownloader] 下载财务数据失败: {e}")
        return results

    def _download_financial_mock(self, codes: list) -> list:
        """模拟财务数据"""
        import numpy as np
        results = []
        for code in codes:
            seed = sum(ord(c) for c in code)
            rng = np.random.default_rng(seed)
            for year in [2023, 2024]:
                for q in ["0331", "0630", "0930", "1231"]:
                    results.append({
                        "code": code,
                        "report_date": f"{year}{q}",
                        "pe_ttm": round(float(rng.uniform(8, 80)), 2),
                        "pb": round(float(rng.uniform(0.8, 8)), 2),
                        "roe": round(float(rng.uniform(3, 25)), 2),
                        "revenue_yoy": round(float(rng.uniform(-20, 50)), 2),
                        "profit_yoy": round(float(rng.uniform(-30, 80)), 2),
                        "dividend_yield": round(float(rng.uniform(0, 5)), 2),
                        "total_market_cap": round(float(rng.uniform(30, 5000)), 2),
                    })
        return results

    # ====== 批量下载 ======

    def download_all_daily_kline(self, codes: list, progress_callback: Optional[Callable] = None) -> dict:
        """批量下载日K线"""
        total = len(codes)
        success = 0
        failed = []

        start_date = "2010-01-01"
        end_date = datetime.now().strftime("%Y-%m-%d")

        for i, code in enumerate(codes):
            try:
                df = self.download_daily_kline(code, start_date, end_date)
                if not df.empty:
                    self.storage.save_kline(code, df, freq="daily")
                    success += 1
                else:
                    failed.append(code)
            except Exception as e:
                print(f"[DataDownloader] {code} 下载失败: {e}")
                failed.append(code)

            if progress_callback:
                progress_callback(i + 1, total, code)

        return {"success": success, "failed": failed, "total": total}

    def download_all_stocks_basic(self) -> int:
        """下载并保存全量股票列表"""
        df = self.download_stock_list()
        if df.empty:
            return 0

        stocks = df.to_dict(orient="records")
        self.storage.save_stocks_basic(stocks)
        return len(stocks)

    def download_all_financial(self, codes: list, progress_callback: Optional[Callable] = None) -> int:
        """批量下载财务数据"""
        results = self.download_financial(codes)
        if results:
            self.storage.save_financial(results)
        return len(results)
