# Future revenue: reduce food waste via supply chain demand forecasting and inventory optimization

## Problem statement (1 sentence)

Reduce food waste driven by demand uncertainty and shelf-life constraints through better demand forecasting (probabilistic/quantile) and inventory/replenishment policies.

## Hypothesis (falsifiable)

- H1: Under the same service-level constraint, a quantile (or conformal) reorder policy reduces waste rate compared to a mean-based base-stock policy.
- H2: For non-stationary demand, EWMA + residual calibration (conformal-like) is more stable than a static window.

## Success metrics

- `waste_rate`: discarded quantity / total inbound
- `service_level`: 1 - (stockout quantity / total demand)
- `total_cost`: sum of waste cost + stockout penalty + holding cost

## Baselines (start simple)

- `baseline_ma_base_stock`: moving-average base-stock
- `baseline_ewma_base_stock`: EWMA base-stock

## Proposed (candidate “research” contribution)

- `cq_base_stock` (conformal-like): mean forecast + historical residual quantile correction to hit target service level

## Data plan

1) Week 1: start with a reproducible perishable inventory simulator without public data (`src/` in this topic).
2) Week 2: add public demand series data (M5, etc.) with assumed shelf-life/waste costs.

## Quick run

- Single experiment: `python3 src/run_experiment.py --config experiments/default.json --seeds 0,1,2 --out results/run.jsonl`

## Plan (next 2 weeks)

- Week 1: literature review (perishable inventory + quantile forecasting + robust inventory control) + simulator/baselines + first experiments
- Week 2: policy improvements (calibration/drift) + ablation + one result table + limitations
