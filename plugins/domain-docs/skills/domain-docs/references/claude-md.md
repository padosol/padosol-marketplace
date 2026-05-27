# CLAUDE.md 계층 전략

Claude Code는 작업 디렉토리부터 루트까지 거슬러 올라가며 `CLAUDE.md`를 **누적해서** 컨텍스트로
읽는다. 이걸 활용해 "작업하는 위치에 따라 필요한 컨텍스트만 들어오게" 계층화한다.

- `order/`에서 작업 → 루트 `CLAUDE.md` + `order/CLAUDE.md`
- `product/`에서 작업 → 루트 `CLAUDE.md` + `product/CLAUDE.md`

다른 도메인의 디테일을 매번 끌어들이지 않아 토큰 효율과 일관성이 좋아진다.

## 루트 CLAUDE.md — 전체 공통 규칙

전체 시스템에 공통되는 것만. 기술 스택, 아키텍처 원칙, 공통 코드 규약, 작업 우선순위, 문서
위치 안내. 템플릿: `assets/root-claude-md-template.md`.

핵심: "도메인별 추가 컨텍스트는 그 도메인 CLAUDE.md를 참조"라는 안내를 넣어 계층을 명시한다.

## 도메인 CLAUDE.md — 도메인 특화 컨텍스트

그 도메인에서 작업할 때 AI가 일관성 있게 움직이기 위한 최소 정보. 템플릿:
`assets/domain-claude-md-template.md`. 보통 다음을 담는다.

- 핵심 개념(Aggregate Root, 주요 Entity/VO)
- 상태 전이 규칙
- 주요 도메인 이벤트
- Aggregate 경계(내부 보유 vs ID로만 참조)
- 외부 의존성(Driven Ports)
- 작업 시 주의사항
- 관련 문서 링크(domain-model.md, glossary.md, adr/)

## 짧게 유지하는 게 핵심

길어지면 안 읽히고, 안 읽히면 갱신도 안 된다. **각 CLAUDE.md 100~200줄 이내**를 목표로.
"전체 코드 컨벤션"이나 "모든 도메인 규칙"을 한 파일에 박지 말 것 — AI가 컨텍스트의 절반을
여기 쓰게 된다. 상세 규칙은 `docs/`로 빼고 CLAUDE.md에선 링크만.

## README와의 분담

같은 폴더에 README와 CLAUDE.md가 공존할 수 있다. **README는 사람용(서술적), CLAUDE.md는
AI용(명령형/규칙형).** 청자와 의도가 다르므로 일부 겹쳐도 괜찮지만, 같은 문단을 복붙하지는
말 것. 규칙·금지사항·작업 순서는 CLAUDE.md, 배경·맥락·사용법은 README.
