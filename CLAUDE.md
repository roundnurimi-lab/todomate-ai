# CLAUDE.md — TodoMate AI

> Claude Code가 이 저장소에서 작업할 때 항상 먼저 읽는 프로젝트 규칙 파일입니다.
> 저장소 루트에 두고, 설계가 바뀌면 이 파일도 같이 고칩니다.

## 1. 프로젝트 개요
- **서비스**: TodoMate AI — LLM 멀티 에이전트 기반 지능형 할 일 관리 시스템
- **핵심 기능**: 자연어 할 일 등록(F1) · 자동 분류/소요시간 예측(F2) · 작업 분해(F3) · 우선순위 추천(F4) · 오늘의 플랜/캘린더 배치(F5) · RAG 생산성 코치(F6) · 알림(F7)
- **요구사항 원본**: `docs/01_기획/[기획] 요구사항 정의서_TodoMate팀.xlsx` (요구사항 ID `REQ-xxx-nnn`)
- **일정**: 2026-11-16 ~ 2026-12-24 (중간발표 12-11, 최종발표 12-24)

## 2. 기술 스택 (임의로 바꾸지 말 것 — 변경 시 PM 승인 + 이 파일 수정)
| 영역 | 스택 |
|---|---|
| Frontend | React 18 + TypeScript + Vite, TailwindCSS, TanStack Query, Zustand |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0(async), Alembic, Pydantic v2 |
| Agent | LangGraph, LangChain, OpenAI `gpt-4o-mini`, MCP Python SDK |
| ML/DL | scikit-learn, LightGBM, transformers(KLUE-RoBERTa), PEFT(QLoRA) |
| Data | MySQL 8.0, Redis 7, ChromaDB, Neo4j 5 |
| Infra | Docker Compose, AWS EC2, GitHub Actions, LangSmith |

## 3. 디렉터리 구조
```
todomate-ai/
├── CLAUDE.md
├── docker-compose.yml
├── .env.example                # 실제 .env는 절대 커밋 금지
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/               # config(pydantic-settings), security, logging
│   │   ├── db/                 # session, models/, migrations(alembic)
│   │   ├── api/v1/             # routers: auth, tasks, plans, coach, admin
│   │   ├── schemas/            # Pydantic 요청/응답 스키마
│   │   ├── services/           # 비즈니스 로직 (라우터는 얇게)
│   │   ├── agents/             # LangGraph: state.py, graph.py, nodes/*.py, prompts/*.md
│   │   ├── ml/                 # 추론 래퍼: classifier.py, duration.py, parser_sllm.py
│   │   └── rag/                # chroma 클라이언트, 임베딩, retriever
│   └── tests/                  # pytest (unit / integration / agent)
├── mcp_servers/                # calendar_server.py, holiday_server.py, task_db_server.py
├── frontend/src/               # pages/, components/, api/, hooks/, stores/
├── ml/                         # 학습 코드 (노트북 X, 스크립트로): data/, train_*.py, eval_*.py
│   └── data/{raw,interim,processed}/   # 원천 데이터는 Git LFS 또는 .gitignore
└── docs/                       # 산출물 (01_기획 ~ 05_발표)
```

## 4. 명령어
```bash
docker compose up -d mysql redis chroma neo4j        # 인프라만 기동
cd backend && uv run uvicorn app.main:app --reload    # API 서버
cd backend && uv run pytest -q                        # 테스트
cd backend && uv run ruff check . && uv run ruff format .
cd backend && uv run alembic revision --autogenerate -m "msg" && uv run alembic upgrade head
cd frontend && pnpm dev | pnpm lint | pnpm test
```

## 5. 코딩 규칙
- **시간대**: DB는 UTC 저장, API 입출력은 ISO-8601(+09:00). 날짜 계산은 `zoneinfo("Asia/Seoul")`.
- **타입**: Python 전 함수 타입힌트, TS `strict: true`. `any` 금지.
- **레이어**: router → service → repository(DB). 라우터에 비즈니스 로직 금지.
- **에러**: `app/core/errors.py`의 도메인 예외 사용, 응답 형식 `{ "code": "...", "message": "..." }`.
- **비밀정보**: API Key·DB 비밀번호 하드코딩 금지. 모두 `Settings`(pydantic-settings)에서 읽기.
- **로그**: `print` 금지, 구조화 로그(JSON) 사용. 사용자 입력 원문·PII는 로그에 남기지 않음.
- **테스트**: 새 서비스/에이전트 노드마다 pytest 작성. LLM 호출은 테스트에서 mock(`FakeListChatModel`).
- **커밋**: Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`), 커밋 메시지에 WBS 번호 `(#4.4)`.

## 6. 에이전트 설계 규칙 (LangGraph)
- State는 `agents/state.py`의 `TodoState(TypedDict)` 하나만 사용. 필드 추가 시 문서(AI 시스템 아키텍처)도 갱신.
  - `messages, user_id, intent, parsed_tasks, subtasks, priorities, plan, rag_context, tool_results, errors, needs_approval`
- 노드: `supervisor, parser, planner, prioritizer, scheduler, coach, review`. 모든 응답은 `review` 노드를 거쳐 출력.
- `recursion_limit=15`, 노드 타임아웃 20초, 외부 API는 tenacity로 지수 백오프 최대 3회.
- 파서는 **자체 sLLM → JSON 스키마 검증 → 실패 시 gpt-4o-mini Fallback** 순서.
- 캘린더 쓰기 등 외부 상태 변경은 `needs_approval=True`로 interrupt → 사용자 승인 후 실행 (Human-in-the-loop).
- RAG 유사도 0.7 미만이면 "정보 부족" 응답. 검색은 항상 `user_id` 메타데이터 필터 포함.
- 프롬프트는 코드에 문자열로 박지 말고 `agents/prompts/*.md`에 분리.

## 7. Claude Code 작업 방식
- 큰 기능은 **Plan 먼저** 제시 → 승인 후 구현. 한 번에 하나의 WBS 작업만.
- 구현 후 반드시 `pytest`/`lint` 실행해서 통과 확인하고 결과를 보고.
- 스키마·API 변경 시 `docs/`의 관련 산출물에 반영할 내용을 요약해서 알려줄 것.
- 모르는 요구사항은 추측하지 말고 요구사항 ID 기준으로 질문.
