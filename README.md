# thesis-research

AI를 “연구팀”처럼 운영하기 위한 작업공간입니다. 여기서 말하는 “미래먹거리”는 food가 아니라 **10–20년 뒤 먹고살 수 있는(경제적 이익) 미래 기회**를 뜻합니다. 핵심은 (1) 논문 수집/정리 → (2) 아이디어/가설화 → (3) 실험/근거 축적 → (4) tech report/논문 형태로 발표로 이어지는 재현 가능한 파이프라인을 유지하는 것입니다.

## Current Focus

- B2B SaaS / 개발툴(엔터프라이즈 플랫폼팀): “머지 가능한 PR 생성(mergeable PR rate)”을 올리는 검증 중심 에이전트
  - `topics/003-enterprise-mergeable-pr-agent/`
  - 로컬 autopilot(지속 실행): `scripts/autopilot.py` + `state/`(로컬 상태 저장)
  - LangGraph로 실행 흐름 구성 + AI-Scientist-v2 아이디어 생성(옵션)

## 빠른 시작

- 의존성 설치:
  - `python3 -m pip install -r requirements.txt`
- DeepSeek 설정(키는 파일에 저장하지 말고 환경변수로만):
  - `cp .env.example .env` 후 `DEEPSEEK_API_KEY`만 채우기 (이 repo는 `.env`를 gitignore 함)
  - 키를 채팅/문서에 노출했다면 즉시 재발급(rotate) 권장
  - DeepSeek API는 고정(다른 LLM으로 교체하지 않음)
- 새 연구 토픽 만들기: `python3 scripts/new_topic.py "미래먹거리: 정밀발효 기반 단백질"`
- 논문 검색(메타데이터 수집):
  - OpenAlex: `python3 scripts/openalex_search.py --query "precision fermentation protein" --per-page 25 --pages 2`
  - arXiv: `python3 scripts/arxiv_search.py --query "cellular agriculture" --max-results 50`
- 검색 + 요약(DeepSeek로 토픽 브리프 생성):
  - `python3 scripts/research_pipeline.py --topic topics/001-미래먹거리정밀발효기반단백질 --query "precision fermentation protein"`
- 지속 실행(로컬, systemd 유저 타이머):
  - 1) `.env` 준비: `cp .env.example .env` 후 `DEEPSEEK_API_KEY` 설정
  - 2) 설치/시작: `bash scripts/install_autopilot_systemd_user.sh`
  - 3) 상태 확인: `systemctl --user status thesis-research-autopilot.timer`
- 단일 실행(기본 6시간 러닝):
  - `python3 scripts/autopilot.py` (기본 6시간 동안 주기적으로 업데이트)
  - 1회 실행만 원하면: `python3 scripts/autopilot.py --run-hours 0`

## AI-Scientist-v2 연동(옵션)

AI-Scientist는 별도 환경(보통 GPU/conda)에서 실행합니다.

- 1) 클론: `git clone https://github.com/SakanaAI/AI-Scientist-v2 third_party/AI-Scientist-v2`
- 2) 환경 변수:
  - `export AI_SCIENTIST_HOME=/path/to/third_party/AI-Scientist-v2`
  - `export AI_SCIENTIST_MODEL=deepseek-coder-v2-0724`
  - `export AI_SCIENTIST_ENABLE=1`
  - (선택) `export AI_SCIENTIST_PYTHON=/path/to/conda/env/bin/python`
- 3) 아이디어 생성 브리지:
  - `python3 scripts/ai_scientist_bridge.py --workshop-file ai_scientist_v2/mergeable_pr_agent.md --max-ideas 3 --num-reflections 2`

autopilot과 함께 쓸 때:

- `python3 scripts/autopilot.py --enable-ai-scientist`
- 논문 요약 템플릿: `templates/paper_summary.md`
- 논문(LaTeX) 빌드(선택): `cd paper && make` (로컬에 `latexmk`/LaTeX 필요)

## 폴더 구조

- `topics/`: 연구 토픽 단위 작업(질문/가설/클레임/실험)
- `literature/`: 논문 메타데이터 라이브러리(검색 결과 누적)
- `templates/`: 요약/실험/회의 노트 템플릿
- `team/`: “AI 연구팀” 역할 정의 및 운영 규칙
- `paper/`: 최종 논문 원고(LaTeX) 스켈레톤
- `scripts/`: 검색/생성 자동화 스크립트
