# domain-docs

도메인 기반(DDD/헥사고날) 코드베이스에서 프로젝트 문서를 **"변경 주체를 따라"** 올바른 계층에 배치하고 작성하는 Claude Code plugin.

핵심 원칙은 하나다:

> **"이 문서가 변경될 때, 어떤 코드가 같이 변경되는가?"** — 같이 변경되는 코드와 같은 곳에 둔다.

ADR(아키텍처 결정 기록) · 계층형 CLAUDE.md · README · 용어집(glossary) · 도메인 간 계약(contracts)을 다루고, 타입별 템플릿을 제공한다.

## 설치

local marketplace 등록 후:
```
/plugin install domain-docs@local
```

scope는 **user** 권장. `robust-feature-workflow`와 함께 설치하면, 워크플로우가 문서를 만들 때 이 플러그인을 권위로 사용한다.

## 사용

```
이 결정 ADR로 남겨줘 — 어느 계층에 둬야 해?
```

```
order 도메인 CLAUDE.md 구성해줘
```

```
프로젝트 문서 구조 잡아줘 / 용어집 만들어줘 / 도메인 간 계약 문서
```

**쓴다:** 결정을 ADR로 기록할 때, 문서를 어느 계층에 둘지 정할 때, 도메인별 CLAUDE.md·README·glossary·contracts를 만들 때, 문서 구조를 처음 세우거나 도메인 추가로 재정비할 때.
**안 쓴다:** 자유형 마크다운 초안(→ `doc-draft`), 기존 CLAUDE.md 품질 감사·개선(→ `claude-md-improver`).

## 배치 결정표

| 변경 주체 | 위치 |
|---|---|
| 전체 시스템 | 루트 `docs/`, 루트 `CLAUDE.md` |
| 여러 도메인 공통 | 루트 `docs/` |
| 특정 도메인만 | `{도메인}/docs/`, `{도메인}/CLAUDE.md` |
| 특정 어댑터만 | 어댑터 폴더 `README` (필요시만) |
| 도메인 간 계약 | 루트 `docs/contracts/` |

**ADR 판단법:** "이 결정을 바꾸려면 다른 도메인 코드도 건드려야 하나?" → Yes면 시스템 레벨(`docs/adr/`), No면 도메인 레벨(`{도메인}/docs/adr/`).

## 구조

```
domain-docs/
├── .claude-plugin/plugin.json
├── README.md
└── skills/
    └── domain-docs/
        ├── SKILL.md                          # 변경주체 원칙 + 배치 결정표 + 디렉토리 구조 + 3대 함정
        ├── references/
        │   ├── adr.md                        # ADR 2층위·번호·Superseded·코드참조·인덱스
        │   ├── claude-md.md                  # 루트/도메인 CLAUDE.md·누적읽기·짧게 유지
        │   └── readme-glossary-contracts.md  # README·glossary·도메인 간 계약·변경관리
        └── assets/                           # 복사용 템플릿 6종
            ├── adr-template.md
            ├── adr-index-template.md
            ├── root-claude-md-template.md
            ├── domain-claude-md-template.md
            ├── domain-readme-template.md
            └── glossary-template.md
```
