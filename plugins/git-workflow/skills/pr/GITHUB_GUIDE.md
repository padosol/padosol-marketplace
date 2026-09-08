# pr · GITHUB_GUIDE

`GF_HOST=github` 일 때 pr SKILL.md 가 따르는 호스트별 명령. 모든 명령은 인증된 `gh` CLI 기준. SKILL 본문의 `<가이드: 섹션명>` 은 아래 동명 섹션을 가리킨다. 본문의 "PR" 은 GitHub 에선 그대로 PR.

## PR 템플릿 위치

아래 경로를 **위에서부터** 확인해 먼저 존재하는 파일 1개를 템플릿으로 사용한다:

```bash
ROOT="$(git rev-parse --show-toplevel)"
TEMPLATE_PATH=""
for f in \
  "$ROOT/.github/PULL_REQUEST_TEMPLATE.md" \
  "$ROOT/.github/pull_request_template.md" \
  "$ROOT/PULL_REQUEST_TEMPLATE.md" \
  "$ROOT/docs/PULL_REQUEST_TEMPLATE.md"; do
  [ -f "$f" ] && { TEMPLATE_PATH="$f"; break; }
done
[ -n "$TEMPLATE_PATH" ] && echo "template: $TEMPLATE_PATH" || echo "no template"
```

디렉토리형 멀티 템플릿(`.github/PULL_REQUEST_TEMPLATE/*.md`)이 여러 개면 자동 선택 금지 — 목록을 사용자에게 보여 주고 고르게 한 뒤 그 파일을 쓴다:

```bash
ls "$ROOT"/.github/PULL_REQUEST_TEMPLATE/*.md 2>/dev/null
```

## 내장 템플릿 조정

프로젝트 템플릿이 없어 `template.md` 를 쓸 때, GitHub 에는 네이티브 시간 추적이 없으므로 다음을 적용한다:

- `## 체크리스트` 의 **작업 시간 기록 항목(`/spend` 언급 줄)을 삭제**한다. 체크할 수 없는 항목을 남기면 리뷰어에게 거짓 신호가 된다.
- 나머지 섹션(관련 이슈 / 요약 / 변경 유형 / 변경 내용 / 테스트·검증 / 머지 전에 필요한 것 / 크로스 리포 영향 / 체크리스트)은 그대로 유지한다.
- `## 머지 전에 필요한 것` 은 **수동 조치가 실제로 있을 때만** 남긴다(시크릿 등록, 인프라 명령, 다른 PR 과의 머지 순서). 코드 머지로 끝나면 섹션째 삭제한다.

## 라벨 목록

프로젝트에 이미 존재하는 라벨 목록:

```bash
gh label list --limit 100
```

- 크로스 리포면 `-R <owner>/<repo>` 를 붙인다.
- 4단계 변경 유형과 같은(또는 명백히 대응하는) 이름이 목록에 있으면 생성 시 `--label "<라벨>"` 로 붙이고, 없으면 라벨 없이 생성한다. **새 라벨을 만들지 않는다.**

## PR/MR 생성

입력: `source`(소스 브랜치), `base`(타깃 브랜치), `title`, `body_file`. stdout 으로 PR URL 출력 → 끝 숫자가 PR 번호.

```bash
gh pr create \
  --head "$source" \
  --base "$base" \
  --title "$title" \
  --body-file "$body_file" \
  --assignee @me
# 출력: https://github.com/<owner>/<repo>/pull/<N>
```

- 유형 라벨이 있으면 `--label "<라벨>"` 추가. 초안이면 `--draft` 추가.
- `--fill`(자동 본문)·`--signoff` 는 쓰지 않는다. 본문은 항상 `--body-file` 로만 전달한다.

## 시간 추적

**미지원.** GitHub 에는 estimate/spend 에 해당하는 네이티브 시간추적 기능이 없다.

- SKILL §5 의 estimate·spend 산출을 **하지 않는다**(세션 경과 시간 계산도 생략).
- SKILL §7 의 이슈 시간 기록도 **하지 않는다**.
- 결과 보고에는 `시간 기록: 해당 없음 (GitHub 미지원)` 으로 명시한다.
- 시간을 평문 코멘트(`Estimate: 2h` 등)로 이슈에 남기지 않는다 — 집계되지 않는 노이즈일 뿐이다.

## 연결 이슈에 시간 기록

**no-op.** 위 "시간 추적" 이 미지원이므로 실행할 명령이 없다. 이 단계를 건너뛰고 결과 보고에 그 사실만 남긴다.

## PR 코멘트

SKILL §7-2 에서 본문 밖으로 덜어낸 상세 근거를 PR 첫 코멘트로 게시한다. `$N` 은 생성 명령이 출력한 PR 번호(`#` 없이 숫자만):

```bash
NOTE=$(mktemp)
# NOTE 에 <details> 로 접은 상세 근거를 기록
gh pr comment "$N" --body-file "$NOTE"
rm -f "$NOTE"
```

- 크로스 리포면 `-R <owner>/<repo>` 를 붙인다.
- 본문과 마찬가지로 **트레일러를 넣지 않는다.**
- 셸 명령에는 숫자 번호만 넘긴다 — `#`·백틱·미치환 `<...>` 토큰을 넣지 않는다.

## 번호 표기

PR 번호는 `#<번호>` 로 표기한다 (예: `#57`). URL 형식은 `https://github.com/<owner>/<repo>/pull/<N>`.
