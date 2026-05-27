# await-merge · GITLAB_GUIDE

`GF_HOST=gitlab` 일 때 await-merge SKILL.md 가 따르는 호스트별 명령. 인증된 `glab` CLI 기준. SKILL 본문의 `<가이드: 섹션명>` 은 아래 동명 섹션을 가리킨다. "PR" 은 GitLab 에선 MR, 번호는 iid.

## 현재 브랜치의 열린 PR 번호

```bash
glab mr view --output json 2>/dev/null | jq -r '.iid // empty'
```

## PR 정보 조회

`$PR_NUM`(MR iid) 의 정보를 GitHub 와 **동일한 정규화 JSON** `{number, state, headRefName, baseRefName, mergedAt, url}` 으로 맞춰 반환. GitLab `opened` → `OPEN` 정규화, `.iid` → number, source/target branch 매핑:

```bash
glab mr view "$PR_NUM" --output json | jq '{
  number: .iid,
  state: (.state | ascii_upcase | sub("OPENED"; "OPEN")),
  headRefName: .source_branch,
  baseRefName: .target_branch,
  mergedAt: .merged_at,
  url: .web_url
}'
```

rate limit 에 걸리면 stderr 에 `rate limit`/`403`/`429` 가 섞여 나오므로, 폴링 루프에서 `2>&1` 로 캡처해 감지한다.

## 호스트 기본 브랜치

orch settings 에서 base 를 못 정했을 때의 fallback:

```bash
glab repo view --output json | jq -r '.default_branch'
```
