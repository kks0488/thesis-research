# thesis-research

Workspace to operate AI as a research team. "Future revenue" here means economic opportunities 10-20 years out (not food). The core loop is (1) collect/curate papers -> (2) ideas/hypotheses -> (3) experiments/evidence -> (4) a tech report/paper for reproducible outputs.

## Current Focus

- B2B SaaS / DevTools (enterprise platform teams): a verification-first agent that increases "mergeable PR rate"
  - `topics/003-enterprise-mergeable-pr-agent/`
  - local autopilot (continuous run): `scripts/autopilot.py` + `state/` (local state)
  - LangGraph orchestration + AI-Scientist-v2 ideation (optional)

## Quick start

- Install deps:
  - `python3 -m pip install -r requirements.txt`
- Configure DeepSeek (keep keys out of files; env vars only):
  - `cp .env.example .env` then fill in `DEEPSEEK_API_KEY` only (`.env` is gitignored)
  - if a key is exposed, rotate it immediately
  - DeepSeek API is fixed (no other LLMs)
- Create a new topic: `python3 scripts/new_topic.py "Future revenue: precision fermentation protein"`
- Paper search (metadata):
  - OpenAlex: `python3 scripts/openalex_search.py --query "precision fermentation protein" --per-page 25 --pages 2`
  - arXiv: `python3 scripts/arxiv_search.py --query "cellular agriculture" --max-results 50`
- Search + brief (DeepSeek generates topic brief):
  - `python3 scripts/research_pipeline.py --topic topics/001-미래먹거리정밀발효기반단백질 --query "precision fermentation protein"`
- Continuous run (local systemd user timer):
  - 1) Prepare `.env`: `cp .env.example .env` then set `DEEPSEEK_API_KEY`
  - 2) Install/start: `bash scripts/install_autopilot_systemd_user.sh`
  - 3) Status: `systemctl --user status thesis-research-autopilot.timer`
- Single run (default 6 hours):
  - `python3 scripts/autopilot.py` (updates periodically for 6 hours)
  - One-shot: `python3 scripts/autopilot.py --run-hours 0`

## AI-Scientist-v2 integration (optional)

AI-Scientist runs in a separate environment (often GPU/conda).

- 1) Clone: `git clone https://github.com/SakanaAI/AI-Scientist-v2 third_party/AI-Scientist-v2`
- 2) Env vars:
  - `export AI_SCIENTIST_HOME=/path/to/third_party/AI-Scientist-v2`
  - `export AI_SCIENTIST_MODEL=DeepSeek-V3.2-Speciale` (compat mode, deepseek-chat alias)
  - `export AI_SCIENTIST_ENABLE=1`
  - (optional) native v2:
    - `export AI_SCIENTIST_MODEL=deepseek-coder-v2-0724`
    - `export AI_SCIENTIST_NATIVE=1`
  - (optional) `export AI_SCIENTIST_PYTHON=/path/to/conda/env/bin/python`
- 3) Ideation bridge:
  - `python3 scripts/ai_scientist_bridge.py --workshop-file ai_scientist_v2/mergeable_pr_agent.md --max-ideas 3 --num-reflections 2`

With autopilot:

- `python3 scripts/autopilot.py --enable-ai-scientist`
- Paper summary template: `templates/paper_summary.md`
- Paper build (optional): `cd paper && make` (requires LaTeX/latexmk)

## Folder structure

- `topics/`: per-topic work (questions, hypotheses, claims, experiments)
- `literature/`: paper metadata library (search results)
- `templates/`: summary/experiment/meeting templates
- `team/`: AI research team roles and ops rules
- `paper/`: final paper (LaTeX skeleton)
- `scripts/`: automation scripts
