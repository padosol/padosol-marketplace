---
name: await-merge
description: 지정한 GitHub PR (또는 현재 브랜치의 PR) 이 머지될 때까지 60초 간격으로 폴링하고, MERGED 감지 시 develop 으로 이동·pull·머지된 로컬 브랜치 삭제까지 자동 수행한다. 사용자가 PR 을 직접 GitHub 웹에서 머지하는 워크플로우에서 "머지 후 청소까지 손 안 대고" 끝내는 게 목적. 사용자가 "머지 기다려줘", "await merge", "/await-merge", "PR 머지되면 정리" 같은 의도를 보이면 트리거. PR 번호 인자 없으면 현재 브랜치의 open PR 자동 검색. CLOSED (not merged) 상태가 감지되면 cleanup 없이 알림 후 종료.
---

# await-merge

지정 PR 이 머지될 때까지 GitHub 을 폴링하고, 머지 즉시 로컬 cleanup 까지 끝낸다. 사용자가 "PR 은 내가 웹에서 머지할게, 그 뒤 정리는 너가" 흐름을 원할 때 사용.

## 왜 폴링인가 (webhook 안 쓰는 이유)

**진짜 push 모델 (GitHub webhook → smee/cloudflared tunnel → 로컬 listener → inotify)** 이 latency 측면에서 최선이지만, 셋업 비용이 비싸다 (smee 채널 + 데몬 + 항상 켜진 tmux). 60초 폴링은 GitHub 인증 한도 (5000/hr) 의 1.2% 만 쓰고 abuse 트리거 안 한다 — Claude 세션 살아있는 동안만 쓰는 일회성 자동화로는 가성비 우위.

영구 자동화 원하면 별도로 SessionStart hook 또는 webhook 인프라 권장 (이 스킬과 별개).

## GitHub API rate limit 정책 준수

| 한도 | 폴링 사용량 |
|---|---|
| Authenticated REST 5,000 req/hour/user | 60s 폴링 = 60 req/hr (1.2%) |
| Secondary rate limit (rapid sequential) | 60s 간격 sequential 안전 |

**준수 규칙**:
- 기본 폴링 간격 60s, 최소 30s. 사용자가 더 짧게 요청해도 30s 로 clamp.
- 403/429 응답 받으면 즉시 중단하고 사용자에게 알림 (Retry-After 미준수 시 abuse 판정 위험).
- `gh` CLI 인증 (PAT) 으로만 호출. 미인증 60/hr 한도는 1분만에 소진.

## 언제 트리거

사용자가 다음 중 하나를 표현:
- `/await-merge` (인자 있거나 없거나)
- "머지 기다려" / "머지되면 정리" / "PR 머지될 때까지 기다려"
- "머지는 내가 할게, 끝나면 청소"
- 다른 스킬 (예: `/open-pr`) 의 명시적 invocation 지시

자동 트리거 금지: 사용자가 명시 의사 없으면 폴링 시작하지 않음 (세션 리소스 점유).

## 절차

### 1. 대상 PR 결정

인자 우선순위:
1. `args` 에 PR 번호 있으면 그대로 사용 (예: `/await-merge 84`)
2. 없으면 현재 브랜치의 open PR 1건 자동 검색:
   ```bash
   gh pr view --json number,state --jq '.number'
   ```
   - 검색 실패 → 사용자에게 PR 번호 묻고 중단 (자유 입력이라 plain text 질문 OK)
   - 다중 매칭 → 후보 최대 4건 (PR 번호·title·생성일) 을 모아 **`AskUserQuestion` 도구로 TUI 선택지 제시**, 사용자 선택을 받는다. 임의 fallback (예: "가장 최근 open") 금지

### 2. 사전 검증

```bash
# 현재 상태 확인
PR_INFO=$(gh pr view <PR#> --json number,state,headRefName,baseRefName,mergeable,title)
```

확인 사항:
- `state` 가 이미 `MERGED` 면 → 폴링 건너뛰고 곧장 cleanup (섹션 4)
- `state` 가 `CLOSED` 인데 mergedAt null 이면 → 머지 안 된 채 닫힘. cleanup 안 하고 사용자 안내 후 종료
- `state` 가 `OPEN` 이면 정상, 폴링 시작 (섹션 3)
- `headRefName` 을 기억 (cleanup 단계에서 삭제 대상 브랜치)

### 3. Monitor 폴링 무장

`Monitor` 도구를 `persistent: true` 로 무장. 60s 간격, 사용자 요청 짧을 시 30s 까지 허용.

```bash
PR_NUM=<번호>
INTERVAL=${INTERVAL:-60}
while true; do
  resp=$(gh pr view "$PR_NUM" --json state,mergedAt 2>&1)
  if echo "$resp" | grep -q "rate limit\|403\|429"; then
    echo "RATE_LIMITED: $resp"
    break
  fi
  state=$(echo "$resp" | jq -r '.state // "ERROR"')
  case "$state" in
    MERGED) echo "PR_MERGED"; break ;;
    CLOSED) echo "PR_CLOSED_NOT_MERGED"; break ;;
    OPEN) ;;  # 계속
    *) echo "UNKNOWN_STATE: $state"; break ;;
  esac
  sleep "$INTERVAL"
done
```

`description` 에 PR 번호 + 브랜치명 명시 (예: "PR #84 머지 폴링 (chore/MP-16-...)").

### 4. 이벤트 처리

Monitor 알림 받으면:

#### `PR_MERGED`

1. **default 브랜치 동적 조회 (하드코딩 금지)**:
   ```bash
   DEFAULT_BRANCH=$(gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name')
   ```
   `develop` / `main` / 그 외 무엇이든 리포가 알려주는 값을 그대로 사용. PR 의 `baseRefName` 도 보조 신호로 활용 가능 (release 브랜치로 머지된 경우 대응).
2. 워킹 트리 깨끗한지 확인:
   ```bash
   git status --porcelain
   ```
   non-empty 면 자동 cleanup 중단, 사용자에게 stash/commit 요청.
3. 현재 브랜치(`CUR=$(git branch --show-current)`) 에 따라 분기:
   - `CUR == headRefName` (작업 브랜치 위): `git switch "$DEFAULT_BRANCH"` → pull → branch -d
   - `CUR == DEFAULT_BRANCH` (이미 default 위): **switch 생략**, 바로 pull → branch -d. **pull 을 절대 건너뛰지 말 것** — 이게 "머지 후 로컬 default 가 최신화 안 됨" 버그의 원인.
   - 그 외 (다른 feature 브랜치 등): 자동 cleanup 보류, 사용자에게 보고만. 자동 switch 시 작업 중 변경분 손실 위험.
4. cleanup 실행 (분기 1·2 공통):
   ```bash
   git pull --ff-only
   git branch -d "$HEAD_REF_NAME"   # -D 금지: merged 아니면 거부되도록
   ```
   `-d` 가 거부하면 ("not fully merged") 에러 그대로 사용자에게 노출. 강제 삭제 자동 fallback 금지.
5. 사용자에게 결과 보고 + Linear MP 키가 있으면 자동 Done 전이 안내 (Linear GitHub Integration 이 처리).

#### `PR_CLOSED_NOT_MERGED`
- cleanup 절대 자동 수행 금지 (작업 손실 위험)
- 사용자에게 "PR 닫힘, 머지 안 됨" 알림 후 **`AskUserQuestion` 도구로 TUI 선택지 제시** — header `Closed PR`, options: `재오픈` / `브랜치 보존 (cleanup 안 함)` / `수동 삭제`. plain text 로 "어떻게 할까요?" 질문 금지.

#### `RATE_LIMITED`
- 즉시 중단, 사용자에게 GitHub API 한도 도달 알림. 1시간 후 재시도 권장.

#### `UNKNOWN_STATE`
- 로깅 후 종료. 수동 확인 요청.

### 5. 세션 종료 시

Monitor 는 세션 lifetime 동안 유지 (`persistent: true`). 사용자가 세션 종료하면 자연 stop. 이 경우 머지 감지 못할 수 있으므로, 무장 시 사용자에게 "이 세션 살아있는 동안만 동작" 명시.

## 실패 모드 / 주의

- ❌ `git switch develop` 처럼 default 브랜치 하드코딩 — main 리포에서 switch 실패로 cleanup 전체 중단 + pull 누락
  ✅ `gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'` 로 매번 조회
- ❌ "현재 브랜치 ≠ headRefName" 만 보고 cleanup 전체 보류 — 사용자가 이미 default 로 이동해 있으면 pull 까지 건너뜀
  ✅ 3-way 분기 (headRefName / default / 그 외) 로 default 위에 있을 땐 pull 만이라도 수행
- ❌ `git branch -D` 사용 — 머지 안 된 브랜치도 강제 삭제, 작업 손실
  ✅ `git branch -d` 만 사용. git 이 거부하면 cleanup 실패로 보고
- ❌ 워킹 트리 dirty 한 상태에서 `git switch` — 변경 사항 손실 또는 conflict
  ✅ `git status --porcelain` 가드 후 진행
- ❌ 폴링 간격 30s 미만 — secondary rate limit 위험
  ✅ 최소 30s clamp, 기본 60s
- ❌ 이미 MERGED 인 PR 에 폴링 시작 — Monitor 리소스 낭비
  ✅ 사전 검증에서 즉시 cleanup 분기
- ❌ 자동 트리거 (다른 스킬에서 호출 안 했는데 임의 무장) — 사용자 모르는 폴링
  ✅ 명시적 invocation 또는 스킬 chain 만 허용

## 사용 예

```
사용자: PR #84 머지되면 청소까지 부탁해
Claude: [/await-merge 84 호출]
        → 사전 검증 (state=OPEN) → Monitor 무장
        ... (60초 간격 폴링) ...
        Monitor 알림: PR_MERGED
        → git switch develop → pull → branch -d → 보고
```

## See Also

- `/open-pr` — PR 생성 후 await-merge 자동 chain (이 플러그인)
- GitHub REST rate limit 문서: https://docs.github.com/en/rest/overview/rate-limits-for-the-rest-api
- 더 가벼운 영구 자동화: `~/.claude/settings.json` 의 SessionStart hook (세션 시작 시 머지 감지)
