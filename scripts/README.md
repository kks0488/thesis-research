# Scripts

## new_topic.py

Creates a new topic folder and baseline docs.

Example:

- `python3 scripts/new_topic.py "Future revenue: precision fermentation protein"`

## openalex_search.py

Fetches works metadata from OpenAlex and appends it to `literature/library.jsonl`.

Example:

- `python3 scripts/openalex_search.py --query "precision fermentation protein" --per-page 25 --pages 2`

## arxiv_search.py

Fetches recent preprint metadata from arXiv and appends it to `literature/library.jsonl`.

Example:

- `python3 scripts/arxiv_search.py --query "cellular agriculture" --max-results 50`

## research_pipeline.py

Collects from OpenAlex/arXiv and generates a topic brief (reading priority/claims/hypotheses/experiments/2-week plan) via DeepSeek, then saves it to the topic folder.

Prereqs:

- set `DEEPSEEK_API_KEY`
- default model is `DEEPSEEK_MODEL=deepseek-reasoner` (DeepSeek-V3.2-Speciale alias supported)
- scripts auto-load `.env` or `.env.local` from the repo root if present

Example:

- `python3 scripts/research_pipeline.py --topic topics/001-미래먹거리정밀발효기반단백질 --query "precision fermentation protein"`

## autopilot.py

Automatically collects AI/LLM/software engineering papers and summarizes next research directions for improving "mergeable PR rate".

Prereqs:

- `python3 -m pip install -r requirements.txt` (LangGraph included)

Default behavior:

- `python3 scripts/autopilot.py` (updates periodically for 6 hours)
- One-shot: `python3 scripts/autopilot.py --run-hours 0`

systemd user timer:

- `bash scripts/install_autopilot_systemd_user.sh`

### AI-Scientist-v2 integration (optional)

- Clone: `git clone https://github.com/SakanaAI/AI-Scientist-v2 third_party/AI-Scientist-v2`
- Env vars:
  - `export AI_SCIENTIST_HOME=/path/to/third_party/AI-Scientist-v2`
  - `export AI_SCIENTIST_MODEL=deepseek-reasoner` (compat mode; DeepSeek-V3.2-Speciale alias supported)
  - `export AI_SCIENTIST_ENABLE=1`
  - (optional) native v2:
    - `export AI_SCIENTIST_MODEL=deepseek-coder-v2-0724`
    - `export AI_SCIENTIST_NATIVE=1`
  - (optional) `export AI_SCIENTIST_PYTHON=/path/to/conda/env/bin/python`
- Bridge:
  - `python3 scripts/ai_scientist_bridge.py --workshop-file ai_scientist_v2/mergeable_pr_agent.md`
- With autopilot:
  - `python3 scripts/autopilot.py --enable-ai-scientist`
