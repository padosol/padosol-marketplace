# robust-feature-workflow

단일 기능을 **"속도보다 견고함"** 우선으로 만드는 단계별 워크플로우 Claude Code plugin.
도메인 → 애플리케이션 → 어댑터 순(inside-out)으로 **Phase 0~6**를 밟고, 각 Phase 끝마다 "여기까지는 깨지지 않는다"를 보장하는 **게이트**를 통과해야 다음으로 넘어간다.

- **DDD** — Aggregate·불변식·도메인 이벤트·유비쿼터스 언어
- **헥사고날(포트&어댑터)** — 인바운드/아웃바운드 포트, 의존성 방향 = 작업 순서
- **TDD** — 상태 전이를 테스트로 박고, 테스트를 설계 압력으로 사용

## 설치

local marketplace 등록 후:
```
/plugin install robust-feature-workflow@local
```

scope는 **user** 권장 (어느 프로젝트에서나 호출하고 싶을 때).

> 문서(ADR·용어집·CLAUDE.md·README) 작성은 **domain-docs** 플러그인에 위임한다. 워크플로우가
> 문서를 만들 때 `domain-docs` 스킬을 사용하므로, 함께 설치하면 연동이 완성된다.

## 사용

```
이 기능 탄탄하게 만들자: 주문하기 API
```

또는

```
/robust-feature-workflow 주문 생성 기능을 DDD로 처음부터 제대로
```

**쓴다:** 실패 비용이 큰 새 기능(주문/결제/예약/정산 등) — 불변식·상태전이·외부연동이 얽힌 substantial한 기능.
**안 쓴다:** 버그픽스, 리네임, 오타, 단일 함수 리팩토링 같은 trivial한 작업.

진행 상태는 `FEATURE-<기능명>.md`(진행 파일)에 게이트 단위로 남겨, 세션이 끊겨도 이어받는다.

## Phase 요약

| Phase | 내용 | 게이트 |
|---|---|---|
| 0 | 기능 이해 (유스케이스·불변식·Acceptance Criteria) | 한 문장 유스케이스 + 불변식 + GWT 1개 |
| 1 | 도메인 모델링 (VO→Entity→Aggregate, 상태전이 테스트) | 도메인에 인프라 의존성 0, 단위 테스트 통과 |
| 2 | Application Layer (인/아웃바운드 포트, 유스케이스) | Mock 기반 시나리오 전체 통과 |
| 3 | Adapter (Persistence·외부·Web) | 어댑터별 통합 테스트 통과 |
| 4 | End-to-End (실제 인프라, 동시성·장애) | Acceptance Criteria가 E2E로 통과 |
| 5 | 비기능 (관찰성·보안·문서화) | 로깅·메트릭·인가·API 문서 |
| 6 | 코드 리뷰 & 리팩토링 | 셀프 리뷰 통과, PR 관심사별 분리 |

## 구조

```
robust-feature-workflow/
├── .claude-plugin/plugin.json
├── README.md
└── skills/
    └── robust-feature-workflow/
        ├── SKILL.md                  # 7 Phase 워크플로우 + 게이트 + 4원칙
        ├── references/
        │   ├── templates.md          # GWT·상태전이 표·포트 스텁·셀프리뷰 체크리스트
        │   └── spring-stack.md       # Phase별 Spring/JPA/Testcontainers/WireMock 도구
        └── assets/
            ├── acceptance-criteria-template.md
            └── feature-progress-template.md
```

`spring-stack.md`는 Spring 레퍼런스다. 다른 스택이면 동등 도구로 치환하면 된다.
