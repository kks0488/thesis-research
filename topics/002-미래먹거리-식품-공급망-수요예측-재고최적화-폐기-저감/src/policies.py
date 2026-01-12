#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass

from inventory_sim import InventoryState, approx_poisson_quantile


def mean(xs: list[int]) -> float:
    if not xs:
        return 0.0
    return sum(xs) / len(xs)


def ewma(xs: list[int], alpha: float) -> float:
    if not xs:
        return 0.0
    alpha = max(0.0, min(1.0, float(alpha)))
    m = float(xs[0])
    for x in xs[1:]:
        m = alpha * float(x) + (1.0 - alpha) * m
    return m


@dataclass(frozen=True)
class PolicyConfig:
    service_level_target: float = 0.95
    history_window: int = 28
    ewma_alpha: float = 0.2
    residual_window: int = 60


def _base_stock_order_qty(state: InventoryState, target_stock: int) -> int:
    # Inventory position = on-hand + pipeline
    position = state.on_hand_total + sum(state.pipeline)
    return max(0, int(target_stock) - int(position))


def baseline_ma_base_stock(state: InventoryState, cfg: PolicyConfig) -> int:
    hist = (state.demand_history or [])[-max(1, int(cfg.history_window)) :]
    mu = mean(hist)
    target_stock = approx_poisson_quantile(mu, cfg.service_level_target)
    return _base_stock_order_qty(state, target_stock)


def baseline_ewma_base_stock(state: InventoryState, cfg: PolicyConfig) -> int:
    hist = (state.demand_history or [])[-max(2, int(cfg.history_window)) :]
    mu = ewma(hist, cfg.ewma_alpha)
    target_stock = approx_poisson_quantile(mu, cfg.service_level_target)
    return _base_stock_order_qty(state, target_stock)


def cq_base_stock(state: InventoryState, cfg: PolicyConfig) -> int:
    # Conformal-like residual calibration:
    # mean forecast (EWMA) + empirical residual quantile adjustment.
    hist = state.demand_history or []
    window = max(5, int(cfg.history_window))
    resid_window = max(10, int(cfg.residual_window))

    recent = hist[-window:]
    mu = ewma(recent, cfg.ewma_alpha)

    # Build residuals on last resid_window points using a simple rolling mean forecast proxy.
    resids: list[float] = []
    # Avoid expensive loops early.
    start = max(0, len(hist) - resid_window)
    for i in range(start, len(hist)):
        past = hist[max(0, i - window) : i]
        if not past:
            continue
        pred = ewma(past, cfg.ewma_alpha)
        resids.append(float(hist[i]) - pred)

    if not resids:
        target_stock = approx_poisson_quantile(mu, cfg.service_level_target)
        return _base_stock_order_qty(state, target_stock)

    # Empirical quantile of residuals at desired service level.
    q = float(cfg.service_level_target)
    q = min(0.999, max(0.001, q))
    resids_sorted = sorted(resids)
    idx = int(math.ceil(q * len(resids_sorted))) - 1
    idx = max(0, min(len(resids_sorted) - 1, idx))
    adj = resids_sorted[idx]

    calibrated_mu = max(0.0, mu + adj)
    target_stock = approx_poisson_quantile(calibrated_mu, cfg.service_level_target)
    return _base_stock_order_qty(state, target_stock)

