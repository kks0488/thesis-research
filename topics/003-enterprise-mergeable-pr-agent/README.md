# Enterprise Mergeable PR Agent (B2B DevTools)

## Thesis (1 sentence)

엔터프라이즈 코드베이스에서 PR 자동 생성의 병목은 “코드 생성”이 아니라 “머지 가능성(검증/정책/리스크)”이며, 이를 올리는 시스템(루프+게이트)을 제안한다.

## Problem

- 입력: Issue(요구사항/버그) + Repo + CI/정책
- 출력: 머지 가능한 PR(필수 체크 통과) 또는 “왜 불가능한지” 리포트(다음 액션 포함)

## Success Metric (primary)

- `mergeable_pr_rate`: (필수 체크 통과 + 머지 가능한 상태의 PR) / 전체 시도

## Default “Mergeable” Policy (v0)

- `tests`: required
- `lint/format`: required if configured
- `typecheck`: required if configured
- `secrets`: required (no leaked secrets)
- `security scan`: optional in v0, required in v1

## System Design (v0)

1. Context Builder: repo 구조 + 변경영향 + 소유권(CODEOWNERS) + 최근 CI 실패 패턴을 요약
2. Patch Planner: 최소 변경 계획 + 체크리스트 생성
3. Verifier Loop: 테스트/린트 실행 → 실패 분류 → 수정 → 재검증
4. Mergeability Gate: 정책을 충족할 때만 PR 생성, 아니면 실패 리포트 생성

## Evaluation Plan

- Baselines:
  - B0: 단발 PR 생성(검증 없음)
  - B1: PR 생성 + 테스트 1회
  - Ours: 루프 + 게이트
- Datasets:
  - 공개 벤치(가능하면 SWE-bench 계열)
  - 공개 레포 샘플(언어/빌드 다양) + “작은 이슈” 세트
- Reporting:
  - `mergeable_pr_rate` (primary)
  - 실패 유형 분포(CI/의존성/포맷/테스트/정책)
  - 비용/시간 트레이드오프

