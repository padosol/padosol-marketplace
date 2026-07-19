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
