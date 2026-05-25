# <도메인명> 도메인 컨텍스트

## 핵심 개념
- <Aggregate Root: 한 줄 설명>
- <주요 Entity/VO: 한 줄 설명>

## 상태 전이 규칙
- <예: PLACED 상태에서만 결제 가능>
- <예: SHIPPED 이후 취소 불가 (docs/adr/0003 참조)>

## 주요 도메인 이벤트
- <XxxEvent: 무엇을 트리거하는가>

## Aggregate 경계
- 내부 보유(값으로): <...>
- 외부 참조(ID로만): <CustomerId, ProductId ...>

## 외부 의존성 (Driven Ports)
- <XxxPort: 역할>

## 작업 시 주의사항
- <상태 전이는 반드시 도메인 메서드로만>
- <JPA Entity와 도메인 모델은 별도 클래스 + Mapper>

## 관련 문서
- 도메인 모델 상세: docs/domain-model.md
- 용어집: docs/glossary.md
- 주요 결정: docs/adr/
