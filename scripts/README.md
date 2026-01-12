# Scripts

## new_topic.py

새 토픽 폴더와 기본 문서를 생성합니다.

예:

- `python3 scripts/new_topic.py "미래먹거리: 정밀발효 기반 단백질"`

## openalex_search.py

OpenAlex에서 검색어로 works 메타데이터를 가져와 `literature/library.jsonl`에 누적합니다.

예:

- `python3 scripts/openalex_search.py --query "precision fermentation protein" --per-page 25 --pages 2`

## arxiv_search.py

arXiv에서 검색어로 최신 preprint 메타데이터를 가져와 `literature/library.jsonl`에 누적합니다.

예:

- `python3 scripts/arxiv_search.py --query "cellular agriculture" --max-results 50`

## research_pipeline.py

OpenAlex/arXiv에서 자료를 가져오고, DeepSeek로 “토픽 브리프(읽기 우선순위/클레임/가설/실험/2주 계획)”를 생성해 토픽 폴더에 저장합니다.

사전 준비:

- 환경변수 `DEEPSEEK_API_KEY` 설정
- 모델은 기본 `DEEPSEEK_MODEL=DeepSeek-V3.2-Speciale` (필요 시 변경)

예:

- `python3 scripts/research_pipeline.py --topic topics/001-미래먹거리정밀발효기반단백질 --query "precision fermentation protein"`

## autopilot.py

AI/LLM/소프트웨어공학 논문을 자동 수집하고 “머지 가능한 PR 비율”을 올리는 다음 연구 방향을 요약합니다.

사전 준비:

- `python3 -m pip install -r requirements.txt` (LangGraph 포함)

기본 동작:

- `python3 scripts/autopilot.py` (기본 6시간 동안 주기적으로 업데이트)
- 1회 실행만: `python3 scripts/autopilot.py --run-hours 0`

systemd 유저 타이머:

- `bash scripts/install_autopilot_systemd_user.sh`

### AI-Scientist-v2 연동(옵션)

- 클론: `git clone https://github.com/SakanaAI/AI-Scientist-v2 third_party/AI-Scientist-v2`
- 환경 변수:
  - `export AI_SCIENTIST_HOME=/path/to/third_party/AI-Scientist-v2`
  - `export AI_SCIENTIST_MODEL=deepseek-coder-v2-0724`
  - `export AI_SCIENTIST_ENABLE=1`
  - (선택) `export AI_SCIENTIST_PYTHON=/path/to/conda/env/bin/python`
- 브리지 실행:
  - `python3 scripts/ai_scientist_bridge.py --workshop-file ai_scientist_v2/mergeable_pr_agent.md`
- autopilot과 함께:
  - `python3 scripts/autopilot.py --enable-ai-scientist`
