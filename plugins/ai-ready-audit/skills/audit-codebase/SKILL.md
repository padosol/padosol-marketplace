---
name: audit-codebase
description: 임의의 git 리포지토리가 AI 에이전트와 협업하기 좋은 상태(AI-Ready)인지 100점 7-카테고리 루브릭으로 감사한다. JSON 점수표, 한국어 HTML 대시보드, ROI 우선순위 액션 리스트를 산출한다. 사용자가 "AI-ready 평가", "AI 친화 점수", "codebase 감사", "rubric으로 점수", "context layer 평가", "AI navigation 점수", "이 리포 AI 친화적인가" 같은 의도를 보이면 무조건 트리거한다. 한 codebase 전체를 평가하는 작업이라 즉시 답하기보다 이 스킬을 써야 한다.
---

# audit-codebase

## 무엇을 하는가

지정한 git 리포지토리를 7개 카테고리(A~G, 총 100점) 루브릭으로 평가하고 다음 3가지를 출력한다:

1. **scorecard.json** — 카테고리/항목별 점수 + 근거
2. **report.html** — 한국어 대시보드 (점수, ROI 액션 리스트, broken refs 경고)
3. (필요 시) **action_plan.md** — ROI 순서대로 정리된 개선 항목

루브릭의 자세한 정의는 `references/rubric.json`에 있다. 사용자가 별도 지정 없으면 이 파일을 그대로 사용한다.

## 핵심 원칙

- **신호 추출은 결정적, 점수 부여는 판단**: `scripts/audit.py`가 mechanical signal(파일 수, 섹션 존재, 깨진 참조 등)을 JSON으로 뽑고, **너(Claude)가 신호 + 실제 파일 내용을 보고 점수를 매긴다**. 스크립트가 매기지 않는 이유는 "주석에 흩어진 tribal knowledge가 충분한지"같은 항목은 본문 의미를 봐야만 평가 가능하기 때문.
- **샘플링 검증**: signal로 잡히지 않는 미묘한 부분(B4 non-obvious patterns의 실효성, C tribal knowledge의 깊이 등)은 대표 모듈 1~2개의 context 파일을 직접 읽고 판단한다.
- **점수에 반드시 "근거" 필드**: 각 카테고리/항목에 한국어 1~2문장 reason을 붙인다. ROI 액션 리스트가 의미 있어지려면 "왜 이 점수인가"가 명확해야 한다.

## 절차

### 1. 입력 받기

사용자가 명시 안 했으면 cwd를 기본값으로. 보통:
- 이 스킬을 부른 위치 = 평가 대상 리포 루트
- 출력 디렉토리 기본값: `<repo>/.ai-ready-audit/<YYYY-MM-DD>/`

```
TARGET_REPO=<사용자 지정 또는 cwd>
OUT_DIR=$TARGET_REPO/.ai-ready-audit/$(date +%Y-%m-%d)
mkdir -p "$OUT_DIR"
```

### 2. mechanical signals 추출

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/audit-codebase/scripts/audit.py \
  "$TARGET_REPO" --pretty --out "$OUT_DIR/signals.json"
```

생성된 `signals.json`을 읽어서 다음을 머릿속에 정리한다:
- 핵심 모듈 수, 모듈별 context 파일 유무
- CLAUDE.md/AGENTS.md 라인 분포 (B1 conciseness 기준 25-35줄)
- 섹션 카운트(commands/key files/gotcha/see also)
- Five-Question 모듈 커버리지(C 평가)
- architecture/dependency 문서 유무(D)
- CI lint/test/typecheck/freshness 유무(E, F)
- broken_refs_sample (E1)

### 3. 대표 파일 직접 읽기 (샘플링)

신호만으로 점수가 모호한 항목을 위해 다음을 읽는다:
- 루트 `CLAUDE.md` (또는 첫 발견된 primary context)
- `signals.modules` 중 file_count 상위 1~2개 모듈의 context 파일
- `references/rubric.json` 전체 (점수 부여 기준 일치를 위해)

읽은 결과를 다음 관점에서 평가:
- **B 항목별**: 실제로 quick commands가 copy-paste 가능한가? key files가 3-5개로 좁혀졌나? gotcha가 "왜 실패하는지" 설명되어 있나?
- **C Five Questions**: 모듈별 5질문에 답이 보이는가? signals의 hit count는 키워드 매칭일 뿐이라 의미 깊이는 본문을 봐야 안다.
- **D**: ARCHITECTURE.md 등이 있어도 실제 의존성 표기가 ownership/data flow를 담는지.

### 4. scorecard.json 작성

`$OUT_DIR/scorecard.json`을 다음 스키마로 직접 생성:

```json
{
  "repo_name": "lol-server",
  "repo_path": "/home/padosol/lol/lol-server",
  "git_head": "<from signals>",
  "scanned_at": "<from signals>",
  "tracked_files": <from signals.totals>,
  "scores": {
    "A": { "score": 5, "reason": "5개 모듈 중 root CLAUDE.md만 존재, 모듈별 context 없음", "action_hint": "module/core, module/infra/api 각각에 CLAUDE.md 추가" },
    "B": {
      "score": 12,
      "items": {
        "B1": { "score": 2, "reason": "CLAUDE.md 187줄로 권장(25-35) 초과" },
        "B2": { "score": 4, "reason": "## 빌드 및 실행 명령어 섹션 존재" },
        "B3": { "score": 0, "reason": "key files 섹션 없음" },
        "B4": { "score": 4, "reason": "..." },
        "B5": { "score": 2, "reason": "..." }
      }
    },
    "C": { "score": 8, "reason": "..." },
    "D": { "score": 5, "reason": "..." },
    "E": {
      "score": 9,
      "items": {
        "E1": { "score": 3, "reason": "broken refs 50건 추정. 다만 다수가 의미상 정상이라 차감 부분만 -2" },
        "E2": { "score": 2, "reason": "..." },
        "E3": { "score": 3, "reason": "test/lint CI 일부 존재" },
        "E4": { "score": 1, "reason": "..." }
      }
    },
    "F": { "score": 3, "reason": "..." },
    "G": { "score": 0, "reason": "AI 성능 측정 흔적 없음" }
  }
}
```

규칙:
- **A, C, D, F, G**는 카테고리 단위 단일 점수
- **B, E**는 `items.<id>` 하위 점수 합이 카테고리 점수가 됨 (수동 검증)
- 점수는 rubric의 levels에 정의된 값 중 하나만 사용 (예: A는 0/5/10/15)
  - sub-item(B*, E*)은 0~max 정수 자유. 단 full_criteria 미달이면 그에 비례해 감점.
- `reason`은 한국어 1~2문장. signal 인용("CLAUDE.md 187줄")이 가장 강력함.
- `action_hint`(선택)는 다음 단계로 무엇을 하면 점수가 오를지. 없으면 rubric의 next-level criteria가 자동 채워진다.

### 5. 대시보드 + ROI 렌더

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/audit-codebase/scripts/render_dashboard.py \
  "$OUT_DIR/scorecard.json" \
  --signals "$OUT_DIR/signals.json" \
  --out "$OUT_DIR/report.html"
```

스크립트가 자동으로:
- 총점 + grade 산출
- 카테고리 카드 + 바 차트
- ROI 정렬한 액션 표 (`gap / effort_weight` 내림차순)
- broken refs 경고 박스

### 6. 사용자에게 보고

다음 형식으로 답하라:

```
## AI-Ready Audit · <repo_name>

총점: **<TOTAL>/100** — <Grade Level>

| 카테고리 | 점수 | 핵심 사유 |
|---|---|---|
| A. AI Navigation & Coverage | 5/15 | ... |
| ... |
| G. Agent Performance Outcomes | 0/5 | ... |

### 우선순위 액션 (ROI top 3)

1. **B3 Key Files** (+4점, low effort) — ...
2. **A Navigation Coverage** (+5점, medium effort) — ...
3. **F Freshness** (+4점, medium effort) — ...

📂 산출물:
- `<OUT_DIR>/signals.json`
- `<OUT_DIR>/scorecard.json`
- `<OUT_DIR>/report.html` ← 브라우저로 열어서 확인
```

## 자주 하는 실수 (피하라)

- **신호를 곧 점수로 환산하지 말 것**. 예: "section_with_gotcha=2"라고 곧장 만점 주면 안 됨. 본문 깊이를 봐야 함.
- **broken_refs_in_docs 절댓값에 휘둘리지 말 것**. audit.py는 path 매칭이 단순해서 실제로는 존재하는 모듈 내부 경로도 broken으로 잡힌다. 샘플 5~10개를 직접 검증한 비율로 E1 차감.
- **G(Agent Performance Outcomes)는 default 0**. metrics dashboard / before-after benchmark 흔적이 없으면 0점이 맞다.
- **Sub-item이 있는 B/E는 카테고리 score를 따로 안 매김**. items 합이 자동으로 카테고리 점수가 된다고 간주 (render_dashboard.py가 합산).
- **보고는 한국어로**. dashboard도 한국어로 렌더된다.

## 큰 리포에서 (성능)

- audit.py는 보통 수 초 내. 단 1만 파일 이상이면 git ls-files 캐시가 도움.
- Claude의 샘플링 단계가 가장 느림. 모듈이 많으면 file_count 상위 3개만 보고 나머지는 signal만 활용.
- 출력물이 그 자리에 .ai-ready-audit/<date>/로 쌓이므로 git에서 무시하도록 .gitignore 한 줄 추가 권장:
  ```
  .ai-ready-audit/
  ```
