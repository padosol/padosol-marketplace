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

## 내장 fallback 템플릿

프로젝트 MR 템플릿을 못 찾았을 때 쓰는 이 스킬 디렉토리의 내장 골격. GitLab 은 **상황별 분기 없이 단일 MR 템플릿 고정**이다 — 변경 성격은 템플릿 안의 `## 변경 유형` 체크박스(feat/fix/refactor/chore/ci/docs/test)에서 **택1** 로 표현한다.

| 상황 | 파일 |
| --- | --- |
| 전부 | `templates/mr.md` |

채우기 규칙:

- 체크박스는 스킬이 판단한 유형 **하나만** `- [x]` 로 바꾸고 나머지는 `- [ ]` 로 남긴다. 두 유형 이상이 해당하면 체크를 늘리지 말고 사용자에게 MR 분리를 권한다.
- 유형 판단 근거: 브랜치 prefix (`feature|feat`→feat, `fix|hotfix|bugfix`→fix, `refactor`→refactor, 나머지 prefix 는 동명 유형) → 미매칭 시 `$BASE..HEAD` 커밋의 conventional type 최빈값. 둘 다 불명확하면 `AskUserQuestion` 으로 확인.
- `## 관련 이슈` 가 이슈 슬롯이다 — `ISSUE_KEY` 가 있으면 `Closes <이슈키>` 를 여기에만 넣고 본문 마지막에 중복 append 하지 않는다. 키가 없으면 (placeholder 금지) 이 섹션을 안내 주석째로 삭제.
- `## 체크리스트` 항목은 스킬이 실제로 확인한 것만 `- [x]`, 확인 못 한 항목은 `- [ ]` 로 남겨 사용자가 판단하게 한다. 항목 자체를 지우거나 추가하지 않는다.

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

모든 항목이 곧장 fail 이면 사용자에게 알림, pending/queued/pass 면 진행.
