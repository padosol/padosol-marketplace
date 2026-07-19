# merge-cleanup · GITHUB_GUIDE

`GF_HOST=github` 일 때 merge-cleanup SKILL.md 가 따르는 호스트별 명령. 인증된 `gh` CLI 기준. SKILL 본문의 `<가이드: 섹션명>` 은 아래 동명 섹션을 가리킨다.

## 현재 브랜치의 PR 번호

현재 브랜치에 연결된 PR 번호 (open/merged/closed 무관 — 이 스킬은 이미 머지된 PR 도 조회한다):

```bash
gh pr view --json number --jq '.number' 2>/dev/null || true
```

빈 결과면 현재 브랜치에 PR 이 없다는 뜻 (타겟/보호 브랜치 위이거나 미생성) → SKILL §1 에서 사용자에게 PR 번호를 묻는다.

## PR 정보 조회

`$PR_NUM` 의 정보를 **정규화된 JSON** `{number, state, headRefName, baseRefName, mergedAt, url}` 으로 반환. GitHub 의 state 는 이미 `OPEN`/`MERGED`/`CLOSED` 라 추가 변환 불필요:

```bash
gh pr view "$PR_NUM" --json number,state,headRefName,baseRefName,mergedAt,url
```
