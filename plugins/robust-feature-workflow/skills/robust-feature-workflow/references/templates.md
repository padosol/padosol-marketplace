# Templates & Patterns

SKILL.md의 각 Phase에서 참조하는 작성법·패턴 모음.

## 1. Given-When-Then (Acceptance Criteria)

Phase 0에서 작성하고 Phase 4에서 그대로 E2E 테스트가 된다. 하나의 시나리오 = 하나의 테스트.

```
Given 재고가 충분한 상품 2개가 카탈로그에 있고
  And 고객이 유효한 배송지를 입력했을 때
When  주문하기를 요청하면
Then  주문 상태가 PLACED가 되고
  And 재고가 예약되며
  And OrderPlacedEvent가 발행된다
```

작성 팁:
- **관찰 가능한 결과만** Then에 쓴다. "내부적으로 X를 호출한다"는 구현 디테일 — 피한다.
- 성공 1개로 끝내지 말 것. 핵심 실패 경로(재고 부족, 결제 실패, 검증 실패)도 각각 시나리오로.
- Given이 길어지면 Aggregate 경계가 넓다는 신호일 수 있다.

## 2. 상태 전이 테스트 표 (Phase 1-3)

상태 머신을 표로 그리고 **각 행을 테스트 1개로** 변환한다. 허용/불허를 빠짐없이.

| From → To | 허용? | 테스트 메서드 |
|---|---|---|
| PLACED → PAID | O | `pay_fromPlaced_success` |
| PLACED → CANCELLED | O | `cancel_fromPlaced_success` |
| PAID → SHIPPED | O | `ship_fromPaid_success` |
| SHIPPED → CANCELLED | X | `cancel_afterShipped_throws` |
| PAID → PAID | X | `pay_twice_throws` |

불허 전이를 빼먹기 쉽다. "이 상태에서 하면 안 되는 것"이 곧 불변식이다.

## 3. 포트 인터페이스 스텁 (Phase 2)

인바운드(유스케이스)와 아웃바운드(외부 의존성)를 인터페이스로만 먼저 정의한다. 구현은 Phase 3.

```java
// 인바운드 포트 — 애플리케이션이 외부에 제공하는 능력
public interface PlaceOrderUseCase {
    OrderResult placeOrder(PlaceOrderCommand command);
}

// 아웃바운드 포트 — 애플리케이션이 외부에 요구하는 능력
public interface OrderRepository {
    Order save(Order order);
    Optional<Order> findById(OrderId id);
}
public interface InventoryPort {
    ReservationResult reserve(ProductId id, int quantity);
}
```

포트를 도출하는 신호: 유스케이스를 구현하다가 "이건 누가 해주지?" 싶으면 그게 아웃바운드
포트다. 도메인이 아니라 애플리케이션 레이어에 둔다(도메인은 외부를 몰라야 하므로).

## 4. ADR (Architecture Decision Record)

되돌리기 어려운 결정마다 한 장. **작성·배치는 `domain-docs` 스킬을 사용한다** — 시스템 결정인지
도메인 결정인지에 따라 둘 위치(`docs/adr/` vs `{도메인}/docs/adr/`)가 달라지고, 템플릿과 인덱스
관리도 그 스킬이 제공한다. 예: "왜 Saga 대신 2PC를 안 썼는가", "왜 이 Aggregate 경계인가",
"@Transactional을 어디 뒀는가".

## 5. 셀프 리뷰 체크리스트 (Phase 6)

- [ ] 도메인 패키지에 프레임워크/인프라 의존성이 없는가
- [ ] 같은 비즈니스 규칙이 여러 레이어에 중복되어 있지 않은가
- [ ] 테스트가 구현 디테일이 아니라 **행위**를 검증하는가
- [ ] 이름이 도메인 언어(유비쿼터스 랭귀지)와 일치하는가
- [ ] 죽은 코드, 의미 없는 TODO, 빈 주석을 정리했는가
- [ ] 모든 불변식과 상태 전이에 대응하는 테스트가 있는가
- [ ] 도메인 이벤트가 실수로 영속화되지 않는가(transient)
- [ ] PR이 관심사별로 쪼개져 리뷰어가 30분 안에 읽을 크기인가
