"""基本面因子"""
import pandas as pd
import numpy as np
from .base import Factor


class FundamentalFactor(Factor):
    """
    基本面因子基类 — 从财务数据 DataFrame 读取最新值
    需要由外部传入 financial_df (DataFrame, columns: code/pe_ttm/pb/roe/...)
    """
    category = "fundamental"
    field: str = ""

    def calculate(self, df: pd.DataFrame, **kwargs) -> pd.Series:
        # 基本面因子不基于 K 线计算，需要外部 financial_data
        fin_df = kwargs.get("financial_df")
        if fin_df is None or fin_df.empty:
            return pd.Series(np.nan, index=df.index)

        # 如果没有 code 列，返回当前可用的值
        if self.field in fin_df.columns:
            val = float(fin_df[self.field].iloc[0])
            return pd.Series(val, index=df.index)
        return pd.Series(np.nan, index=df.index)

    def get_value(self, df: pd.DataFrame, date_str: str, **kwargs) -> float:
        fin_df = kwargs.get("financial_df")
        if fin_df is None or fin_df.empty:
            return np.nan
        if self.field in fin_df.columns:
            return float(fin_df[self.field].iloc[0])
        return np.nan


class PETTMFactor(FundamentalFactor):
    name = "pe_ttm"
    display = "PE_TTM"
    field = "pe_ttm"


class PBFactor(FundamentalFactor):
    name = "pb"
    display = "PB 市净率"
    field = "pb"


class ROEFactor(FundamentalFactor):
    name = "roe"
    display = "ROE"
    field = "roe"


class RevenueYoYFactor(FundamentalFactor):
    name = "revenue_yoy"
    display = "营收同比增速"
    field = "revenue_yoy"


class ProfitYoYFactor(FundamentalFactor):
    name = "profit_yoy"
    display = "净利润同比增速"
    field = "profit_yoy"


class DividendYieldFactor(FundamentalFactor):
    name = "dividend_yield"
    display = "股息率"
    field = "dividend_yield"
