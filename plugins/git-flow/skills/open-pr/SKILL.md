---
name: open-pr
description: 현재 브랜치 기준으로 PR/MR 을 GitHub 또는 GitLab 에 생성한다. 플랫폼은 .orch/settings.json 의 git_host 또는 gh/glab 인증 상태로 자동 결정 (GF_HOST 환경변수 override 가능) 후, 호스트별 명령은 이 스킬 디렉토리의 GITHUB_GUIDE.md / GITLAB_GUIDE.md 를 따른다. 브랜치명 / 커밋 메시지에서 Linear MP 키 자동 추출, 본문에 Closes 매직워드 포함 (GitLab 도 Closes 인식). 본문 템플릿은 프로젝트 PR/MR 템플릿 (`.github/PULL_REQUEST_TEMPLATE.md` / `.gitlab/merge_request_templates/`) 을 우선 활용하고, 없으면 변경 성격(기능 구현·리팩토링·버그픽스·그 외)을 브랜치 prefix → 커밋 type 으로 자동 판단(애매하면 확인)해 이 스킬 디렉토리 `templates/` 의 상황별 템플릿을 선택한다. **PR/MR 생성까지만 담당한다 — 자동 머지 폴링·체인 없음.** 머지 후 로컬 정리는 사용자가 웹에서 직접 머지한 뒤 `/merge-cleanup` 을 수동 실행한다. 사용자가 "PR 만들어줘", "MR 만들어줘", "open pr", "/open-pr", "PR 올려" 같은 의도를 보이면 트리거. 기본 base 브랜치는 `develop` (hotfix 패턴은 `main`). 보호 브랜치 직접 push 는 `safe-commit` 스킬이 막으므로 이 스킬은 push 가 끝난 feature 브랜치에서만 의미.
---

# open-pr

현재 feature 브랜치를 GitHub PR 또는 GitLab MR 로 올린다. **생성까지만 담당하며 자동 머지 폴링·체인은 없다** — 사용자가 웹에서 직접 머지한 뒤 뒷정리가 필요하면 `/merge-cleanup` 을 수동으로 실행한다.

## 언제 트리거

- `/open-pr`
- "PR 만들어줘" / "MR 만들어줘" / "PR 올려" / "PR 까지" / "open pr" / "open mr"
- safe-commit / 일반 커밋 직후 사용자가 PR 까지 가자고 표현

자동 트리거 금지: 단순 커밋 의도 (`/safe-commit`) 만으로는 PR 생성 안 함.

## 절차

### 0. 플랫폼 탐지 → 가이드 선택

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

탐지가 비-0 으로 종료하면 (둘 다 인증 / 둘 다 미인증 / 잘못된 값) stderr 메시지 그대로 안내하고 중단.

결정된 플랫폼에 따라 **이후 모든 호스트 명령(PR 조회·생성·CI 확인 등)은 이 스킬 디렉토리의 해당 가이드를 그대로 따른다**:
- `github` → `GITHUB_GUIDE.md`
- `gitlab` → `GITLAB_GUIDE.md`

먼저 해당 가이드를 Read 로 열어 둔다. 본문의 **`<가이드: 섹션명>`** 표기는 선택된 가이드의 동명 섹션 명령을 의미한다. **SKILL 본문에는 `if [ "$GF_HOST" = ... ]` 같은 플랫폼 분기를 두지 않는다 — 분기는 가이드 파일에만.**

이하 본문에서 **`PR`** 은 host 에 따라 PR (GitHub) / MR (GitLab) 을 의미.

### 1. 사전 검증

```bash
git status --porcelain        # uncommitted 있으면 사용자 안내 후 중단
git branch --show-current     # 보호 브랜치 (main/develop) 면 거부
git rev-parse --abbrev-ref @{u} 2>/dev/null  # upstream 없으면 push 필요
```

체크 항목:
- 보호 브랜치 (`main`, `develop`) → 거부 + safe-commit 으로 브랜치 만들도록 안내
- uncommitted 변경 → safe-commit 흐름 안내, 중단
- upstream 없음 또는 ahead → `git push -u origin <branch>` 먼저 실행
- 이미 같은 브랜치에 open PR 있으면 그 번호 재사용 (중복 생성 금지): `<가이드: 현재 브랜치의 열린 PR 번호>` 로 확인. 비어있지 않으면 그 PR/MR 번호를 보고하고 종료 (새로 만들지 않음).

### 2. PR 메타데이터 조립

#### MP 키 추출 (우선순위)

1. 현재 브랜치명 정규식: `^(feature|fix|refactor|chore|docs|hotfix)/MP-(\d+)-` → 번호 추출
2. 실패 시 최근 커밋 메시지: `git log -1 --format=%s | grep -oE 'MP-[0-9]+'`
3. 그래도 없으면 사용자에게 묻고 받음 (placeholder `MP-XXX` 금지 — 머지 후 Linear 자동 전이가 깨짐)

#### PR 제목

`[MP-<번호>] <type>: <한글 요약>`
- type 은 브랜치 prefix 와 동일 (`feature` → `feat`, `hotfix` → `fix` 등 매핑)
- 한글 요약은 머지 대상 커밋들의 첫 줄 분석으로 도출. 단일 커밋이면 그 메시지 본문 차용. 다중이면 가장 큰 변경 덩어리 기준.

#### Base 브랜치

- 기본: `develop`
- 브랜치 prefix `hotfix/` → `main`
- 사용자 명시 (`/open-pr --base main`) → 그것 우선

#### PR 본문 — 템플릿 우선 + 결정적 골격 + 푸터 분리

본문은 아래 순서로 조립하고, 푸터는 변수 조립 후 **별도 단계로 강제 append** 한다. 본문을 자유 형식으로 즉석 작성하면 컨텍스트 누적 시 Claude 기본 푸터로 회귀해 PR 컨벤션이 깨진다. 본문 생성 파이프라인은 "**프로젝트 템플릿 탐지 → (프로젝트 템플릿 채우기 | 상황 판단 → 내장 상황별 템플릿 채우기) → footer append → 검증 (다음 단계)**" 결정적 4단계.

##### 1) 프로젝트 템플릿 탐지

프로젝트에 PR/MR 템플릿이 있으면 **반드시 그 템플릿을 본문 토대로 사용**한다. 템플릿이 있는데 내장 골격으로 대체하는 것 금지.

`<가이드: PR 템플릿 위치>` 섹션의 경로 우선순위대로 템플릿 파일을 찾아 `TEMPLATE_BODY` 로 로드한다. (GitHub 디렉토리형 멀티 템플릿이 여러 개면 자동 선택하지 말고 목록을 사용자에게 보여 주고 고르게 한 뒤 그 파일을 로드.) 못 찾으면 아래 3) 상황 판단 → 내장 상황별 템플릿.

##### 2) 프로젝트 템플릿이 있을 때 — 템플릿 채우기

`TEMPLATE_BODY` 를 본문 토대로 삼아 슬롯만 채운다:
- 템플릿의 **섹션 헤더 / 순서 / 체크리스트 항목을 보존**한다. 임의로 섹션을 추가·삭제하지 않는다.
- placeholder, 빈 bullet, 안내용 HTML 주석(`<!-- ... -->`) 자리에 이 PR 의 분석 내용을 채운다. 안내용 주석은 채운 뒤 제거.
- 템플릿에 이슈/티켓 링크 슬롯이 있으면 거기에 `Closes MP-<번호>` 를 넣고, 없으면 본문 마지막(푸터 직전 줄)에 `Closes MP-<번호>` 를 append.
- 채울 근거가 없는 섹션은 비워 두지 말고 `N/A` 또는 한 줄 사유를 적는다 (빈 헤더 방지).

##### 3) 프로젝트 템플릿이 없을 때 — 상황 판단 → 내장 상황별 템플릿

프로젝트 템플릿을 못 찾았을 때, 변경 성격(**상황**)을 판단해 이 스킬 디렉토리 `templates/` 중 하나를 `TEMPLATE_BODY` 로 로드한 뒤 **2) 와 동일한 채우기 로직**으로 슬롯만 채운다 (섹션 헤더·순서 보존, 안내 주석 `<!-- -->`·빈 bullet 자리 채운 뒤 주석 제거, 근거 없는 섹션은 `N/A` 또는 생략).

상황 4종 ↔ 템플릿 파일:

| 상황 | 파일 | 대상 |
| --- | --- | --- |
| 기능 구현 | `templates/feature.md` | 새 기능·엔드포인트·화면 추가 |
| 리팩토링 | `templates/refactor.md` | 동작 불변, 구조/가독성/중복 개선 |
| 버그픽스 | `templates/bugfix.md` | 결함 수정 (hotfix 포함) |
| 그 외 | `templates/general.md` | chore·docs·config·build·test·style·perf 등 |

**상황 판단 (하이브리드 — 자동 우선, 애매하면 확인)**, 순서대로:

1. **브랜치 prefix** (`git branch --show-current` 의 `<type>/...`):
   - `feature/`, `feat/` → 기능 구현
   - `refactor/` → 리팩토링
   - `fix/`, `hotfix/`, `bugfix/` → 버그픽스
   - `chore/`, `docs/`, `style/`, `test/`, `build/`, `ci/`, `perf/` → 그 외
2. prefix 미매칭 시 **커밋 type 집계** (base..HEAD 커밋들의 conventional type):
   ```bash
   git log "$BASE..HEAD" --format=%s \
     | grep -oiE '^(feat|fix|refactor|chore|docs|style|test|build|ci|perf)' \
     | tr 'A-Z' 'a-z' | sort | uniq -c | sort -rn
   ```
   최빈 type → 상황 매핑 (`feat`→기능, `refactor`→리팩토링, `fix`→버그픽스, 그 외 type→그 외). 단, 최빈 type 이 전체의 과반 미만이면 **혼재 = 신뢰도 낮음**.
3. **신뢰도 낮음** (prefix 미매칭 + 커밋 type 혼재/불명확/집계 불가) → `AskUserQuestion` 4지선다로 확인: 기능 구현 / 리팩토링 / 버그픽스 / 그 외. **자동 판단이 확실하면(1 매칭 또는 2 의 최빈 과반) 묻지 않는다.**

슬롯 채우기 공통 규칙 (내장 템플릿에도 적용):
- **Summary**: 정확히 1~3 bullet. 4개 이상이면 가장 큰 변경 1~3 으로 압축
- **Changes**: 각 bullet 은 `` `<path>` — <한 줄 설명> `` 형태. 변경 파일이 1개거나 docs/config 만 변경 시 섹션을 통째로 생략 (빈 헤더 금지)
- **Test plan / Behavior parity / Reproduction 등 체크리스트**: 단순 변경 1~2 항목, 복합 변경 (배포·DB 마이그레이션·다중 컴포넌트) 4~6 항목. 각 항목은 검증 주체가 명확해야 함 (예: `bash -n 통과`, `EC2 cutover 후 health check 200`)
- **Closes MP-`<번호>`**: 본문 마지막 줄, 푸터 (`🤖 Generated by Padosol`) 직전. 다른 위치 금지. GitHub 은 Closes 키워드로 Linear 자동 Done 전이, GitLab 은 MR description 의 Closes 키워드로 issue 자동 close — 양쪽 동일 어휘.

본문 변수 조립 직후 푸터 강제 append:

```bash
BODY="${BODY}

🤖 Generated by Padosol"
```

규칙:
- `Closes MP-<번호>` 매직워드 필수
- 푸터는 항상 마지막 1줄 (앞에 빈 줄 1개), 정확히 `🤖 Generated by Padosol`. 변형 금지
- **금지 문구** (다음 단계 검증으로 차단):
  - `Claude Code` / `claude.com/claude-code` / `claude.com/claude`
  - `Co-Authored-By: Claude` (어떤 모델 ID variant 도)
  - `Generated with [Claude` 등 Claude 동반 푸터

### 3. PR 본문 검증

생성 호출 직전, banned phrase 가 본문에 없는지 grep 으로 차단:

```bash
if printf '%s\n' "$BODY" | grep -qiE 'claude code|co-authored-by:[[:space:]]*claude|claude\.com/claude'; then
  echo "ERROR: PR 본문에 금지 문구 검출 — 본문 재작성 필요" >&2
  printf '%s\n' "$BODY" | grep -inE 'claude code|co-authored-by:[[:space:]]*claude|claude\.com/claude' >&2
  exit 1
fi
```

검증 실패 시 본문을 재생성한다 (골격 재실행). 검증 우회 금지.

### 4. PR/MR 생성

본문을 임시 파일로 저장한 뒤 `<가이드: PR/MR 생성>` 명령으로 생성한다 (입력: base 브랜치, 제목, 본문 파일):

```bash
TMP_BODY="$(mktemp)"
printf '%s\n' "$BODY" > "$TMP_BODY"
# → <가이드: PR/MR 생성> 실행 (base="$BASE", title="$TITLE", body_file="$TMP_BODY")
#   생성 명령이 stdout 으로 PR/MR URL 을 출력
rm -f "$TMP_BODY"
```

생성 명령이 출력한 URL 끝부분 숫자가 PR 번호 (양 플랫폼 공통 — GitHub `.../pull/<N>`, GitLab `.../merge_requests/<N>`):

```bash
PR_NUM="$(echo "$CREATE_URL" | grep -Eo '[0-9]+$')"
```

### 5. CI 확인 (선택, 짧게) + 종료

생성 직후 첫 CI 등록을 `<가이드: CI 상태 1회 확인>` 으로 1회 확인.

모든 항목이 곧장 fail 이면 사용자에게 알린다. 정상 (pending/queued/pass) 이면 그대로 진행. 장시간 CI 대기는 여기서 watch 하지 않는다 (이 스킬은 폴링하지 않음).

생성한 PR/MR 번호·URL 을 사용자에게 보고하고 **종료한다.** 자동으로 머지를 기다리거나 다른 스킬을 chain 호출하지 않는다. 사용자가 웹에서 머지한 뒤 로컬 뒷정리(worktree·브랜치 삭제, 타겟 최신화)가 필요하면 `/merge-cleanup <PR#>` 을 **수동으로** 실행하도록 안내만 한다.

## 실패 모드 / 주의

- ❌ 플랫폼 분기를 SKILL 본문에 인라인 (`if [ "$GF_HOST" = github ]`) — 분기가 흩어져 한쪽 host 만 동작
  ✅ §0 에서 1회 탐지 후 GITHUB_GUIDE.md / GITLAB_GUIDE.md 의 명령만 사용. SKILL 본문은 플랫폼-무관
- ❌ MP 키 placeholder (`MP-XXX`) 로 PR 생성 — Linear 매핑 깨짐, Closes 매직워드 무효화
  ✅ 키 못 찾으면 사용자에게 물어보고 받기. 받기 전 PR 생성 금지
- ❌ Claude 브랜딩 trailer (`Co-Authored-By: Claude`, `🤖 Generated with Claude Code`) — 프로젝트 컨벤션 위반
  ✅ trailer 는 `Created-By: Padosol` (커밋), 푸터 `🤖 Generated by Padosol` (PR 본문) 만
- ❌ 보호 브랜치에서 PR 시도 — 의미 없음
  ✅ 사전 검증에서 거부, safe-commit 안내
- ❌ 같은 브랜치에 PR 중복 생성 — host CLI 가 에러 내지만 idempotent 하게 기존 번호 재사용
  ✅ `<가이드: 현재 브랜치의 열린 PR 번호>` 먼저 확인
- ❌ Closes 매직워드를 커밋 메시지에 기재 — squash 시 소실
  ✅ PR/MR 본문에만 기재
- ❌ 프로젝트 PR/MR 템플릿이 있는데 내장 상황별 템플릿으로 덮어씀 — 팀 컨벤션 무시
  ✅ 프로젝트 템플릿 탐지되면 그 본문을 토대로 슬롯만 채움 (섹션 보존), 없을 때만 내장 상황별 템플릿
- ❌ 상황 판단이 확실한데도 매번 AskUserQuestion 으로 되물음 — 하이브리드 취지 훼손, 흐름 끊김
  ✅ 브랜치 prefix 매칭 또는 커밋 type 최빈 과반이면 자동 확정, 혼재/불명확일 때만 4지선다 확인
- ❌ 상황을 임의로 정해 엉뚱한 내장 템플릿 선택 (예: 버그픽스인데 feature.md) — 섹션이 변경 성격과 어긋남
  ✅ 브랜치 prefix → 커밋 type 순으로 근거 있게 판단, 근거 부족하면 사용자에게 확인
- ❌ PR 생성 후 자동으로 머지 폴링/체인 시작 — 사용자 모르게 세션 리소스 점유
  ✅ 이 스킬은 생성까지만. 머지 후 정리는 사용자가 `/merge-cleanup` 을 수동 실행 (자동 chain 없음)

## 사용 예

```
사용자: 변경사항 PR 까지 올려줘. 머지는 내가 함.
Claude: [/safe-commit] 으로 commit 끝남 → /open-pr 호출
        → §0 플랫폼 탐지 (GF_HOST=github) → GITHUB_GUIDE.md 채택
        → 검증 → MP 키 추출
        → 본문 생성: 프로젝트 템플릿 없음 → 브랜치 `refactor/MP-84-...` prefix 매칭
          → templates/refactor.md 로 슬롯 채움 (질문 없이 자동 확정)
        → <가이드: PR/MR 생성> 실행
        → PR #84 생성 보고 후 종료 ("머지 후 뒷정리는 /merge-cleanup 84 를 수동 실행" 안내)
        ... (사용자 GitHub 에서 머지) ...
        → (사용자가 원할 때) /merge-cleanup 84 수동 실행

상황 애매 예:

```
사용자: PR 올려줘
Claude: → 브랜치 `work/MP-90-misc` (prefix 미매칭)
        → 커밋 type 집계: feat 2, fix 2 (과반 없음 = 혼재)
        → AskUserQuestion 4지선다 제시 → 사용자 "기능 구현" 선택
        → templates/feature.md 로 슬롯 채움 → PR 생성
```

GitLab workspace 예:

```
사용자: MR 까지 올려줘
Claude: → §0 탐지 (GF_HOST=gitlab, settings.json git_host=gitlab) → GITLAB_GUIDE.md
        → <가이드: PR/MR 생성> (glab mr create --target-branch develop)
        → MR !12 생성 보고 후 종료 ("머지 후 /merge-cleanup 12 수동 실행" 안내)
```

## See Also

- `/merge-cleanup` — 사용자가 웹에서 머지한 뒤 **수동으로** 실행하는 뒷정리 스킬 (worktree·브랜치 삭제, 타겟 최신화). 이 스킬이 자동 chain 하지 않음 (이 플러그인)
- `safe-commit:safe-commit` — 커밋 단계의 sibling 스킬 (보호 브랜치 가드)
- `GITHUB_GUIDE.md` / `GITLAB_GUIDE.md` — 플랫폼별 호스트 명령 (이 스킬 디렉토리)
- `templates/feature.md` · `refactor.md` · `bugfix.md` · `general.md` — 프로젝트 템플릿이 없을 때 쓰는 내장 상황별 골격 (이 스킬 디렉토리)
- `.github/PULL_REQUEST_TEMPLATE.md` / `.gitlab/merge_request_templates/` — 프로젝트 본문 템플릿 (있으면 내장 골격보다 우선. 위치 우선순위는 각 가이드의 **PR 템플릿 위치** 섹션)
