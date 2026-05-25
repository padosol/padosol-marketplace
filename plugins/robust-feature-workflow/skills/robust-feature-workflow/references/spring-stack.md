# Spring / JPA 스택 가이드

SKILL.md Phase별로, Spring Boot + JPA 환경에서 쓰는 구체 도구. 다른 스택(NestJS, .NET, Go
등)이면 **같은 역할을 하는 동등 도구**로 치환한다 — 중요한 건 도구가 아니라 각 Phase의 게이트다.

## Phase 1 — 도메인

- 도메인 패키지에 `jakarta.persistence`, `org.springframework.*` import가 들어가면 게이트
  위반. 순수 POJO + 도메인 인터페이스만.
- 도메인 단위 테스트는 `@SpringBootTest` 금지. 그냥 JUnit5 + AssertJ로 인메모리. 컨텍스트
  로딩 없이 1초 안에 끝나야 한다.

## Phase 2 — Application

- Application Service 테스트는 Mockito로 포트를 Mock. `@SpringBootTest` 대신 순수 단위 테스트.
- 호출 순서/롤백 검증은 `InOrder`, `verify(...)`, `verifyNoInteractions(...)`.
- 트랜잭션 경계: 보통 Application Service 메서드에 `@Transactional`. 재고 예약 등 별도
  트랜잭션이 필요하면 `@Transactional(propagation = REQUIRES_NEW)` 또는 Saga 고려.

## Phase 3 — Adapter

### Persistence
- `@DataJpaTest`로 round-trip(저장→조회→도메인 복원). 기본은 인메모리 H2지만, 실제 DB 방언
  차이가 중요하면 `@AutoConfigureTestDatabase(replace = NONE)` + Testcontainers.
- VO는 `@Embeddable` / `@Embedded`. `Money`처럼 통화+금액이면 `@AttributeOverride`로 컬럼명 매핑.
- 컬렉션은 `cascade = ALL`, `orphanRemoval = true` 조합 주의 — Aggregate Root가 라인 생명주기를
  소유한다면 맞지만, 의도치 않은 삭제를 부를 수 있다.
- 도메인 이벤트는 **영속화 금지**. `@Transient` 또는 별도 컬렉션으로 보관 후 발행하고 비운다.
- JPA Entity ↔ 도메인 모델은 별도 클래스 + Mapper로 분리. Entity에 비즈니스 로직 금지.

### 외부 시스템
- HTTP 클라이언트: `RestClient`/`WebClient` + 타임아웃, Resilience4j로 재시도·서킷브레이커.
- 계약 테스트: `@RestClientTest` 또는 WireMock으로 외부 응답 스텁(정상/타임아웃/5xx).

### Web
- DTO(Request/Response)는 web 패키지에만. 도메인 모델을 컨트롤러 밖으로 노출 금지.
- 입구 검증: Bean Validation(`@Valid`, `@NotNull` 등).
- `@WebMvcTest` + MockMvc로 HTTP 계약만 검증, UseCase는 `@MockBean`.
- 예외 매핑: 도메인 예외 → HTTP 상태(400/409 등)는 `@RestControllerAdvice`에 집중.

## Phase 4 — E2E

- `@SpringBootTest` + `@Testcontainers` + `@Container PostgreSQLContainer`. 실제 DB·실제 컨텍스트,
  외부 시스템만 WireMock.
- 동시성: 낙관적 락 `@Version`, 비관적 락 `@Lock(PESSIMISTIC_WRITE)`. 같은 재고 동시 주문
  테스트로 검증.
- 이벤트 발행 후 롤백 위험: Transactional Outbox 패턴(같은 트랜잭션에 outbox row 저장 후
  별도 발행) 또는 `@TransactionalEventListener(phase = AFTER_COMMIT)`.
- 느리므로 `@Tag("e2e")` + CI 전용 프로파일로 분리.

## Phase 5 — 비기능

- 로깅: `MDC.put("orderId", ...)`로 컨텍스트 주입, JSON 구조화 로깅(logstash-encoder 등).
- 메트릭: Micrometer + `@Timed`, 커스텀 카운터(주문 생성/실패).
- 트레이싱: Micrometer Tracing(구 Sleuth)으로 외부 호출에 trace 전파.
- 인가: Spring Security로 타 고객 주문 접근 차단. 민감정보(카드번호 등) 로깅 마스킹.
- 문서화: springdoc-openapi로 OpenAPI 스펙 자동 생성.
