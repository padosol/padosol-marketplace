# merge-done · GITLAB_GUIDE

`GF_HOST=gitlab` 일 때 merge-done SKILL.md 가 따르는 호스트별 명령. 인증된 `glab` CLI 기준. SKILL 본문의 `<가이드: 섹션명>` 은 아래 동명 섹션을 가리킨다. "PR" 은 GitLab 에선 MR, 번호는 iid.

## 브랜치로 PR 목록 조회

입력: `branch`. 그 브랜치를 source 로 하는 MR 을 상태 무관(opened/merged/closed)으로 조회해 GitHub 와 **동일한 정규화 JSON 배열**로 맞춘다 (`opened` → `OPEN`, `.iid` → `number`, source/target branch 매핑):

```bash
glab mr list --source-branch "$branch" --all --output json | jq '[.[] | {
  number: .iid,
  state: (.state | ascii_upcase | sub("OPENED"; "OPEN")),
  headRefName: .source_branch,
  baseRefName: .target_branch,
  mergedAt: .merged_at,
  url: .web_url
}]'
```

결과가 1건이면 그 `number`(iid), 0건·2건 이상이면 SKILL §2 대로 사용자에게 묻는다.

## PR 정보 조회

`$PR_NUM`(MR iid) 의 정보를 GitHub 와 **동일한 정규화 JSON** `{number, state, headRefName, baseRefName, mergedAt, mergeCommitSha, mergedBy, url}` 으로 맞춰 반환:

```bash
glab mr view "$PR_NUM" --output json | jq '{
  number: .iid,
  state: (.state | ascii_upcase | sub("OPENED"; "OPEN")),
  headRefName: .source_branch,
  baseRefName: .target_branch,
  mergedAt: .merged_at,
  mergeCommitSha: (.merge_commit_sha // .squash_commit_sha // null),
  mergedBy: (.merged_by.username // null),
  url: .web_url
}'
```

- squash 머지면 `merge_commit_sha` 가 비고 `squash_commit_sha` 에 값이 들어온다.
- 크로스 리포면 `-R <group>/<repo>` 를 붙인다.

## 번호 표기

MR 번호는 `!<번호>` 로 표기한다 (예: `!123`). 셸 명령에는 항상 `!` 없는 숫자 iid 만 넘긴다.
