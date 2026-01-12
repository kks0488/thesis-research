# thesis-research

AI를 “연구팀”처럼 운영하기 위한 작업공간입니다. 여기서 말하는 “미래먹거리”는 food가 아니라 **10–20년 뒤 먹고살 수 있는(경제적 이익) 미래 기회**를 뜻합니다. 핵심은 (1) 논문 수집/정리 → (2) 아이디어/가설화 → (3) 실험/근거 축적 → (4) tech report/논문 형태로 발표로 이어지는 재현 가능한 파이프라인을 유지하는 것입니다.

## Current Focus

- B2B SaaS / 개발툴(엔터프라이즈 플랫폼팀): “머지 가능한 PR 생성(mergeable PR rate)”을 올리는 검증 중심 에이전트
  - `topics/003-enterprise-mergeable-pr-agent/`
  - 로컬 autopilot(지속 실행): `scripts/autopilot.py` + `state/`(로컬 상태 저장)

## 빠른 시작

- DeepSeek 설정(키는 파일에 저장하지 말고 환경변수로만):
  - `cp .env.example .env` 후 `DEEPSEEK_API_KEY`만 채우기 (이 repo는 `.env`를 gitignore 함)
  - 키를 채팅/문서에 노출했다면 즉시 재발급(rotate) 권장
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
- 논문 요약 템플릿: `templates/paper_summary.md`
- 논문(LaTeX) 빌드(선택): `cd paper && make` (로컬에 `latexmk`/LaTeX 필요)

## 폴더 구조

- `topics/`: 연구 토픽 단위 작업(질문/가설/클레임/실험)
- `literature/`: 논문 메타데이터 라이브러리(검색 결과 누적)
- `templates/`: 요약/실험/회의 노트 템플릿
- `team/`: “AI 연구팀” 역할 정의 및 운영 규칙
- `paper/`: 최종 논문 원고(LaTeX) 스켈레톤
- `scripts/`: 검색/생성 자동화 스크립트
