---
name: await-merge
description: 지정한 PR/MR (또는 현재 브랜치의 PR/MR) 이 머지될 때까지 60초 간격으로 폴링하고, MERGED 감지 시 base 브랜치로 이동·pull·머지된 로컬 브랜치 삭제까지 자동 수행한다. GitHub (gh) 와 GitLab (glab) 양쪽 지원 — host 는 .orch/settings.json 의 git_host 또는 인증 상태로 자동 결정. 사용자가 PR/MR 을 직접 웹에서 머지하는 워크플로우에서 "머지 후 청소까지 손 안 대고" 끝내는 게 목적. 사용자가 "머지 기다려줘", "await merge", "/await-merge", "PR 머지되면 정리" 같은 의도를 보이면 트리거. PR 번호 인자 없으면 현재 브랜치의 open PR/MR 자동 검색. CLOSED (not merged) 상태가 감지되면 cleanup 없이 알림 후 종료.
---

# await-merge

지정 PR/MR 이 머지될 때까지 host 를 폴링하고, 머지 즉시 로컬 cleanup 까지 끝낸다. 사용자가 "PR/MR 은 내가 웹에서 머지할게, 그 뒤 정리는 너가" 흐름을 원할 때 사용.

## 왜 폴링인가 (webhook 안 쓰는 이유)

**진짜 push 모델 (host webhook → smee/cloudflared tunnel → 로컬 listener → inotify)** 이 latency 측면에서 최선이지만, 셋업 비용이 비싸다 (smee 채널 + 데몬 + 항상 켜진 tmux). 60초 폴링은 인증 한도의 1.2% 만 쓰고 abuse 트리거 안 한다 — Claude 세션 살아있는 동안만 쓰는 일회성 자동화로는 가성비 우위.

영구 자동화 원하면 별도로 SessionStart hook 또는 webhook 인프라 권장 (이 스킬과 별개).

## API rate limit 정책 준수

| host | 한도 | 폴링 사용량 |
|---|---|---|
| GitHub | Authenticated REST 5,000 req/hr | 60s 폴링 = 60 req/hr (1.2%) |
| GitLab | Authenticated 2,000 req/min (cloud) | 60s 폴링 = 1 req/min (0.05%) |

**준수 규칙**:
- 기본 폴링 간격 60s, 최소 30s. 사용자가 더 짧게 요청해도 30s 로 clamp.
- 403/429 응답 받으면 즉시 중단하고 사용자에게 알림 (Retry-After 미준수 시 abuse 판정 위험).
- `gh` / `glab` CLI 인증 (PAT) 으로만 호출. 미인증 한도는 1분만에 소진.

## 언제 트리거

사용자가 다음 중 하나를 표현:
- `/await-merge` (인자 있거나 없거나)
- "머지 기다려" / "머지되면 정리" / "PR 머지될 때까지 기다려" / "MR 머지될 때까지"
- "머지는 내가 할게, 끝나면 청소"
- 다른 스킬 (예: `/open-pr`) 의 명시적 invocation 지시

자동 트리거 금지: 사용자가 명시 의사 없으면 폴링 시작하지 않음 (세션 리소스 점유).

## 절차

### 0. host 추상화 sourcing

```bash
source "${CLAUDE_PLUGIN_ROOT}/scripts/host.sh"
gf_detect_host   # GF_HOST / GF_CLI / GF_PR_NOUN 결정
```

이하 본문에서 **`PR`** 은 GitHub PR / GitLab MR 양쪽을 의미.

### 1. 대상 PR 결정

인자 우선순위:
1. `args` 에 PR 번호 있으면 그대로 사용 (예: `/await-merge 84`)
2. 없으면 현재 브랜치의 open PR 1건 자동 검색:
   ```bash
   pr_num="$(gf_pr_current_open_num)"
   ```
   - 검색 실패 → 사용자에게 PR 번호 묻고 중단 (자유 입력이라 plain text 질문 OK)
   - 다중 매칭 → 후보 최대 4건 (PR 번호·title·생성일) 을 모아 **`AskUserQuestion` 도구로 TUI 선택지 제시**, 사용자 선택을 받는다. 임의 fallback (예: "가장 최근 open") 금지

### 2. 사전 검증

```bash
PR_INFO="$(gf_pr_info "$pr_num")"
# 표준화된 JSON: {number, state, headRefName, baseRefName, mergedAt, url}
state="$(echo "$PR_INFO" | jq -r '.state')"
head_ref="$(echo "$PR_INFO" | jq -r '.headRefName')"
base_ref="$(echo "$PR_INFO" | jq -r '.baseRefName')"
merged_at="$(echo "$PR_INFO" | jq -r '.mergedAt // empty')"
```

`gf_pr_info` 가 host 차이를 흡수해 `state` 는 항상 `OPEN`/`MERGED`/`CLOSED` 셋 중 하나. GitLab `opened` → `OPEN` 으로 정규화됨.

확인 사항:
- `state` 가 이미 `MERGED` 면 → 폴링 건너뛰고 곧장 cleanup (섹션 4)
- `state` 가 `CLOSED` 인데 `merged_at` 빈 값이면 → 머지 안 된 채 닫힘. cleanup 안 하고 사용자 안내 후 종료
- `state` 가 `OPEN` 이면 정상, 폴링 시작 (섹션 3)
- `head_ref` 을 기억 (cleanup 단계에서 삭제 대상 브랜치)

### 3. Monitor 폴링 무장

`Monitor` 도구를 `persistent: true` 로 무장. 60s 간격, 사용자 요청 짧을 시 30s 까지 허용.

```bash
PR_NUM=<번호>
INTERVAL=${INTERVAL:-60}
while true; do
  info="$(gf_pr_info "$PR_NUM" 2>&1)"
  if echo "$info" | grep -qiE 'rate limit|403|429'; then
    echo "RATE_LIMITED: $info"
    break
  fi
  state="$(echo "$info" | jq -r '.state // "ERROR"')"
  case "$state" in
    MERGED) echo "PR_MERGED"; break ;;
    CLOSED) echo "PR_CLOSED_NOT_MERGED"; break ;;
    OPEN)   ;;  # 계속
    *)      echo "UNKNOWN_STATE: $state"; break ;;
  esac
  sleep "$INTERVAL"
done
```

`description` 에 PR 번호 + host + 브랜치명 명시 (예: "GitHub PR #84 머지 폴링 (chore/MP-16-...)" / "GitLab MR !12 머지 폴링").

### 4. 이벤트 처리

Monitor 알림 받으면:

#### `PR_MERGED`

1. **base 브랜치 결정 — orch settings 의 프로젝트별 값 우선**:

   진실의 원천은 `.orch/settings.json` 의 `projects.<alias>.default_base_branch`. **프로젝트마다 다르므로 글로벌 fallback 에 의존하지 말 것** — alias 마다 명시되어 있어야 한다 (`validate-harness` SessionStart hook 이 누락 차단).

   ```bash
   # PWD 부터 부모 traverse — .orch 디렉토리가 있는 첫 위치
   ORCH_SETTINGS=""
   d="$PWD"
   while [ "$d" != "/" ]; do
     if [ -f "$d/.orch/settings.json" ]; then ORCH_SETTINGS="$d/.orch/settings.json"; break; fi
     d="$(dirname "$d")"
   done

   BASE_BRANCH=""
   if [ -n "$ORCH_SETTINGS" ]; then
     # cwd 가 어떤 alias.path 와 가장 길게 prefix-match 하는지로 alias 결정
     alias=$(jq -r --arg cwd "$PWD" '
       .projects // {} | to_entries
       | map(select($cwd | startswith(.value.path)))
       | sort_by(.value.path | length) | reverse | .[0].key // ""
     ' "$ORCH_SETTINGS")
     if [ -n "$alias" ]; then
       BASE_BRANCH=$(jq -r --arg a "$alias" '.projects[$a].default_base_branch // ""' "$ORCH_SETTINGS")
     fi
   fi

   # orch 외부 (settings.json 없음) 또는 alias 매칭 실패 시에만 host default fallback
   if [ -z "$BASE_BRANCH" ]; then
     BASE_BRANCH="$(gf_default_branch)"
   fi
   [ -n "$BASE_BRANCH" ] || { echo "ERROR: BASE_BRANCH 결정 실패"; exit 1; }
   ```

   - **orch 워크스페이스 안에서 alias 매칭 성공인데 값이 빈 경우는 도달 불가** — hook 이 사전 차단. 도달했다면 hook 우회되었다는 신호 (예: 캐시된 plugin 구버전) — 사용자에게 보고.
   - **PR.baseRefName 사전 검증**: `gf_pr_info` 의 `baseRefName` 값이 `BASE_BRANCH` 와 다르면 (예: release 브랜치로 머지) 경고하고 cleanup 보류 — 자동 switch 시 사용자가 기대한 branch 와 어긋남.
2. 워킹 트리 깨끗한지 확인:
   ```bash
   git status --porcelain
   ```
   non-empty 면 자동 cleanup 중단, 사용자에게 stash/commit 요청.
3. 현재 브랜치(`CUR=$(git branch --show-current)`) 에 따라 분기:
   - `CUR == head_ref` (작업 브랜치 위): `git switch "$BASE_BRANCH"` → pull → branch -d
   - `CUR == BASE_BRANCH` (이미 base 위): **switch 생략**, 바로 pull → branch -d. **pull 을 절대 건너뛰지 말 것** — "머지 후 로컬 base 가 최신화 안 됨" 버그의 원인.
   - 그 외 (다른 feature 브랜치 등): 자동 cleanup 보류, 사용자에게 보고만. 자동 switch 시 작업 중 변경분 손실 위험.
4. cleanup 실행 (분기 1·2 공통):
   ```bash
   git pull --ff-only
   git branch -d "$HEAD_REF_NAME"   # -D 금지: merged 아니면 거부되도록
   ```
   `-d` 가 거부하면 ("not fully merged") 에러 그대로 사용자에게 노출. 강제 삭제 자동 fallback 금지.
5. 사용자에게 결과 보고 + Linear MP 키가 있으면 자동 Done 전이 안내 (Linear의 GitHub/GitLab Integration 이 처리).

#### `PR_CLOSED_NOT_MERGED`
- cleanup 절대 자동 수행 금지 (작업 손실 위험)
- 사용자에게 "PR 닫힘, 머지 안 됨" 알림 후 **`AskUserQuestion` 도구로 TUI 선택지 제시** — header `Closed PR`, options: `재오픈` / `브랜치 보존 (cleanup 안 함)` / `수동 삭제`. plain text 로 "어떻게 할까요?" 질문 금지.

#### `RATE_LIMITED`
- 즉시 중단, 사용자에게 host API 한도 도달 알림. 1시간 후 재시도 권장.

#### `UNKNOWN_STATE`
- 로깅 후 종료. 수동 확인 요청.

### 5. 세션 종료 시

Monitor 는 세션 lifetime 동안 유지 (`persistent: true`). 사용자가 세션 종료하면 자연 stop. 이 경우 머지 감지 못할 수 있으므로, 무장 시 사용자에게 "이 세션 살아있는 동안만 동작" 명시.

## 실패 모드 / 주의

- ❌ `gh` / `glab` 직접 호출 — host 분기가 흩어져 한쪽 host 만 동작
  ✅ 항상 `gf_pr_*` helper 경유 (정규화된 state 사용)
- ❌ base 브랜치 하드코딩 (`develop` / `main`) 또는 글로벌 단일값 의존 — 프로젝트마다 base 가 다른데 한 값으로 고정 → switch 실패로 cleanup 전체 중단 + pull 누락
  ✅ orch settings.json 의 `projects.<alias>.default_base_branch` (프로젝트별, validate-harness hook 이 필수 보장), orch 외부 환경에서만 `gf_default_branch` fallback
- ❌ "현재 브랜치 ≠ headRefName" 만 보고 cleanup 전체 보류 — 사용자가 이미 base 로 이동해 있으면 pull 까지 건너뜀
  ✅ 3-way 분기 (head_ref / base / 그 외) 로 base 위에 있을 땐 pull 만이라도 수행
- ❌ PR baseRefName 검증 생략 — PR 이 release/staging 같은 비기본 브랜치로 머지된 경우에도 default 로 switch 해버려 mismatch
  ✅ `gf_pr_info` 의 `baseRefName` 으로 PR 실제 base 와 결정한 BASE_BRANCH 비교, 다르면 사용자 확인
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

GitHub:
```
사용자: PR #84 머지되면 청소까지 부탁해
Claude: [/await-merge 84 호출]
        → source host.sh, gf_detect_host (host=github)
        → 사전 검증 (state=OPEN) → Monitor 무장
        ... (60초 간격 폴링) ...
        Monitor 알림: PR_MERGED
        → git switch develop → pull → branch -d → 보고
```

GitLab:
```
사용자: MR !12 머지되면 청소
Claude: → gf_detect_host (host=gitlab)
        → gf_pr_info: state=OPEN, source_branch=feat/x
        → 폴링 ... → state=MERGED
        → cleanup (base branch from orch settings)
```

## See Also

- `/open-pr` — PR/MR 생성 후 await-merge 자동 chain (이 플러그인)
- `scripts/host.sh` — gh/glab 추상화 (이 플러그인)
- GitHub REST rate limit: https://docs.github.com/en/rest/overview/rate-limits-for-the-rest-api
- GitLab API rate limit: https://docs.gitlab.com/ee/user/gitlab_com/index.html#gitlabcom-specific-rate-limits
- 더 가벼운 영구 자동화: `~/.claude/settings.json` 의 SessionStart hook (세션 시작 시 머지 감지)
