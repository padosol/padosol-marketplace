---
name: merge-done
description: PR(GitHub) / MR(GitLab) 머지가 완료된 뒤 뒷정리를 수행하는 스킬. 플랫폼을 한 번 자동 감지한 뒤 GITHUB_GUIDE.md / GITLAB_GUIDE.md 의 호스트별 명령을 따른다. PR 번호(또는 현재 브랜치)로 머지 완료 여부를 확인하고, 머지된 경우에만 로컬 타겟 브랜치(develop/main 등)를 원격 기준으로 최신화한 뒤 작업용 git worktree 와 작업 브랜치를 정리한다. 사용자가 "머지 완료", "PR 머지됐어 정리해줘", "MR 머지됐어 정리해줘", "머지 끝났으니 워크트리/브랜치 치워줘", "merge-done", "!123 머지됐어" 같은 의도를 보일 때 트리거된다. 아직 머지되지 않았거나(OPEN) 닫힌(CLOSED) PR/MR 이면 정리하지 않고 멈춘다.
---

# merge-done

PR/MR 머지가 끝난 뒤의 **뒷정리 자동화** 스킬이다. 흐름은 항상 아래 순서를 지킨다:

0. 플랫폼 탐지 → 1. 시작 위치 파악 → 2. PR 식별 → 3. 머지 완료 **확인** → 4. 로컬 타겟 브랜치 최신화 → 5. 워크트리 정리 → 6. 작업 브랜치 정리 → 7. 결과 보고

> **안전 원칙**: 3단계에서 `state == "MERGED"` 가 확인되기 전에는 **절대 브랜치/워크트리를 지우지 않는다.** 머지 안 된 브랜치를 지우면 작업이 유실된다.

> **출력 규칙 (중요)**: 사용자에게 보여줄 상태·결과 메시지는 **어시스턴트 채팅 텍스트로만** 출력한다 — `echo` 등으로 셸에서 실행하지 않는다. 셸 명령에는 `!`, 백틱, 미치환 `<...>` 플레이스홀더를 **절대** 넣지 않고 실제 값으로 바꾼 토큰만 넣는다(호스트 CLI 에는 숫자 번호 `"$PR_NUM"` 만). 이를 어기면 `!`·백틱·`<...>` 가 섞인 토큰이 셸에서 명령 치환·리다이렉션으로 해석돼 `syntax error near unexpected token` 으로 실패한다.

이하 본문에서 **`PR`** 은 host 에 따라 PR (GitHub) / MR (GitLab) 을 의미한다. 작업 브랜치는 보통 `.claude/worktrees/<name>` 아래 git worktree 로 체크아웃되어 있다.

---

## 0. 플랫폼 탐지 → 가이드 선택

먼저 어떤 git 플랫폼인지 **한 번** 결정한다 (결정 순서: `GF_HOST` 환경변수 > `.orch/settings.json` 의 `git_host` > `gh`/`glab` 인증 상태):

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

탐지가 비-0 으로 종료하면 stderr 메시지 그대로 안내하고 중단한다.

결정된 플랫폼에 따라 **이후 모든 호스트 명령(PR 조회 등)은 이 스킬 디렉토리의 해당 가이드를 그대로 따른다**:
- `github` → `GITHUB_GUIDE.md`
- `gitlab` → `GITLAB_GUIDE.md`

먼저 해당 가이드를 Read 로 열어 둔다. 본문의 **`<가이드: 섹션명>`** 표기는 선택된 가이드의 동명 섹션 명령을 의미한다. **SKILL 본문에는 `if [ "$GF_HOST" = ... ]` 같은 플랫폼 분기를 두지 않는다 — 분기는 가이드 파일에만.** 3~7단계의 git 작업은 플랫폼과 무관하다.

## 1. 시작 위치 파악

현재 어느 repo / 워크트리에 있는지 확인한다.

```bash
git rev-parse --show-toplevel        # 현재 작업트리 루트
git rev-parse --abbrev-ref HEAD      # 현재 브랜치
git worktree list                    # 메인 작업트리 + 연결된 워크트리 목록
```

`git worktree list` 의 **첫 줄**이 메인 작업트리다. 이후 `cd` 로 옮겨다닐 메인 경로로 기억해 둔다.

## 2. PR 식별

- **사용자가 번호를 줬으면** 그 번호를 쓴다. GitLab 은 MR 을 `!123` 으로 표기하지만 **앞의 `!`(또는 `#`)는 떼고 숫자만**(`123`) 쓴다.
- **번호가 없으면** 현재 브랜치로 추론한다 — `<가이드: 브랜치로 PR 목록 조회>` 를 현재 브랜치로 실행한다.

```bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
# → <가이드: 브랜치로 PR 목록 조회> 실행 (branch="$BRANCH")
```

- 결과가 1건이면 그 `number` 를 쓴다.
- 0건이거나 2건 이상이면 사용자에게 어떤 PR 인지 물어본다. **추측해서 진행하지 않는다.**

확정한 번호는 **숫자만** 셸 변수에 담아 이후 모든 호스트 명령에 쓴다:

```bash
PR_NUM=123    # ! · # 없이 숫자만
```

> **주의**: 호스트 CLI·git 명령에는 항상 숫자 번호(`"$PR_NUM"`)만 넘긴다. `!`·`#` 표기나 백틱·`<...>` 플레이스홀더는 셸 명령에 넣지 않는다(위 "출력 규칙" 참고).

## 3. 머지 완료 확인 (게이트)

`<가이드: PR 정보 조회>` 로 `$PR_NUM` 의 정보를 **정규화 JSON** 으로 받는다. 어느 호스트든 아래 필드가 같은 이름으로 채워진다:

| 필드 | 용도 |
|---|---|
| `state` | `MERGED` / `OPEN` / `CLOSED` (가이드가 정규화) |
| `baseRefName` | 머지된 대상 브랜치 (예: `develop`, `main`) — 4단계에서 최신화 |
| `headRefName` | 작업 브랜치 — 5·6단계에서 정리 대상 |
| `mergedAt`, `mergeCommitSha`, `mergedBy` | 사용자에게 보여줄 머지 정보 |

판정:

- `state == "MERGED"` → **4단계로 진행.** `mergedAt` / `mergeCommitSha` 를 사용자에게 한 줄로 보고.
- `state == "OPEN"` → **중단**하고, "PR/MR 이 아직 머지되지 않았습니다(OPEN). 정리를 진행하지 않습니다." 를 번호와 함께 채팅으로 보고한다.
- `state == "CLOSED"` → **중단**하고, "PR/MR 이 머지 없이 닫혔습니다(CLOSED). 작업이 유실될 수 있어 정리를 진행하지 않습니다. 강제로 정리하려면 명시적으로 요청해 주세요." 를 번호와 함께 채팅으로 보고한다.
- 그 외 → 상태를 그대로 보고하고 중단.

## 4. 로컬 타겟 브랜치 최신화 (pull)

`baseRefName`(예: `develop`)을 **메인 작업트리에서** 체크아웃하고 원격 기준으로 pull 한다(연결된 워크트리에서 타겟 브랜치를 체크아웃하면 충돌할 수 있다).

```bash
cd <메인 작업트리 경로>              # 1단계에서 확인한 경로
git switch <baseRefName>             # 이미 타겟이면 그대로
git pull --ff-only origin <baseRefName>   # fetch + fast-forward (머지 커밋까지 반영)
```

- `--ff-only` 로 pull 한다(로컬 타겟에 별도 커밋이 쌓여 fast-forward 불가하면 pull 이 실패). 이때 **강제로 진행하지 말고** 상황을 보고한 뒤 사용자 판단을 받는다. 보통 타겟 브랜치에 로컬 커밋을 직접 쌓지는 않으므로 드문 경우다.

이로써 작업이 끝나면 메인 작업트리는 origin 기준으로 최신화된 타겟 브랜치(머지 커밋 포함)에 올라가 있다.

## 5. 워크트리 정리

작업 브랜치(`headRefName`)가 별도 워크트리에 체크아웃돼 있으면 그 워크트리를 제거한다.

```bash
git worktree list --porcelain    # "branch refs/heads/<headRefName>" 인 항목의 worktree 경로를 찾는다
```

- 해당 워크트리가 **없으면**(작업 브랜치가 메인 작업트리에 그냥 체크아웃돼 있던 경우) 이 단계는 건너뛰고 6단계로 간다.
- **현재 cwd 가 그 워크트리 안이면** 이미 4단계에서 메인 작업트리로 `cd` 했으므로(자기가 선 워크트리는 제거 불가) 안전하다. 혹시 아직 안 옮겼다면 먼저 메인 경로로 이동한다.
- 제거:

```bash
git worktree remove <워크트리 경로>
```

- `git worktree remove` 가 **커밋되지 않은 변경 때문에 실패**하면 그냥 `--force` 하지 말고, "워크트리 `<경로>` 에 커밋되지 않은 변경이 있습니다. 그래도 제거할까요?" 라고 **사용자에게 확인**한 뒤 승인 시에만 `git worktree remove --force <경로>` 한다.

## 6. 작업 브랜치 정리

```bash
git branch -d <headRefName>
```

- 성공하면 다음 단계로.
- **`-d` 가 "not fully merged" 로 실패하면**: PR 은 3단계에서 `MERGED` 로 이미 확인됐지만, squash/rebase 머지라 git 로컬 그래프상으로는 미머지로 보이는 정상적인 경우다. 이때 **임의로 `-D` 하지 말고** 사용자에게 확인한다:

  > (채팅으로) "PR/MR 은 호스트에서 MERGED 로 확인됐지만, squash/rebase 머지라 로컬 git 에서는 해당 작업 브랜치가 미머지로 보입니다. git branch -D 로 강제 삭제할까요?"

  사용자가 승인하면 `git branch -D <headRefName>` 실행, 거절하면 브랜치는 남겨두고 그 사실을 보고한다.

원격 추적 참조도 정리한다(호스트가 머지 시 원격 소스 브랜치를 보통 자동 삭제하므로 stale 참조가 남는다):

```bash
git fetch --prune
```

## 7. 결과 보고

수행한 내용을 한 번에 요약한다. 번호는 `<가이드: 번호 표기>` 형식으로 적는다. 예:

```
MR !123 (feature/foo → develop) 머지 확인 완료 (mergedAt: 2026-06-01)
✓ develop 최신화 (origin/develop 로 fast-forward)
✓ 워크트리 제거: .claude/worktrees/foo
✓ 작업 브랜치 삭제: feature/foo
✓ 원격 추적 정리 (fetch --prune)
현재 위치: 메인 작업트리, 브랜치: develop
```

건너뛰거나 사용자 확인으로 남겨둔 항목이 있으면 그대로 명시한다(예: "작업 브랜치 feature/foo 는 사용자 요청으로 삭제하지 않음").

---

## 빠른 참조 — 단계별 게이트

| 단계 | 진행 조건 | 막히면 |
|---|---|---|
| 0 플랫폼 | `GF_HOST` > `.orch/settings.json` > 인증 상태로 1회 결정 | 둘 다 인증/미인증 → 안내 후 중단 |
| 2 PR 식별 | 번호 명시 또는 브랜치 조회 1건 | 0건·2건 이상 → 사용자에게 질문 |
| 3 머지 확인 | `state == "MERGED"` | OPEN/CLOSED → **중단**, 정리 안 함 |
| 4 타겟 pull | `pull --ff-only` 성공 | ff 불가 → 보고 후 사용자 판단 |
| 5 워크트리 제거 | 깨끗한 워크트리 | dirty → 사용자 확인 후 `--force` |
| 6 브랜치 삭제 | `-d` 성공 또는 사용자 승인 | not-fully-merged → 사용자에게 `-D` 확인 |

## See Also

- `GITHUB_GUIDE.md` / `GITLAB_GUIDE.md` — 플랫폼별 호스트 명령 (이 스킬 디렉토리)
- `git-workflow:pr` — PR/MR 을 만드는 앞 단계 스킬
