"""策略组装引擎 — 将前端表单数据组装为 ConfigStrategy"""
from typing import List, Dict, Optional
from .config_strategy import ConfigStrategy


class StrategyComposer:
    """策略组装器"""

    @staticmethod
    def build_config(
        name: str,
        description: str,
        factors: List[Dict],
        buy_signals: List[Dict],
        sell_signals: List[Dict],
        filters: List[Dict],
        position: Dict,
    ) -> dict:
        """
        根据前端表单数据生成策略 JSON 配置
        """
        return {
            "name": name,
            "description": description,
            "factors": factors,
            "timing": {
                "buy_signals": buy_signals,
                "sell_signals": sell_signals,
            },
            "filters": filters,
            "position": position,
        }

    @staticmethod
    def create_strategy(config: dict, storage=None) -> ConfigStrategy:
        """根据配置创建可执行策略"""
        return ConfigStrategy(config, storage=storage)

    @staticmethod
    def validate_config(config: dict) -> tuple[bool, str]:
        """验证策略配置是否有效"""
        if not config.get("name"):
            return False, "策略名称不能为空"

        factors = config.get("factors", [])
        if not factors:
            return False, "至少需要选择一个因子"

        # 检查因子权重
        total_weight = sum(f.get("weight", 0) for f in factors)
        if total_weight <= 0:
            return False, "因子权重总和必须大于 0"

        # 检查信号
        timing = config.get("timing", {})
        buy = timing.get("buy_signals", [])
        sell = timing.get("sell_signals", [])
        if not buy and not sell:
            return False, "至少需要配置一个买入或卖出信号"

        return True, "OK"
