# open-pr · GITLAB_GUIDE

`GF_HOST=gitlab` 일 때 open-pr SKILL.md 가 따르는 호스트별 명령. 모든 명령은 인증된 `glab` CLI 기준. SKILL 본문의 `<가이드: 섹션명>` 은 아래 동명 섹션을 가리킨다. 본문의 "PR" 은 GitLab 에선 MR.

## 현재 브랜치의 열린 PR 번호

현재 브랜치에 이미 열린 MR 이 있으면 그 iid 출력, 없으면 빈 문자열:

```bash
glab mr view --output json 2>/dev/null | jq -r '.iid // empty'
```

## PR 템플릿 위치

`.gitlab/merge_request_templates/` 의 `Default.md` 우선, 없으면 첫 `.md` 파일을 템플릿으로 사용 (`TEMPLATE_BODY`):

```bash
ROOT="$(git rev-parse --show-toplevel)"
TEMPLATE_PATH=""; TEMPLATE_BODY=""
if [ -f "$ROOT/.gitlab/merge_request_templates/Default.md" ]; then
  TEMPLATE_PATH="$ROOT/.gitlab/merge_request_templates/Default.md"
else
  TEMPLATE_PATH="$(ls "$ROOT"/.gitlab/merge_request_templates/*.md 2>/dev/null | head -1)"
fi
[ -n "$TEMPLATE_PATH" ] && TEMPLATE_BODY="$(cat "$TEMPLATE_PATH")"
[ -n "$TEMPLATE_BODY" ] && echo "template: $TEMPLATE_PATH" || echo "no template"
```

## PR/MR 생성

입력: `base`(타깃 브랜치), `title`, `body_file`. stdout 으로 MR URL 출력 → 끝 숫자가 MR iid.

```bash
glab mr create \
  --target-branch "$base" \
  --title "$title" \
  --description "$(cat "$body_file")" \
  --yes
# 출력: https://gitlab.com/<group>/<proj>/-/merge_requests/<N>
```

## CI 상태 1회 확인

```bash
glab ci status --branch "$(git branch --show-current)"
```

모든 항목이 곧장 fail 이면 await-merge chain 보류, pending/queued/pass 면 진행.
