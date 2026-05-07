---
name: track-tokens
description: |
  현재 Claude Code 세션의 transcript JSONL 을 파싱해 모델별 토큰 사용량 (input / output / cache_read / cache_creation) 과 추정 비용을 집계해서 markdown 또는 JSON 으로 출력. 사용자가 "토큰 얼마 썼어", "토큰 사용량", "이번 세션 토큰", "/track-tokens", "session usage", "비용 얼마", "cost 얼마", "report 에 토큰 추가" 같은 의도를 보이거나, simplify-save · ai-ready-audit 등 보고서 작성 직후 정확한 사용량 섹션을 붙여야 할 때 트리거. 반드시 transcript 에서만 값을 읽고, 추정·하드코딩된 숫자는 출력 금지 — 사용자가 보고서에 적힌 숫자로 의사결정한다는 점을 항상 의식한다.
---

# track-tokens

`message.usage` 필드는 Claude Code 세션 transcript JSONL 안에 매 assistant turn 마다 정확히 기록된다. 이게 토큰 사용량의 단일 진실 소스. 이 스킬은 그 JSONL 을 그대로 합산해 보고서·세션 종료 시점에 정확한 숫자를 내놓는다. **추정·기억으로 토큰 수를 답하지 말 것** — 보고서에 들어가는 숫자가 의사결정 근거가 되므로 transcript 가 없으면 그 사실을 알리고 멈춰야 한다.

## 언제 트리거

- `/track-tokens` (인자 있거나 없거나)
- "이번 세션 토큰 얼마 썼어" / "토큰 사용량" / "비용 얼마"
- simplify-save / ai-ready-audit / 다른 보고서 스킬 직후 사용자가 "사용량 섹션 추가해" / "report 에 토큰 붙여"

자동 트리거 금지 항목:
- 사용자가 묻지 않았는데 보고서 끝에 임의로 토큰 섹션 첨부
- transcript 미발견 시 추정값으로 메우기

## 인자

```
/track-tokens [--format markdown|json] [--no-cost] [--session PATH] [--since ISO8601]
```

전부 생략 가능. 가장 흔한 호출은 인자 없이 → 현재 세션 markdown.

- `--session` : 특정 JSONL 지정. 생략 시 `~/.claude/projects/*/*.jsonl` 중 mtime 최신 자동 선택.
- `--since`   : 그 시각 이후의 turn 만 합산 (예: 보고서 작성 직전 timestamp 를 기록해 두고 그 이후 사용량만 보고할 때).
- `--no-cost` : 비용 컬럼 생략. 가격이 불확실해 보일 때.
- `--pricing PATH` : 비용 단가 JSON 으로 override.

## 절차

### 1. 실행

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/track-tokens/scripts/track_tokens.py \
  --format markdown
```

`${CLAUDE_PLUGIN_ROOT}` 는 플러그인 루트 (`plugins/token-tracker/`). Claude Code 가 자동 주입.

### 2. 결과 확인

스크립트 stdout 이 표 형태 markdown:

```
## Token Usage

**Source:** `/home/.../<session>.jsonl`
**Window:** `<first ts>` → `<last ts>`

| Model | Msgs | Input | Output | Cache Read | Cache Write | Cost (USD) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `claude-opus-4-7` | 1,574 | 218,506 | 1,388,300 | 155,774,764 | 3,902,583 | $414.2357 |
| **Total** | ... |
```

비용 단가가 없는 모델은 `Cost` 컬럼이 `—` 로 비고, 본문 끝에 `Note: cost not computed for unknown models: ...` 가 붙는다. 이때 사용자에게 "비용 단가가 등록되지 않은 모델이 있으니 토큰 수만 신뢰해 달라" 안내.

### 3. 보고서에 첨부 (체이닝 시)

simplify-save 등에서 호출한 경우, 산출 markdown 을 보고서 파일 끝에 그대로 append:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/track-tokens/scripts/track_tokens.py \
  --format markdown >> "$REPORT_FILE"
```

### 4. 결과 보고

사용자에게는:
- 총 input / output / cache_read / cache_creation 합계
- (있으면) 추정 비용
- transcript 경로
- 비용 단가가 stale 일 수 있음을 한 줄로 명시

## 단가 (비용 추정용)

`scripts/track_tokens.py` 의 `DEFAULT_PRICING` 에 모델별 1M 토큰당 USD 단가를 박아둠 (input / output / cache_read / cache_creation). Anthropic 공식 가격이 바뀌면 이 dict 를 업데이트하거나 `--pricing custom.json` 으로 override.

비용은 어디까지나 **추정**. 정확한 청구액은 콘솔 invoice 가 진실. 보고서에 적을 때는 "추정" 또는 "estimate" 라고 표기.

## 멱등성 / 부작용

이 스킬은 read-only. transcript 를 파싱만 하고 외부 시스템에 아무것도 쓰지 않는다 (chain 호출자가 보고서 파일에 append 하는 건 호출자의 책임).

## 실패 모드 / 주의

- ❌ 추정값 / 기억 / 어림셈으로 토큰 수 답변
  ✅ 항상 transcript 파싱 결과로만 답변. 못 찾으면 "transcript 미발견" 명시 후 중단
- ❌ 단가가 등록되지 않은 모델에 임의 비용 표기
  ✅ Cost 컬럼 `—`, Note 로 unknown_models 명시
- ❌ 모든 turn 을 합산해 "이번 보고서 작성 비용" 으로 보고
  ✅ 보고서 직전 timestamp 를 `--since` 로 넘기거나, "세션 누적" 임을 명확히 표기
- ❌ Claude / Anthropic 브랜딩 푸터 추가 — 프로젝트 컨벤션 위반
  ✅ 출력 markdown 그대로, 마무리는 호출자 (simplify-save 등) 가 자체 푸터로
- ❌ 다른 사용자의 transcript 까지 포함되도록 glob 확장
  ✅ `find_active_session()` 은 `~/.claude/projects/` 안만 본다. 외부 경로는 `--session` 명시 필요

## 사용 예

### 예시 1: 단독 호출

```
사용자: 이번 세션 토큰 얼마 썼어?
Claude: [/track-tokens]
        → markdown 표 출력 (모델별 + 합계 + 추정 비용)
        → "claude-opus-4-7 모델로 토큰 합 약 1.6억, 추정 $414. 단가는 stale 가능성 있음" 안내
```

### 예시 2: simplify-save 보고서에 사용량 섹션 첨부

```
사용자: /simplify
Claude: [simplify-save] → docs/simplify/2026-05-07-foo.md 생성
사용자: 토큰 사용량도 같이 적어줘
Claude: [/track-tokens --since <보고서 시작 시각>]
        → 결과 markdown 을 보고서 끝에 append
```

### 예시 3: 비용 빼고 토큰만

```
사용자: /track-tokens --no-cost
Claude: → Cost 컬럼 없는 표 출력. 단가 불확실할 때 권장.
```

## See Also

- `simplify-save:simplify-save` — 보고서에 사용량 섹션 붙일 때 자주 chain
- `ai-ready-audit:audit-codebase` — audit 보고서 산출 후 사용량 첨부
- `/cost` (Claude Code 내장) — 빠른 텍스트 요약 (이 스킬은 보고서/JSON 친화 포맷)
