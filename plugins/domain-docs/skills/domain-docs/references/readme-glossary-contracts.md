# README · Glossary · Contracts · 변경 관리

## README의 두 층위

### 루트 README
시스템 진입점. **신규 입사자가 30분 안에 시스템을 파악**하는 게 목표.
- 시스템 한 줄 설명
- 도메인 목록과 책임
- 로컬 실행 방법
- 주요 문서 링크

### 도메인 README
해당 도메인 진입점. 템플릿: `assets/domain-readme-template.md`.
- 도메인 한 줄 설명
- 핵심 유스케이스 목록
- 외부 의존성(어떤 포트를 가지는지)
- 주요 도메인 이벤트
- 관련 ADR 링크

## Glossary — 의외로 가장 가치 있는 문서

도메인 용어가 명확히 정의되면 팀 의사소통이 빨라지고, 코드 네이밍이 자연스럽게 일관되며,
AI가 도메인 언어(유비쿼터스 랭귀지)를 정확히 쓴다. 템플릿: `assets/glossary-template.md`.

각 용어는 **한글 명칭 + (영문) + 1~2문장 정의**. 특히 "주문 시점 가격(Snapshot Price)"처럼
도메인 고유 개념과, "청약 철회 vs 취소"처럼 헷갈리는 구분을 명확히 적어 둔다.

용어는 그 용어가 속한 계층의 glossary에 둔다(시스템 전체 용어 → `docs/glossary.md`, 도메인
용어 → `{도메인}/docs/glossary.md`).

## 도메인 간 계약(Contracts) — 시스템 레벨

Order가 Product를 참조한다면 그 결정은 **어느 한쪽이 아니라 시스템 레벨**이다. 양쪽 다
영향받으므로 한쪽에 두면 비대칭이 생긴다. 루트로 끌어올린다.

```
docs/adr/0003-event-driven-between-bounded-contexts.md
docs/contracts/
├── product-events.md        # Product가 발행하는 이벤트
├── order-events.md          # Order가 발행하는 이벤트
└── shared-vocabulary.md     # 양쪽이 합의한 ID, 값 객체
```

원칙: 도메인 간 통신은 직접 호출보다 이벤트 기반으로 두고, 그 계약을 여기 문서화한다.

## 변경 관리 — 문서가 썩지 않게

문서의 가장 큰 적은 "코드는 변경됐는데 문서는 그대로". 장치:

**1. PR 체크리스트** (저장소 PR 템플릿에 추가)
```
## 문서 영향
- [ ] 도메인 규칙 변경 → ADR 추가 또는 수정
- [ ] 새 용어 도입 → glossary.md 업데이트
- [ ] 아키텍처 결정 변경 → 관련 CLAUDE.md 업데이트
```

**2. ADR "결과" 섹션에 코드/테스트 경로** → 코드 검색 시 ADR이 같이 발견됨.

**3. CLAUDE.md는 짧게** → 길면 안 읽히고, 안 읽히면 갱신도 안 됨.

**4. 분기별 30분 점검** → ADR 인덱스와 CLAUDE.md를 훑어 폐기된 결정·낡은 컨텍스트 정리.
