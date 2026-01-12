#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from inventory_sim import Costs, EpisodeResult, SimConfig, run_episode, sample_poisson
from policies import PolicyConfig, baseline_ewma_base_stock, baseline_ma_base_stock, cq_base_stock


def parse_seeds(text: str) -> list[int]:
    out: list[int] = []
    for part in (text or "").split(","):
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    return out


def build_demand_fn(cfg: dict[str, Any], *, seed: int) -> Callable[[int], int]:
    dm = cfg.get("demand_model") or {}
    typ = (dm.get("type") or "poisson").strip()

    if typ == "poisson_drift":
        lam0 = float(dm.get("lambda_start", 20.0))
        lam1 = float(dm.get("lambda_end", 25.0))
        horizon = int(cfg.get("horizon_days", 180))

        import random

        rng = random.Random(seed + 1337)

        def fn(t: int) -> int:
            frac = 0.0 if horizon <= 1 else min(1.0, max(0.0, t / (horizon - 1)))
            lam = lam0 + (lam1 - lam0) * frac
            # Weekly seasonality bump
            lam *= 1.0 + 0.15 * math.sin(2.0 * math.pi * (t % 7) / 7.0)
            return sample_poisson(lam, rng)

        return fn

    raise ValueError(f"unknown demand_model.type: {typ}")


def build_policy_fn(cfg: dict[str, Any]) -> Callable:
    pol = cfg.get("policy") or {}
    name = (pol.get("name") or "baseline_ma_base_stock").strip()
    pcfg = PolicyConfig(
        service_level_target=float(pol.get("service_level_target", 0.95)),
        history_window=int(pol.get("history_window", 28)),
        ewma_alpha=float(pol.get("ewma_alpha", 0.2)),
        residual_window=int(pol.get("residual_window", 60)),
    )

    if name == "baseline_ma_base_stock":
        return lambda state: baseline_ma_base_stock(state, pcfg)
    if name == "baseline_ewma_base_stock":
        return lambda state: baseline_ewma_base_stock(state, pcfg)
    if name == "cq_base_stock":
        return lambda state: cq_base_stock(state, pcfg)

    raise ValueError(f"unknown policy.name: {name}")


def summarize(result: EpisodeResult) -> dict[str, Any]:
    return {
        "total_demand": result.total_demand,
        "total_sold": result.total_sold,
        "total_stockout": result.total_stockout,
        "total_wasted": result.total_wasted,
        "total_received": result.total_received,
        "service_level": result.service_level,
        "waste_rate": result.waste_rate,
        "total_cost": result.total_cost,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run perishable inventory experiments and write JSONL results.")
    parser.add_argument("--config", required=True, help="Path to experiment JSON config")
    parser.add_argument("--seeds", default="0,1,2,3,4", help="Comma-separated random seeds")
    parser.add_argument("--out", default="results/run.jsonl", help="Output JSONL path")
    args = parser.parse_args()

    cfg_path = Path(args.config)
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    costs_cfg = cfg.get("costs") or {}
    sim_cfg = SimConfig(
        horizon_days=int(cfg.get("horizon_days", 180)),
        warmup_days=int(cfg.get("warmup_days", 30)),
        shelf_life_days=int(cfg.get("shelf_life_days", 7)),
        lead_time_days=int(cfg.get("lead_time_days", 1)),
        costs=Costs(
            waste_cost=float(costs_cfg.get("waste_cost", 1.0)),
            stockout_cost=float(costs_cfg.get("stockout_cost", 3.0)),
            holding_cost=float(costs_cfg.get("holding_cost", 0.05)),
        ),
    )
    policy_fn = build_policy_fn(cfg)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    seeds = parse_seeds(args.seeds)

    with out_path.open("w", encoding="utf-8") as f:
        for seed in seeds:
            demand_fn = build_demand_fn(cfg, seed=seed)
            result = run_episode(cfg=sim_cfg, demand_fn=demand_fn, policy_fn=policy_fn, rng_seed=seed)
            rec = {
                "seed": seed,
                "config": cfg,
                "sim_cfg": asdict(sim_cfg),
                "metrics": summarize(result),
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

