# await-merge · GITHUB_GUIDE

`GF_HOST=github` 일 때 await-merge SKILL.md 가 따르는 호스트별 명령. 인증된 `gh` CLI 기준. SKILL 본문의 `<가이드: 섹션명>` 은 아래 동명 섹션을 가리킨다.

## 현재 브랜치의 열린 PR 번호

```bash
gh pr view --json number --jq '.number' 2>/dev/null || true
```

## PR 정보 조회

`$PR_NUM` 의 정보를 **정규화된 JSON** `{number, state, headRefName, baseRefName, mergedAt, url}` 으로 반환. GitHub 의 state 는 이미 `OPEN`/`MERGED`/`CLOSED` 라 추가 변환 불필요:

```bash
gh pr view "$PR_NUM" --json number,state,headRefName,baseRefName,mergedAt,url
```

rate limit 에 걸리면 stderr 에 `rate limit`/`403`/`429` 가 섞여 나오므로, 폴링 루프에서 `2>&1` 로 캡처해 감지한다.

## 호스트 기본 브랜치

orch settings 에서 base 를 못 정했을 때의 fallback:

```bash
gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'
```
