# 프로젝트 컨텍스트

## 기술 스택
- <언어/런타임>
- <프레임워크>
- <DB / 캐시>
- <테스트 도구>

## 아키텍처
- <예: 헥사고날(Ports & Adapters) + DDD>
- 도메인별 모듈 분리: <order/, product/ ...>
- 도메인 간 통신은 <예: 이벤트 기반 (직접 호출 금지)>

## 공통 코드 규약
- 도메인 계층에 프레임워크 의존성 금지
- <생성자 주입만, 필드 주입 금지>
- <테스트 네이밍 규칙 등>

## 작업 시 우선순위
1. 도메인 → Application → Adapter 순서
2. 테스트 먼저, 구현 나중
3. 새 외부 의존성 추가 시 ADR 작성

## 문서 위치
- 시스템 결정: docs/adr/
- 도메인 결정: {도메인}/docs/adr/
- 도메인 용어: {도메인}/docs/glossary.md
- 도메인 간 계약: docs/contracts/

## 작업 디렉토리에 따른 추가 컨텍스트
- <order/> 작업 시: <order/CLAUDE.md> 참조
- <product/> 작업 시: <product/CLAUDE.md> 참조
