# open-pr · GITHUB_GUIDE

`GF_HOST=github` 일 때 open-pr SKILL.md 가 따르는 호스트별 명령. 모든 명령은 인증된 `gh` CLI 기준. SKILL 본문의 `<가이드: 섹션명>` 은 아래 동명 섹션을 가리킨다.

## 현재 브랜치의 열린 PR 번호

현재 브랜치에 이미 열린 PR 이 있으면 그 번호 출력, 없으면 빈 문자열:

```bash
gh pr view --json number --jq '.number' 2>/dev/null || true
```

## PR 템플릿 위치

아래 경로를 **위에서부터** 확인해 먼저 존재하는 파일 1개를 템플릿으로 사용 (`TEMPLATE_BODY`):

```bash
ROOT="$(git rev-parse --show-toplevel)"
TEMPLATE_PATH=""; TEMPLATE_BODY=""
for f in \
  "$ROOT/.github/PULL_REQUEST_TEMPLATE.md" \
  "$ROOT/.github/pull_request_template.md" \
  "$ROOT/PULL_REQUEST_TEMPLATE.md" \
  "$ROOT/docs/PULL_REQUEST_TEMPLATE.md"; do
  [ -f "$f" ] && { TEMPLATE_PATH="$f"; break; }
done
[ -n "$TEMPLATE_PATH" ] && TEMPLATE_BODY="$(cat "$TEMPLATE_PATH")"
[ -n "$TEMPLATE_BODY" ] && echo "template: $TEMPLATE_PATH" || echo "no template"
```

디렉토리형 멀티 템플릿(`.github/PULL_REQUEST_TEMPLATE/*.md`)이 여러 개면 자동 선택 금지 — 목록을 사용자에게 보여 주고 고르게 한 뒤 그 파일을 `TEMPLATE_BODY` 로 로드:

```bash
ls "$ROOT"/.github/PULL_REQUEST_TEMPLATE/*.md 2>/dev/null
```

## 내장 fallback 템플릿

프로젝트 PR 템플릿을 못 찾았을 때 쓰는 이 스킬 디렉토리의 내장 골격. GitHub 은 변경 성격(**상황**)을 판단해 4종 중 하나를 고른다.

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

이 4종에는 이슈 슬롯 섹션이 따로 없다 — `ISSUE_KEY` 가 있으면 템플릿 끝 안내 주석 자리에 `Closes <이슈키>` 한 줄(푸터 직전)을 남기고, 없으면 그 주석째로 삭제한다.

## PR/MR 생성

입력: `base`(타깃 브랜치), `title`, `body_file`. stdout 으로 PR URL 출력 → 끝 숫자가 PR 번호.

```bash
gh pr create --base "$base" --title "$title" --body-file "$body_file"
# 출력: https://github.com/<owner>/<repo>/pull/<N>
```

## CI 상태 1회 확인

```bash
gh pr checks "$PR_NUM"
```

모든 항목이 곧장 fail 이면 사용자에게 알림, pending/queued/pass 면 진행.
