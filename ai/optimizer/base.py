"""优化器基类"""
from abc import ABC, abstractmethod
from typing import Dict, List, Callable, Optional, Any


class BaseOptimizer(ABC):
    """参数优化器抽象基类"""

    def __init__(self, strategy_config: dict, param_space: dict,
                 backtest_runner: Callable, **opts):
        """
        :param strategy_config: 原始策略配置 (JSON)
        :param param_space: 参数搜索空间，如:
            {"factors[0].weight": {"type": "float", "low": 0.1, "high": 0.9},
             "position.max_stocks": {"type": "int", "low": 3, "high": 20}}
        :param backtest_runner: 回测函数 (params: dict) -> dict (含 summary 的 backtest result)
        """
        self.strategy_config = strategy_config
        self.param_space = param_space
        self.backtest_runner = backtest_runner
        self.opts = opts

    @abstractmethod
    def optimize(self, n_trials: int = 100) -> dict:
        """
        执行参数优化
        :return: {"best_params": {...}, "best_score": float, "history": [...], ...}
        """
        pass

    @staticmethod
    def _apply_params(config: dict, params: dict) -> dict:
        """将优化参数应用到策略配置"""
        import copy
        new_config = copy.deepcopy(config)

        for path, value in params.items():
            parts = path.split(".")
            obj = new_config
            for p in parts[:-1]:
                if "[" in p and "]" in p:
                    # 数组索引: factors[0]
                    key, idx = p.replace("]", "").split("[")
                    if key in obj and isinstance(obj[key], list):
                        if int(idx) < len(obj[key]):
                            obj = obj[key][int(idx)]
                        else:
                            break
                elif p in obj:
                    obj = obj[p]
                else:
                    break
            else:
                last = parts[-1]
                if "[" in last and "]" in last:
                    key, idx = last.replace("]", "").split("[")
                    if key in obj:
                        obj[key][int(idx)] = value
                else:
                    obj[last] = value

        return new_config

    @staticmethod
    def _flatten_params(config: dict, prefix: str = "") -> dict:
        """将嵌套配置扁平化为 {path: value}"""
        result = {}
        for k, v in config.items():
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                result.update(BaseOptimizer._flatten_params(v, path))
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        result.update(BaseOptimizer._flatten_params(
                            item, f"{path}[{i}]"))
                    else:
                        result[f"{path}[{i}]"] = item
            else:
                result[path] = v
        return result
