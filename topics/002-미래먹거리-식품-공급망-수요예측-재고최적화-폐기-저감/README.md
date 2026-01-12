# 미래먹거리: 식품 공급망 수요예측·재고최적화로 폐기 저감

## Problem statement (1 sentence)

수요 불확실성과 유통기한 제약 때문에 발생하는 **식품 폐기(waste)** 를, 더 나은 **수요예측(확률/분위수)** + **재고/발주 의사결정(정책)** 으로 줄인다.

## Hypothesis (falsifiable)

- H1: 동일한 서비스레벨(결품률) 제약 하에서, “분위수(또는 conformal) 기반 발주 정책”은 단순 평균 기반 베이스스톡 정책보다 폐기율을 유의미하게 낮춘다.
- H2: 수요 분포가 비정상(non-stationary)인 경우, EWMA+잔차 보정(conformal 유사)이 정적(고정 window)보다 안정적이다.

## Success metrics

- `waste_rate`: 폐기수량 / 총입고수량
- `service_level`: 1 - (결품수량 / 총수요)
- `total_cost`: (폐기비용 + 결품패널티 + 보관비용) 합

## Baselines (start simple)

- `baseline_ma_base_stock`: 이동평균 기반 베이스스톡
- `baseline_ewma_base_stock`: 지수평활(EWMA) 기반 베이스스톡

## Proposed (candidate “research” contribution)

- `cq_base_stock` (conformal-like): 평균 예측 + 과거 잔차 분위수(보정)로 목표 서비스레벨을 맞추는 정책

## Data plan

1) 1주차: 공개 데이터 없이도 재현 가능한 **퍼리셔블(perishable) 재고 시뮬레이터**로 시작(이 토픽 `src/`).
2) 2주차: 공개 수요 시계열 데이터(M5 등)에 “유통기한/폐기 비용” 가정을 추가해 현실성 테스트.

## Quick run

- 단일 실험 실행: `python3 src/run_experiment.py --config experiments/default.json --seeds 0,1,2 --out results/run.jsonl`

## Plan (next 2 weeks)

- Week 1: 문헌 조사(퍼리셔블 재고 + 분위수 예측 + robust inventory control) + 시뮬레이터/베이스라인 구현 + 1차 실험
- Week 2: 정책 개선(보정/드리프트 대응) + ablation + 결과표 1개 만들기 + limitations 정리

