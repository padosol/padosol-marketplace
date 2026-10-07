# pr · GITLAB_GUIDE

`GF_HOST=gitlab` 일 때 pr SKILL.md 가 따르는 호스트별 명령. 모든 명령은 인증된 `glab` CLI 기준. SKILL 본문의 `<가이드: 섹션명>` 은 아래 동명 섹션을 가리킨다. 본문의 "PR" 은 GitLab 에선 MR, 번호는 iid.

## PR 템플릿 위치

`.gitlab/merge_request_templates/` 의 `Default.md` 우선, 없으면 첫 `.md` 파일을 템플릿으로 사용한다:

```bash
ROOT="$(git rev-parse --show-toplevel)"
TEMPLATE_PATH=""
if [ -f "$ROOT/.gitlab/merge_request_templates/Default.md" ]; then
  TEMPLATE_PATH="$ROOT/.gitlab/merge_request_templates/Default.md"
else
  TEMPLATE_PATH="$(ls "$ROOT"/.gitlab/merge_request_templates/*.md 2>/dev/null | head -1)"
fi
[ -n "$TEMPLATE_PATH" ] && echo "template: $TEMPLATE_PATH" || echo "no template"
```

여러 개라 어떤 템플릿인지 애매하면 목록을 사용자에게 보여 주고 고르게 한다.

## 내장 템플릿 조정

프로젝트 템플릿이 없어 `template.md` 를 쓸 때는 **조정 없이 모든 섹션을 그대로** 쓴다 (관련 이슈 / 요약 / 변경 유형 / 변경 내용 / 테스트·검증 / 머지 전에 필요한 것 / 크로스 리포 영향 / 체크리스트). GitLab 은 시간 추적을 지원하므로 `## 체크리스트` 의 작업 시간 기록 항목도 유지한다.

- `## 머지 전에 필요한 것` 은 **수동 조치가 실제로 있을 때만** 남긴다(시크릿 등록, 인프라 명령, 다른 MR 과의 머지 순서). 코드 머지로 끝나면 섹션째 삭제한다.

## 라벨 목록

프로젝트에 이미 존재하는 라벨 목록:

```bash
glab label list
```

- 크로스 리포면 `-R <group>/<repo>` 를 붙인다.
- 4단계 변경 유형과 같은(또는 명백히 대응하는) 이름이 목록에 있으면 생성 시 `-l "<라벨>"` 로 붙이고, 없으면 라벨 없이 생성한다. **새 라벨을 만들지 않는다.**

## PR/MR 생성

입력: `source`(소스 브랜치), `base`(타깃 브랜치), `title`, `body_file`. stdout 으로 MR URL 출력 → 끝 숫자가 MR iid.

```bash
glab mr create \
  --source-branch "$source" \
  --target-branch "$base" \
  --title "$title" \
  -d "$(cat "$body_file")" \
  --assignee @me \
  --yes
# 출력: https://gitlab.example.com/<group>/<repo>/-/merge_requests/<N>
```

- 유형 라벨이 있으면 `-l "<라벨>"` 추가. 초안이면 `--draft` 추가.
- `--fill`(자동 본문)·`--signoff` 는 쓰지 않는다. `--related-issue` 대신 본문의 `Closes #` 로 이슈를 연결한다.

## 시간 추적

**지원.** GitLab 퀵액션으로 이슈에 기록한다. 형식 단위는 `mo w d h m`(예: `1d 4h`, `2h`, `1h 30m`), 기본 환산 `1w=5d`, `1d=8h`.

```
/estimate <예상 시간>     # 계획값, 1회. 예: /estimate 2h
/spend <소비 시간>        # 실제 투입, 누적. 예: /spend 1h 30m (정정은 /spend -1h)
```

- 퀵액션은 **줄 맨 앞**에 와야 GitLab 이 인식한다(각각 한 줄).
- MR 이 아니라 **연결된 이슈**에만 기록한다 (시간 단일 출처 = 이슈). MR 에 적으면 합산되지 않는다.

## 연결 이슈에 시간 기록

`$IID` 는 연결 이슈 번호(`!`·`#` 없이 숫자만):

```bash
NOTE=$(mktemp)
# NOTE 에 두 줄 기록(각각 줄 맨 앞): /estimate <값> · /spend <값>
glab issue note "$IID" -m "$(cat "$NOTE")"
rm -f "$NOTE"
```

- 크로스 리포 이슈면 `-R <group>/<repo>` 를 붙인다.
- 셸 명령에는 숫자 iid 만 넘긴다 — `!`·백틱·미치환 `<...>` 토큰을 넣지 않는다.

## PR 코멘트

SKILL §7-2 에서 본문 밖으로 덜어낸 상세 근거를 MR 첫 코멘트로 게시한다. `$IID` 는 생성 명령이 출력한 MR iid(`!` 없이 숫자만):

```bash
NOTE=$(mktemp)
# NOTE 에 <details> 로 접은 상세 근거를 기록
glab mr note "$IID" -m "$(cat "$NOTE")"
rm -f "$NOTE"
```

- 크로스 리포면 `-R <group>/<repo>` 를 붙인다.
- 이 코멘트에는 **퀵액션(`/estimate`·`/spend`)을 넣지 않는다** — 시간은 연결 이슈에만 기록한다.
- 본문과 마찬가지로 **트레일러를 넣지 않는다.**
- 셸 명령에는 숫자 iid 만 넘긴다 — `!`·백틱·미치환 `<...>` 토큰을 넣지 않는다.

## 번호 표기

MR 번호는 `!<번호>` 로 표기한다 (예: `!57`). 이슈는 `#<번호>`. URL 형식은 `https://<gitlab-host>/<group>/<repo>/-/merge_requests/<N>`.

셸 명령에는 항상 `!` 없는 숫자 iid 만 넘긴다.
