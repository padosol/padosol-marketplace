# cleanup-merged · GITLAB_GUIDE

`GF_HOST=gitlab` 일 때 cleanup-merged SKILL.md 가 따르는 호스트별 명령. 인증된 `glab` CLI 기준. SKILL 본문의 `<가이드: 섹션명>` 은 아래 동명 섹션을 가리킨다. "PR" 은 GitLab 에선 MR, 번호는 iid.

## 현재 브랜치의 PR 번호

현재 브랜치(source branch)에 연결된 MR iid (opened/merged/closed 무관):

```bash
glab mr view --output json 2>/dev/null | jq -r '.iid // empty'
```

빈 결과면 현재 브랜치에 MR 이 없다는 뜻 → SKILL §1 에서 사용자에게 MR 번호를 묻는다.

## PR 정보 조회

`$PR_NUM`(MR iid) 의 정보를 GitHub 와 **동일한 정규화 JSON** `{number, state, headRefName, baseRefName, mergedAt, url}` 으로 맞춰 반환. GitLab `opened` → `OPEN`, `merged` → `MERGED`, `closed` → `CLOSED` 정규화, `.iid` → number, source/target branch 매핑:

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
