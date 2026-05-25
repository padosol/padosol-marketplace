# ADR (Architecture Decision Record) 관리

## 두 층위

| 층위 | 위치 | 내용 |
|---|---|---|
| 시스템 ADR | `docs/adr/` | 여러 도메인에 영향, 기술 스택, 통신 방식 |
| 도메인 ADR | `{도메인}/docs/adr/` | 해당 도메인 내부에서만 영향 |

**경계 판단법:** "이 결정을 바꾸려면 다른 도메인 코드도 건드려야 하나?"
- Yes → 시스템 ADR (`docs/adr/`)
- No → 도메인 ADR (`{도메인}/docs/adr/`)

## 가볍게 유지하는 핵심

- 한 페이지 이내.
- "결정"과 "왜"만 명확히.
- 코드 변경 시 ADR 수정이 부담스럽지 않을 정도.
- **남길지 말지 기준:** "이 결정을 6개월 뒤 누군가 의문을 가질 만한가?" 그런 것만 ADR로.
  일상적인 코드 결정까지 ADR로 쓰면 ADR 더미에 묻혀 정작 중요한 게 안 읽힌다.

## 번호 매기기

- 4자리 0패딩 순번: `0001`, `0002` ... 파일명 `0003-cancel-after-shipped-policy.md`.
- 시스템/도메인 각 층위에서 독립적으로 번호를 매긴다(둘 다 0001부터 시작 가능).

## 상태(Status) 생명주기

`Proposed → Accepted`, 이후 바뀌면 `Deprecated` 또는 `Superseded by NNNN`.
- **폐기해도 파일을 삭제하지 않는다.** 상태만 바꾼다. 과거 결정 맥락이 미래 의사결정의 자료다.
- 대체된 ADR은 새 ADR 번호를 가리키고(`Superseded by 0007`), 새 ADR은 옛 것을 참조한다.

## "결과" 섹션에 코드 참조를 박는다

ADR이 코드와 연결되도록 결과 섹션에 실제 경로를 적는다. 나중에 그 코드를 검색하면 ADR이 같이
발견된다 — 문서가 코드와 어긋나는 걸 막는 가장 싼 장치다.

```
## 결과
- 코드: Order.cancel() (order/domain/model/order/Order.java)
- 테스트: OrderTest.cancel_afterShipped_throws()
```

## ADR 인덱스 (`adr/README.md`)

각 `adr/` 폴더에 인덱스를 두고 ADR 추가/상태 변경 시 갱신한다. 템플릿은
`assets/adr-index-template.md`.

```
| 번호 | 제목 | 상태 | 날짜 |
|---|---|---|---|
| 0001 | Order Aggregate 경계 | Accepted | 2026-02-10 |
| 0004 | 동시 주문 동시성 제어 | Superseded by 0007 | 2026-04-01 |
| 0007 | 낙관적 락 기반 동시성 제어 | Accepted | 2026-05-10 |
```

ADR 본문 템플릿은 `assets/adr-template.md`.
