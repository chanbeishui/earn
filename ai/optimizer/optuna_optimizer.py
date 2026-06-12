"""Optuna 贝叶斯参数优化"""
import copy
from typing import Dict, Any, Optional, Callable
import optuna
from optuna.pruners import MedianPruner

from .base import BaseOptimizer


class OptunaOptimizer(BaseOptimizer):
    """Optuna TPE 贝叶斯优化器"""

    def optimize(self, n_trials: int = 100, progress_callback: Optional[Callable] = None) -> dict:
        study = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=42),
            pruner=MedianPruner(n_startup_trials=10, n_warmup_steps=5),
        )

        history = []

        def objective(trial: optuna.Trial) -> float:
            params = {}
            for name, space in self.param_space.items():
                ptype = space.get("type", "float")
                if ptype == "float":
                    params[name] = trial.suggest_float(
                        name, space["low"], space["high"]
                    )
                elif ptype == "int":
                    params[name] = trial.suggest_int(
                        name, int(space["low"]), int(space["high"])
                    )
                elif ptype == "categorical":
                    params[name] = trial.suggest_categorical(
                        name, space.get("choices", [])
                    )

            # 应用参数到策略
            strategy_cfg = self._apply_params(self.strategy_config, params)

            # 运行回测
            result = self.backtest_runner(strategy_cfg)

            score = result.get("summary", {}).get("sharpe_ratio", 0)
            total_return = result.get("summary", {}).get("total_return_pct", 0)
            max_dd = result.get("summary", {}).get("max_drawdown_pct", -100)

            # 综合评分（惩罚高回撤）
            if max_dd < -30:
                score = score * 0.5

            history.append({
                "trial": trial.number,
                "params": copy.deepcopy(params),
                "score": round(score, 4),
                "total_return": round(total_return, 2),
                "max_drawdown": round(max_dd, 2),
                "state": "running",
            })

            if progress_callback:
                progress_callback(trial.number + 1, n_trials, score)

            return score

        study.optimize(objective, n_trials=n_trials)

        # 标记完成
        for h in history:
            h["state"] = "done"

        return {
            "best_params": study.best_params,
            "best_score": round(study.best_value, 4),
            "history": history,
            "param_importances": self._get_importances(study),
        }

    def _get_importances(self, study: optuna.Study) -> dict:
        """获取参数重要性"""
        try:
            importances = optuna.importance.get_param_importances(study)
            return {k: round(v, 4) for k, v in importances.items()}
        except Exception:
            return {}
