"""遗传算法参数优化"""
import copy
import random
from typing import Dict, Any, Optional, Callable
import numpy as np

from .base import BaseOptimizer


class GeneticOptimizer(BaseOptimizer):
    """遗传算法优化器"""

    def __init__(self, strategy_config: dict, param_space: dict,
                 backtest_runner: Callable, **opts):
        super().__init__(strategy_config, param_space, backtest_runner, **opts)
        self.population_size = opts.get("population_size", 30)
        self.generations = opts.get("generations", 20)
        self.mutation_rate = opts.get("mutation_rate", 0.1)
        self.crossover_rate = opts.get("crossover_rate", 0.7)

    def optimize(self, n_trials: int = 100, progress_callback: Optional[Callable] = None) -> dict:
        pop_size = self.population_size
        generations = min(self.generations, n_trials // pop_size)
        history = []

        # 初始化种群
        population = self._init_population(pop_size)
        scores = []

        for gen in range(generations):
            # 评估适应度
            gen_scores = []
            for i, individual in enumerate(population):
                strategy_cfg = self._apply_params(self.strategy_config, individual)
                result = self.backtest_runner(strategy_cfg)

                score = result.get("summary", {}).get("sharpe_ratio", 0)
                max_dd = result.get("summary", {}).get("max_drawdown_pct", -100)
                if max_dd < -30:
                    score *= 0.5

                gen_scores.append(score)
                history.append({
                    "generation": gen,
                    "individual": i,
                    "params": copy.deepcopy(individual),
                    "score": round(score, 4),
                    "state": "running",
                })

            # 选择精英
            scored = list(zip(population, gen_scores))
            scored.sort(key=lambda x: x[1], reverse=True)
            elite = scored[:max(2, pop_size // 4)]

            if progress_callback:
                n_done = (gen + 1) * pop_size
                progress_callback(n_done, n_trials, elite[0][1])

            # 下一代
            new_pop = [elite[0][0]]  # 保留最优
            while len(new_pop) < pop_size:
                if random.random() < self.crossover_rate:
                    p1 = random.choice(elite)[0]
                    p2 = random.choice(elite)[0]
                    child = self._crossover(p1, p2)
                else:
                    child = copy.deepcopy(random.choice(elite)[0])

                if random.random() < self.mutation_rate:
                    child = self._mutate(child)

                new_pop.append(child)

            population = new_pop[:pop_size]

        # 最终最佳
        best_params = max(zip(population, [self.backtest_runner(
            self._apply_params(self.strategy_config, p)
        ).get("summary", {}).get("sharpe_ratio", 0) for p in population]),
                          key=lambda x: x[1])

        for h in history:
            h["state"] = "done"

        return {
            "best_params": best_params[0],
            "best_score": round(best_params[1], 4),
            "history": history,
            "generations": generations,
        }

    def _init_population(self, size: int) -> list:
        pop = []
        for _ in range(size):
            ind = {}
            for name, space in self.param_space.items():
                if space["type"] in ("float",):
                    ind[name] = random.uniform(space["low"], space["high"])
                elif space["type"] == "int":
                    ind[name] = random.randint(int(space["low"]), int(space["high"]))
                elif space["type"] == "categorical":
                    ind[name] = random.choice(space.get("choices", [0]))
            pop.append(ind)
        return pop

    def _crossover(self, p1: dict, p2: dict) -> dict:
        child = {}
        for key in p1:
            if random.random() < 0.5:
                child[key] = p1[key]
            else:
                child[key] = p2[key]
        return child

    def _mutate(self, ind: dict) -> dict:
        key = random.choice(list(ind.keys()))
        space = self.param_space.get(key, {})
        if space.get("type") == "float":
            delta = (space["high"] - space["low"]) * random.uniform(-0.2, 0.2)
            ind[key] = max(space["low"], min(space["high"], ind[key] + delta))
        elif space.get("type") == "int":
            delta = random.choice([-1, 1])
            ind[key] = max(int(space["low"]), min(int(space["high"]), ind[key] + delta))
        return ind
