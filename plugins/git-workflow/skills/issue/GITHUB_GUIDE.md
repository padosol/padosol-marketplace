# issue · GITHUB_GUIDE

`GF_HOST=github` 일 때 issue SKILL.md 가 따르는 호스트별 명령. 인증된 `gh` CLI 기준. SKILL 본문의 `<가이드: 섹션명>` 은 아래 동명 섹션을 가리킨다.

## 이슈 템플릿 위치

아래 경로를 **위에서부터** 확인해 먼저 존재하는 마크다운 템플릿을 쓴다 (`$ROOT` = 발행처 repo 루트):

```bash
ROOT="$(git rev-parse --show-toplevel)"
TEMPLATE_PATH=""
for f in \
  "$ROOT/.github/ISSUE_TEMPLATE.md" \
  "$ROOT/.github/issue_template.md"; do
  [ -f "$f" ] && { TEMPLATE_PATH="$f"; break; }
done
[ -z "$TEMPLATE_PATH" ] && TEMPLATE_PATH="$(ls "$ROOT"/.github/ISSUE_TEMPLATE/*.md 2>/dev/null | head -1)"
ls "$ROOT"/.github/ISSUE_TEMPLATE/*.md 2>/dev/null    # 여러 개면 목록을 사용자에게 보여 주고 고르게 한다
[ -n "$TEMPLATE_PATH" ] && echo "template: $TEMPLATE_PATH" || echo "no template"
```

- `.github/ISSUE_TEMPLATE/*.yml` (이슈 폼)은 **템플릿으로 쓰지 않는다** — 웹 폼 정의라 CLI 로 본문을 채워 넣을 수 없다. `.yml` 만 있으면 프로젝트 템플릿이 없는 것으로 보고 내장 `template.md` 로 넘어간다.

## 내장 템플릿 조정

프로젝트 템플릿이 없어 `template.md` 를 쓸 때, GitHub 에는 네이티브 시간 추적이 없으므로 다음을 적용한다:

- **`## ⏱ 시간 추적` 섹션을 통째로 삭제**한다 (`/estimate`·`/spend` 는 GitLab 퀵액션이라 GitHub 에선 동작하지 않는 평문일 뿐이다).
- 나머지 섹션(유형 / 배경·목적 / 완료 조건 / 재현 절차)은 그대로 유지한다.

## 라벨 목록

```bash
gh label list --limit 100
```

- 발행처가 현재 repo 가 아니면 `-R <owner>/<repo>` 를 붙인다.
- 유형과 같은(또는 명백히 대응하는) 이름이 있으면 생성 시 `--label "<라벨>"` 로 붙이고, 없으면 라벨 없이 생성한다. **새 라벨을 만들지 않는다.**

## 이슈 생성

입력: `title`, `body_file`, (선택) `label`, (선택) `repo`. stdout 으로 이슈 URL 출력 → 끝 숫자가 이슈 번호.

```bash
gh issue create \
  --title "$title" \
  --body-file "$body_file"
# 출력: https://github.com/<owner>/<repo>/issues/<N>
```

- 유형 라벨이 있으면 `--label "<라벨>"` 추가.
- 발행처가 현재 repo 가 아니면 `-R <owner>/<repo>` 추가.
- 본문은 항상 `--body-file` 로만 전달한다.

## 번호 표기

이슈 번호는 `#<번호>` 로 표기한다 (예: `#43`). URL 형식은 `https://github.com/<owner>/<repo>/issues/<N>`. 셸 명령에는 `#` 없이 숫자만 넘긴다.
