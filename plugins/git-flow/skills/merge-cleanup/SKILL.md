---
name: merge-cleanup
description: '수동 전용 머지정리 스킬. 오직 사용자가 명시적으로 /merge-cleanup 을 실행할 때만 동작한다 — "머지됐으면 정리해줘" 같은 자연어 의도로 자동 호출하거나, 다른 스킬에서 자동 chain 하지 말 것 (자동 트리거·폴링 없음). 하는 일: 현재 세션의 PR/MR 이 이미 머지되었는지 1회 확인하고, 머지되었으면 그 브랜치의 git worktree 제거 → 로컬 브랜치 삭제 → PR 이 머지된 타겟(base) 브랜치를 원격 최신으로 fast-forward → 정리 결과 요약문 출력까지 한 번에 수행. 아직 안 머지됐으면(OPEN/CLOSED) 아무것도 정리하지 않고 안내 후 종료. GitHub (gh) 와 GitLab (glab) 양쪽 지원 — 플랫폼은 .orch/settings.json 의 git_host 또는 인증 상태로 자동 결정 후 호스트별 명령은 이 스킬 디렉토리의 GITHUB_GUIDE.md / GITLAB_GUIDE.md 를 따른다. PR 번호 인자 없으면 현재 브랜치의 PR 자동 검색.'
---

# merge-cleanup (머지정리)

현재 세션에서 작업한 PR/MR 이 **이미 머지되었는지 1회 확인**하고, 머지되었다면 **워크트리 → 로컬 브랜치 → 타겟 브랜치 최신화** 순으로 정리한 뒤 **요약문**을 보여 준다. 사용자가 웹에서 이미 머지를 눌러 둔 뒤 "이제 로컬 뒷정리 해줘" 흐름을 손 안 대고 끝내려고 만든 스킬.

**수동 전용 · 폴링 없음.** 머지를 기다리지 않는다 (1회 확인만). 아직 안 머지됐으면 정리하지 않고 종료하니, 머지한 뒤 다시 `/merge-cleanup` 을 실행하면 된다.

## 호출 방법 (수동 전용 — 자동 트리거 금지)

- **오직 `/merge-cleanup` 명시 실행에만 동작한다.**
- `/merge-cleanup` 또는 `/merge-cleanup <PR#>`
- ❌ "머지됐으면 정리해줘" 같은 자연어 의도로 **자동 invoke 하지 말 것**
- ❌ open-pr 등 다른 스킬에서 **자동 chain 하지 말 것** (이 스킬은 파괴적 작업 — worktree/브랜치 삭제 — 이라 사용자 명시 실행만 허용)

## 절차

### 0. 플랫폼 탐지 → 가이드 선택

어떤 git 플랫폼인지 **한 번** 결정한다 (결정 순서: `GF_HOST` 환경변수 > `.orch/settings.json` 의 `git_host` > `gh`/`glab` 인증 상태):

```bash
GF_HOST="${GF_HOST:-}"
if [ -z "$GF_HOST" ]; then
  d="$PWD"; orch=""
  while [ "$d" != "/" ]; do
    [ -f "$d/.orch/settings.json" ] && { orch="$d/.orch/settings.json"; break; }
    d="$(dirname "$d")"
  done
  if [ -n "$orch" ] && command -v jq >/dev/null 2>&1; then
    case "$(jq -r '.git_host // empty' "$orch" 2>/dev/null)" in
      github|gitlab) GF_HOST="$(jq -r '.git_host' "$orch")" ;;
    esac
  fi
fi
if [ -z "$GF_HOST" ]; then
  gh_ok=0; glab_ok=0
  command -v gh   >/dev/null 2>&1 && gh   auth status >/dev/null 2>&1 && gh_ok=1
  command -v glab >/dev/null 2>&1 && glab auth status >/dev/null 2>&1 && glab_ok=1
  if   [ "$gh_ok" = 1 ] && [ "$glab_ok" = 0 ]; then GF_HOST=github
  elif [ "$gh_ok" = 0 ] && [ "$glab_ok" = 1 ]; then GF_HOST=gitlab
  elif [ "$gh_ok" = 1 ] && [ "$glab_ok" = 1 ]; then
    echo "ERROR: gh / glab 양쪽 인증 — GF_HOST=github|gitlab 로 명시하거나 .orch/settings.json 의 git_host 설정" >&2; exit 2
  else
    echo "ERROR: gh / glab 모두 미인증 — 'gh auth login' 또는 'glab auth login' 후 재시도" >&2; exit 2
  fi
fi
case "$GF_HOST" in github|gitlab) ;; *) echo "ERROR: GF_HOST='$GF_HOST' 잘못된 값 (github|gitlab)" >&2; exit 2 ;; esac
echo "GF_HOST=$GF_HOST"
```

결정된 플랫폼에 따라 **이후 모든 호스트 명령은 이 스킬 디렉토리의 해당 가이드를 그대로 따른다**:
- `github` → `GITHUB_GUIDE.md`
- `gitlab` → `GITLAB_GUIDE.md`

먼저 해당 가이드를 Read 로 열어 둔다. 본문의 **`<가이드: 섹션명>`** 은 선택된 가이드의 동명 섹션 명령. **SKILL 본문에는 플랫폼 분기를 두지 않는다 — 분기는 가이드 파일에만.** 이하 본문에서 **`PR`** 은 GitHub PR / GitLab MR 양쪽을 의미.

### 1. 대상 PR 결정

인자 우선순위:
1. `args` 에 PR 번호 있으면 그대로 사용 (예: `/merge-cleanup 84`) — 현재 브랜치가 아닌 PR (예: 다른 worktree 에서 머지한 PR) 정리에 필요
2. 없으면 현재 브랜치의 PR 1건을 `<가이드: 현재 브랜치의 PR 번호>` 로 자동 검색:
   - 검색 실패 (현재 브랜치가 타겟/보호 브랜치라 PR 없음 등) → 사용자에게 PR 번호 묻고 중단 (자유 입력이라 plain text 질문 OK). 임의 추측 금지
   - 다중 매칭 → 후보 최대 4건 (PR 번호·title·state) 을 모아 **`AskUserQuestion` 도구로 TUI 선택지 제시**, 사용자 선택을 받는다

### 2. 머지 검증 (1회, 폴링 없음)

`<가이드: PR 정보 조회>` 로 정규화된 JSON `{number, state, headRefName, baseRefName, mergedAt, url}` 을 얻는다 (`PR_INFO`). 가이드 명령이 host 차이를 흡수해 `state` 는 항상 `OPEN`/`MERGED`/`CLOSED` 셋 중 하나:

```bash
STATE="$(echo "$PR_INFO"     | jq -r '.state')"
HEAD_REF="$(echo "$PR_INFO"  | jq -r '.headRefName')"
TARGET="$(echo "$PR_INFO"    | jq -r '.baseRefName')"    # PR 이 머지된 타겟(base) 브랜치 — 최신화 대상
MERGED_AT="$(echo "$PR_INFO" | jq -r '.mergedAt // empty')"
PR_URL="$(echo "$PR_INFO"    | jq -r '.url')"
```

분기:
- `STATE == MERGED` → 정상. 섹션 3 으로 진행
- `STATE == OPEN` → **아직 안 머지됨. cleanup 절대 안 함.** 사용자에게 "아직 open 상태" 알리고, **머지한 뒤 다시 `/merge-cleanup <번호>` 를 실행**하도록 안내 후 종료 (폴링하지 않음)
- `STATE == CLOSED` (merged_at 빈 값) → 머지 안 된 채 닫힘. cleanup 안 하고 사용자 안내 후 종료 (작업 손실 위험)

**`TARGET` (= PR baseRefName) 이 이 스킬이 최신화할 타겟 브랜치의 진실의 원천이다.** orch settings 의 `projects.<alias>.default_base_branch` 와 다르면 (예: release 브랜치로 머지) 요약에 경고로 남기되, 최신화 대상은 실제 머지된 `TARGET` 을 따른다.

### 3. 워크트리 지형 파악

머지 확인 후, 삭제/최신화 대상의 위치를 `git worktree list --porcelain` 으로 한 번에 파악한다:

```bash
# 특정 브랜치가 체크아웃된 worktree 경로 (없으면 빈 문자열)
wt_path_for_branch() {
  git worktree list --porcelain | awk -v ref="refs/heads/$1" '
    /^worktree /        { wt=substr($0, 10) }
    $0 == "branch " ref { print wt; exit }
  '
}

MAIN_WT="$(git worktree list --porcelain | awk '/^worktree /{print substr($0,10); exit}')"  # 항상 첫 항목
CUR_WT="$(git rev-parse --show-toplevel)"        # 지금 세션이 서 있는 worktree
HEAD_WT="$(wt_path_for_branch "$HEAD_REF")"      # 머지된 브랜치가 체크아웃된 worktree (없으면 "")
TARGET_WT="$(wt_path_for_branch "$TARGET")"      # 타겟 브랜치가 체크아웃된 worktree (없으면 "")
```

케이스 분류:
- **Case L (linked worktree)**: `HEAD_WT` 가 비어있지 않고 `HEAD_WT != MAIN_WT` — 머지된 브랜치가 별도 worktree 에 있음. worktree teardown 대상.
- **Case M (main worktree)**: `HEAD_WT == MAIN_WT` — 머지된 브랜치가 메인 체크아웃에 있음. worktree 제거 없이 switch 후 브랜치 삭제.
- **Case N (미체크아웃)**: `HEAD_WT` 빈 값 — 브랜치가 어느 worktree 에도 체크아웃 안 됨. 로컬 브랜치 ref 만 존재하거나 이미 없음.

### 4. 사전 가드

정리 전 반드시 확인 (하나라도 걸리면 해당 파괴적 단계를 건너뛰고 요약에 사유 기록):

1. **자기 자신 worktree 제거 방지 (Case L)**: `CUR_WT == HEAD_WT` 이면 **자동 제거 금지**. 지금 세션이 서 있는 디렉토리를 지우면 이후 셸 작업 경로가 사라진다 (harness cwd 가 삭제된 경로에 묶임). 이 경우 자동 실행하지 말고, 메인 워크트리(`$MAIN_WT`)에서 이 스킬을 다시 실행하거나 아래 수동 명령을 안내한다:
   ```
   메인 워크트리로 이동 후 재실행하세요:  (예)  cd "$MAIN_WT" && /merge-cleanup <번호>
   ```
2. **worktree dirty 가드 (Case L)**: `git -C "$HEAD_WT" status --porcelain` 이 non-empty 면 uncommitted 변경 존재 → **자동 제거 금지** (`--force` 사용 안 함). 사용자에게 commit/stash 후 재시도 요청.
3. **operating worktree dirty 가드 (Case M)**: switch 가 필요한 Case M 에서 `git -C "$MAIN_WT" status --porcelain` non-empty 면 switch 불가 → 브랜치 삭제 보류, 사용자 안내.

### 5. 정리 실행

케이스별로:

#### Case L — worktree teardown
```bash
git worktree remove "$HEAD_WT"          # dirty 면 §4-2 에서 이미 차단됨. --force 금지
git worktree prune                       # stale 관리 파일 청소
git branch -d "$HEAD_REF"                # -D 금지: 머지 안 됐으면 거부되도록. 이미 없으면 무시
```
`operating worktree` (= `CUR_WT`, HEAD_WT 아님) 는 그대로 유지 — 사용자가 자기 브랜치 위에 있으면 건드리지 않는다.

#### Case M — switch 후 삭제
```bash
git -C "$MAIN_WT" switch "$TARGET"      # HEAD_REF 에서 벗어나야 삭제 가능
git -C "$MAIN_WT" branch -d "$HEAD_REF" # -D 금지
```

#### Case N — 브랜치 ref 만 정리
```bash
git branch -d "$HEAD_REF" 2>/dev/null || echo "로컬 브랜치 $HEAD_REF 없음 — 스킵"
```

공통: `git branch -d` 가 "not fully merged" 로 거부하면 (squash merge 등으로 로컬 커밋이 원격 base 에 안 보일 때 발생 가능) **강제 삭제 자동 fallback 금지** — 에러를 그대로 노출하고 사용자에게 확인 요청. squash merge 로 인한 정상 케이스면 사용자 동의 하에 `-D` 사용.

### 6. 로컬 타겟 브랜치 최신화

원격 최신을 받아 로컬 `TARGET` 을 fast-forward 한다. **checkout 여부에 따라 방식이 다르다** (checkout 된 브랜치는 refspec fetch 로 못 옮김):

```bash
git fetch origin --prune
BEFORE="$(git rev-parse "$TARGET" 2>/dev/null || echo '(none)')"

# §5 의 정리로 worktree 지형이 바뀌었을 수 있으니 TARGET_WT 를 다시 조회
TARGET_WT="$(wt_path_for_branch "$TARGET")"

if [ -n "$TARGET_WT" ]; then
  # 타겟이 어딘가 체크아웃돼 있음 → 그 worktree 에서 in-place ff (dirty 면 보류)
  if [ -z "$(git -C "$TARGET_WT" status --porcelain)" ]; then
    git -C "$TARGET_WT" merge --ff-only "origin/$TARGET"
  else
    echo "WARN: $TARGET worktree($TARGET_WT) dirty — 자동 ff 보류"
  fi
else
  # 타겟이 어느 worktree 에도 없음 → ref 직접 ff (working tree 안 건드림, dirty-safe)
  git fetch origin "$TARGET:$TARGET"
fi

AFTER="$(git rev-parse "$TARGET" 2>/dev/null || echo '(none)')"
ADVANCED="$( [ "$BEFORE" != "(none)" ] && git rev-list --count "$BEFORE..$AFTER" 2>/dev/null || echo '?')"
```

- **non-fast-forward 거부**: 로컬 `TARGET` 이 원격과 갈라져 있으면 (드묾 — 로컬에만 있는 커밋) fetch/merge 가 ff 거부한다. **강제 갱신 금지.** 요약에 "로컬 타겟이 원격과 분기됨, 수동 확인 필요" 로 남긴다.
- Case M 에서 §5 의 `git switch "$TARGET"` 직후라면 그 worktree 가 곧 타겟이므로 위 로직이 in-place ff 로 자연 처리된다.

### 7. 요약문 출력

수집한 변수로 사용자에게 markdown 요약을 보여 준다 (Claude 가 렌더). 형식:

```markdown
## ✅ merge-cleanup 요약

- **PR**: #<번호> <제목>  ([링크](<PR_URL>))
- **머지 시각**: <MERGED_AT>
- **삭제된 브랜치**: `<HEAD_REF>` (로컬)
- **제거된 worktree**: `<HEAD_WT>`   ← Case L 만, 아니면 "없음 (메인 체크아웃)"
- **타겟 브랜치 최신화**: `<TARGET>`  <BEFORE 앞7> → <AFTER 앞7>  (+<ADVANCED> commits)
- **현재 위치**: `<정리 후 서 있는 worktree/branch>`

<경고가 있으면 나열: baseRefName≠orch default / dirty 로 스킵된 단계 / ff 거부 / squash 로 -d 거부 등>
```

각 단계에서 **실제로 수행된 것만** 적는다. 스킵/실패한 단계는 사유와 함께 명시 (성공한 것처럼 쓰지 않는다). Linear MP 키가 있으면 "Linear 자동 Done 전이는 host integration 이 처리" 한 줄 덧붙임.

## 실패 모드 / 주의

- ❌ 머지 안 됐는데 (OPEN/CLOSED) cleanup — 작업 손실
  ✅ §2 에서 MERGED 만 진행, OPEN 은 "머지 후 다시 실행" 안내, CLOSED 는 안내 후 종료 (폴링·대기 없음)
- ❌ 자연어 의도로 자동 invoke / 다른 스킬에서 자동 chain — 사용자 모르게 worktree·브랜치 삭제
  ✅ 오직 `/merge-cleanup` 명시 실행에만 동작 (수동 전용)
- ❌ 플랫폼 분기를 SKILL 본문에 인라인 — 한쪽 host 만 동작
  ✅ §0 에서 1회 탐지 후 GITHUB_GUIDE.md / GITLAB_GUIDE.md 의 명령만 사용
- ❌ 지금 서 있는 worktree 를 자동 제거 (`CUR_WT == HEAD_WT`) — 셸 작업 경로 증발, 이후 tool 호출 실패
  ✅ §4-1 에서 감지 시 자동 제거 거부, 메인 워크트리에서 재실행하도록 안내
- ❌ `git worktree remove --force` 또는 `git branch -D` 자동 사용 — 커밋 안 된 변경/미머지 브랜치 소실
  ✅ `--force`/`-D` 금지. dirty 는 §4 가드로 사전 차단, `-d` 거부는 사용자 확인 후에만 `-D`
- ❌ 타겟이 다른 worktree 에 체크아웃됐는데 `git fetch origin TARGET:TARGET` 시도 — git 이 "refusing to fetch into branch checked out" 로 거부
  ✅ §6 에서 `TARGET_WT` 유무로 in-place merge --ff-only vs refspec fetch 분기
- ❌ 로컬 타겟이 원격과 분기됐는데 강제 최신화 — 로컬 커밋 유실
  ✅ ff-only 만 사용, 거부되면 요약에 경고로 남기고 수동 처리 유도
- ❌ 타겟 브랜치를 orch default 로 가정 — PR 이 release 등 다른 base 로 머지됐으면 엉뚱한 브랜치 최신화
  ✅ 최신화 대상은 PR 의 실제 `baseRefName`, orch default 와 다르면 경고만
- ❌ 요약에 스킵된 단계를 성공처럼 기록 — 사용자 오판
  ✅ 실제 수행분만 성공으로, 스킵/실패는 사유와 함께 명시

## 사용 예

Case M (메인 워크트리에서 직접 작업 후 머지):
```
사용자: /merge-cleanup
Claude: → §0 플랫폼 탐지 (github) → GITHUB_GUIDE.md
        → §1 현재 브랜치 feature/... 의 PR #84 확인
        → §2 state=MERGED (baseRefName=main)
        → §3 HEAD_WT == MAIN_WT (Case M), 별도 worktree 없음
        → §5 switch main → branch -d feature/...
        → §6 fetch → main ff (+3 commits)
        → §7 요약 출력
```

Case L (별도 worktree 를 메인 세션에서 정리):
```
사용자: /merge-cleanup 91
Claude: → §2 PR #91 MERGED, headRefName=feat/x, baseRefName=main
        → §3 HEAD_WT=/…/worktrees/x (linked, CUR_WT=메인이라 자기제거 아님)
        → §4 worktree clean 확인
        → §5 worktree remove /…/worktrees/x → prune → branch -d feat/x
        → §6 main 은 미체크아웃 → git fetch origin main:main (+2)
        → §7 요약: worktree 제거됨 + 브랜치 삭제 + main 최신화
```

아직 안 머지된 경우:
```
사용자: /merge-cleanup
Claude: → §2 state=OPEN
        → cleanup 안 함. "아직 open 입니다. 웹에서 머지한 뒤 /merge-cleanup <번호> 를 다시 실행하세요." 안내 후 종료 (폴링하지 않음)
```

## See Also

- `/open-pr` — PR/MR 생성 (이 플러그인). 생성만 담당하며 자동 체인·폴링 없음. 사용자가 웹에서 머지한 뒤 이 스킬을 **수동으로** 실행해 뒷정리
- `GITHUB_GUIDE.md` / `GITLAB_GUIDE.md` — 플랫폼별 호스트 명령 (이 스킬 디렉토리)
- `git worktree` 문서: https://git-scm.com/docs/git-worktree
