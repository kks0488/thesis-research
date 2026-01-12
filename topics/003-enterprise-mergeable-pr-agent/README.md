# Enterprise Mergeable PR Agent (B2B DevTools)

## Thesis (1 sentence)

In enterprise codebases, the bottleneck for automatic PR generation is not code synthesis but mergeability (verification/policy/risk). We propose a loop + gate system to raise mergeability.

## Objective (autopilot)

- Continuously explore AI/LLM/software engineering papers and propose **next directions** to increase "mergeable PR rate".
- Orchestrate the pipeline with LangGraph and assist ideation with AI-Scientist-v2 (compat mode by default).

## Problem

- Input: issue (feature/bug) + repo + CI/policy
- Output: a mergeable PR (passes required checks) or a report on why it is not mergeable (with next actions)

## Success Metric (primary)

- `mergeable_pr_rate`: (PRs that pass required checks and are mergeable) / total attempts

## Default “Mergeable” Policy (v0)

- `tests`: required
- `lint/format`: required if configured
- `typecheck`: required if configured
- `secrets`: required (no leaked secrets)
- `security scan`: optional in v0, required in v1

## System Design (v0)

1. Context Builder: summarize repo structure, change impact, ownership (CODEOWNERS), and recent CI failures
2. Patch Planner: minimal-change plan + checklist
3. Verifier Loop: run tests/lint -> classify failures -> fix -> re-verify
4. Mergeability Gate: open PR only when policy passes, otherwise emit a failure report

## Evaluation Plan

- Baselines:
  - B0: single-shot PR generation (no verification)
  - B1: PR generation + one test run
  - Ours: loop + gate
- Datasets:
  - Public benchmark (SWE-bench family if possible)
  - Sample public repos (varied languages/builds) + a "small issue" set
- Reporting:
  - `mergeable_pr_rate` (primary)
  - failure type distribution (CI/deps/format/test/policy)
  - cost/time trade-offs
