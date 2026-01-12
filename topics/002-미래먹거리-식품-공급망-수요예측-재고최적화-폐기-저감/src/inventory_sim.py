#!/usr/bin/env python3
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable


def clamp_int(x: float, lo: int = 0, hi: int = 10**9) -> int:
    return max(lo, min(hi, int(round(x))))


def sample_poisson(lam: float, rng: random.Random) -> int:
    lam = max(0.0, float(lam))
    if lam == 0.0:
        return 0
    if lam < 50.0:
        # Knuth
        L = math.exp(-lam)
        k = 0
        p = 1.0
        while p > L:
            k += 1
            p *= rng.random()
        return k - 1
    # Normal approximation for large lambda
    x = rng.gauss(lam, math.sqrt(lam))
    return max(0, int(x))


def inv_norm_cdf(p: float) -> float:
    # Peter John Acklam's inverse normal CDF approximation.
    p = float(p)
    if not (0.0 < p < 1.0):
        raise ValueError("p must be in (0,1)")

    a = [-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02, 1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00]
    b = [-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02, 6.680131188771972e01, -1.328068155288572e01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00, -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00, 3.754408661907416e00]

    plow = 0.02425
    phigh = 1.0 - plow

    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )
    if p > phigh:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )

    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
        (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    )


def approx_poisson_quantile(mu: float, service_level: float) -> int:
    mu = max(0.0, float(mu))
    if mu == 0.0:
        return 0
    z = inv_norm_cdf(min(0.999999, max(1e-6, float(service_level))))
    return max(0, int(round(mu + z * math.sqrt(mu))))


@dataclass
class Costs:
    waste_cost: float = 1.0
    stockout_cost: float = 3.0
    holding_cost: float = 0.05


@dataclass
class SimConfig:
    horizon_days: int
    warmup_days: int
    shelf_life_days: int
    lead_time_days: int
    costs: Costs


@dataclass
class StepMetrics:
    demand: int
    sold: int
    stockout: int
    wasted: int
    on_hand_end: int
    holding_cost: float
    waste_cost: float
    stockout_cost: float


@dataclass
class EpisodeResult:
    total_demand: int
    total_sold: int
    total_stockout: int
    total_wasted: int
    total_received: int
    total_cost: float

    @property
    def service_level(self) -> float:
        if self.total_demand <= 0:
            return 1.0
        return 1.0 - (self.total_stockout / self.total_demand)

    @property
    def waste_rate(self) -> float:
        if self.total_received <= 0:
            return 0.0
        return self.total_wasted / self.total_received


@dataclass
class InventoryState:
    day: int
    on_hand_by_age: list[int]  # index 0 = oldest (expires next), last = freshest
    pipeline: list[int]  # length lead_time_days; pipeline[0] arrives today
    demand_history: list[int]

    @property
    def on_hand_total(self) -> int:
        return sum(self.on_hand_by_age)


def step_inventory(
    state: InventoryState,
    *,
    demand: int,
    order_qty: int,
    shelf_life_days: int,
    lead_time_days: int,
    costs: Costs,
) -> tuple[InventoryState, StepMetrics]:
    on_hand_by_age = list(state.on_hand_by_age)
    pipeline = list(state.pipeline)

    received = pipeline[0] if pipeline else 0
    if lead_time_days > 0:
        pipeline = pipeline[1:] + [max(0, int(order_qty))]
    else:
        received += max(0, int(order_qty))

    # Age inventory: drop expired bucket, shift others older
    wasted = 0
    if len(on_hand_by_age) != shelf_life_days:
        raise ValueError("on_hand_by_age length mismatch")
    wasted += on_hand_by_age[0]
    on_hand_by_age = on_hand_by_age[1:] + [0]

    # Add received as freshest
    on_hand_by_age[-1] += received

    remaining_demand = max(0, int(demand))
    sold = 0
    for i in range(shelf_life_days):
        take = min(on_hand_by_age[i], remaining_demand)
        on_hand_by_age[i] -= take
        remaining_demand -= take
        sold += take
        if remaining_demand == 0:
            break
    stockout = remaining_demand

    holding_cost = costs.holding_cost * sum(on_hand_by_age)
    waste_cost = costs.waste_cost * wasted
    stockout_cost = costs.stockout_cost * stockout

    next_history = (state.demand_history + [int(demand)])[-365:]
    next_state = InventoryState(
        day=state.day + 1,
        on_hand_by_age=on_hand_by_age,
        pipeline=pipeline if lead_time_days > 0 else [],
        demand_history=next_history,
    )
    metrics = StepMetrics(
        demand=int(demand),
        sold=sold,
        stockout=stockout,
        wasted=wasted,
        on_hand_end=sum(on_hand_by_age),
        holding_cost=holding_cost,
        waste_cost=waste_cost,
        stockout_cost=stockout_cost,
    )
    return next_state, metrics


def run_episode(
    *,
    cfg: SimConfig,
    demand_fn: Callable[[int], int],
    policy_fn: Callable[[InventoryState], int],
    rng_seed: int,
) -> EpisodeResult:
    rng = random.Random(int(rng_seed))
    state = InventoryState(
        day=0,
        on_hand_by_age=[0 for _ in range(cfg.shelf_life_days)],
        pipeline=[0 for _ in range(cfg.lead_time_days)] if cfg.lead_time_days > 0 else [],
        demand_history=[],
    )

    totals = {
        "demand": 0,
        "sold": 0,
        "stockout": 0,
        "wasted": 0,
        "received": 0,
        "cost": 0.0,
    }

    for t in range(cfg.horizon_days):
        demand = int(demand_fn(t))
        order_qty = int(policy_fn(state))
        pre_received = state.pipeline[0] if state.pipeline else 0
        if cfg.lead_time_days == 0:
            pre_received += max(0, order_qty)

        state, m = step_inventory(
            state,
            demand=demand,
            order_qty=order_qty,
            shelf_life_days=cfg.shelf_life_days,
            lead_time_days=cfg.lead_time_days,
            costs=cfg.costs,
        )

        totals["demand"] += m.demand
        totals["sold"] += m.sold
        totals["stockout"] += m.stockout
        totals["wasted"] += m.wasted
        totals["received"] += pre_received
        totals["cost"] += m.holding_cost + m.waste_cost + m.stockout_cost

        # randomize: small perturbation by shuffling policy noise if needed later
        _ = rng.random()

    # Ignore warmup for metrics by shrinking horizon? Keep simple for now: warmup is encoded in policy history windows.
    return EpisodeResult(
        total_demand=int(totals["demand"]),
        total_sold=int(totals["sold"]),
        total_stockout=int(totals["stockout"]),
        total_wasted=int(totals["wasted"]),
        total_received=int(totals["received"]),
        total_cost=float(totals["cost"]),
    )

