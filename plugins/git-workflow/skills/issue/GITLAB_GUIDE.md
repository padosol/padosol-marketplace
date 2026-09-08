# issue · GITLAB_GUIDE

`GF_HOST=gitlab` 일 때 issue SKILL.md 가 따르는 호스트별 명령. 인증된 `glab` CLI 기준. SKILL 본문의 `<가이드: 섹션명>` 은 아래 동명 섹션을 가리킨다.

## 이슈 템플릿 위치

`.gitlab/issue_templates/` 의 `Default.md` 우선, 없으면 첫 `.md` 파일을 쓴다 (`$ROOT` = 발행처 repo 루트):

```bash
ROOT="$(git rev-parse --show-toplevel)"
TEMPLATE_PATH=""
if [ -f "$ROOT/.gitlab/issue_templates/Default.md" ]; then
  TEMPLATE_PATH="$ROOT/.gitlab/issue_templates/Default.md"
else
  TEMPLATE_PATH="$(ls "$ROOT"/.gitlab/issue_templates/*.md 2>/dev/null | head -1)"
fi
ls "$ROOT"/.gitlab/issue_templates/*.md 2>/dev/null    # 여러 개면 유형에 맞는 이름을 보고, 애매하면 사용자에게 묻는다
[ -n "$TEMPLATE_PATH" ] && echo "template: $TEMPLATE_PATH" || echo "no template"
```

## 내장 템플릿 조정

프로젝트 템플릿이 없어 `template.md` 를 쓸 때는 **조정 없이 모든 섹션을 그대로** 쓴다. GitLab 은 시간 추적을 지원하므로 `## ⏱ 시간 추적` 안내 섹션도 그대로 유지한다 (이슈 생성 시점에 `/estimate` 를 기록하지는 않는다 — 착수 시 규약).

## 라벨 목록

```bash
glab label list
```

- 발행처가 현재 repo 가 아니면 `-R <group>/<repo>` 를 붙인다.
- 유형과 같은(또는 명백히 대응하는) 이름이 있으면 생성 시 `-l "<라벨>"` 로 붙이고, 없으면 라벨 없이 생성한다. **새 라벨을 만들지 않는다.**

## 이슈 생성

입력: `title`, `body_file`, (선택) `label`, (선택) `repo`. stdout 으로 이슈 URL 출력 → 끝 숫자가 이슈 번호.

```bash
glab issue create \
  --title "$title" \
  -d "$(cat "$body_file")" \
  --yes
# 출력: https://<gitlab-host>/<group>/<repo>/-/issues/<N>
```

- 유형 라벨이 있으면 `-l "<라벨>"` 추가.
- 발행처가 현재 repo 가 아니면 `-R <group>/<repo>` 추가.
- 본문은 항상 `-d "$(cat "$body_file")"` 로만 전달한다.

## 번호 표기

이슈 번호는 `#<번호>` 로 표기한다 (예: `#43`). URL 형식은 `https://<gitlab-host>/<group>/<repo>/-/issues/<N>`. 셸 명령에는 `#` 없이 숫자만 넘긴다.
