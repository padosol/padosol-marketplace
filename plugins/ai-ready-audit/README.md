# ai-ready-audit

임의의 git 리포지토리를 **AI-Ready 루브릭(100점, 7 카테고리)** 으로 감사하고 다음을 산출하는 Claude Code plugin.

- `signals.json` — 기계적 추출 신호 (파일 통계, 섹션 존재 여부, 깨진 참조 등)
- `scorecard.json` — Claude가 채점한 카테고리별 점수 + 근거
- `report.html` — 한국어 대시보드 + ROI 우선순위 액션 리스트

## 설치

local marketplace 등록 후:
```
/plugin install ai-ready-audit@local
```

scope는 **user** 권장 (어느 프로젝트에서나 호출하고 싶을 때). 특정 리포에서만 쓰려면 **local** scope.

## 사용

```
이 리포 AI-ready 점수 평가해줘
```

또는

```
/audit-codebase
```

평가는 cwd 기준. 다른 리포는 경로를 같이 주면 된다:
```
/path/to/another-repo 의 AI-ready audit 돌려줘
```

산출물은 `<repo>/.ai-ready-audit/<YYYY-MM-DD>/` 에 쌓인다.

## 루브릭

`skills/audit-codebase/references/rubric.json` 참조. 7 카테고리:

| ID | 카테고리 | 점수 |
|----|----------|------|
| A | AI Navigation & Coverage | 15 |
| B | Context Document Quality | 20 (5 sub-items × 4) |
| C | Tribal Knowledge Externalization | 20 (Meta Five-Question framework) |
| D | Cross-Module Dependency & Data Flow Mapping | 15 |
| E | Verification & Quality Gates | 15 (4 sub-items) |
| F | Freshness & Self-Maintenance | 10 |
| G | Agent Performance Outcomes | 5 |
| **합계** | | **100** |

Grade: 90+ AI-Native, 75+ AI-Ready, 60+ AI-Assisted, 40+ AI-Fragile, <40 AI-Hostile.

## 구조

```
ai-ready-audit/
├── .claude-plugin/plugin.json
├── README.md
└── skills/
    └── audit-codebase/
        ├── SKILL.md             # 절차 (Claude가 따른다)
        ├── scripts/
        │   ├── audit.py         # signal 추출
        │   └── render_dashboard.py  # HTML 렌더
        ├── references/
        │   └── rubric.json      # 채점 기준
        └── assets/
            └── dashboard_template.html
```

루브릭을 회사/팀에 맞게 수정하려면 `references/rubric.json`을 fork.
