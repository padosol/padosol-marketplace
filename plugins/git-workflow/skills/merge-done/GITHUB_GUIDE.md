# merge-done · GITHUB_GUIDE

`GF_HOST=github` 일 때 merge-done SKILL.md 가 따르는 호스트별 명령. 인증된 `gh` CLI 기준. SKILL 본문의 `<가이드: 섹션명>` 은 아래 동명 섹션을 가리킨다.

## 브랜치로 PR 목록 조회

입력: `branch`. 그 브랜치를 head 로 하는 PR 을 상태 무관(open/merged/closed)으로 **정규화 JSON 배열**로 반환한다:

```bash
gh pr list --head "$branch" --state all \
  --json number,state,headRefName,baseRefName,mergedAt,url
```

GitHub 의 `state` 는 이미 `OPEN`/`MERGED`/`CLOSED` 라 추가 변환이 필요 없다. 결과가 1건이면 그 `number`, 0건·2건 이상이면 SKILL §2 대로 사용자에게 묻는다.

## PR 정보 조회

`$PR_NUM` 의 정보를 **정규화 JSON** `{number, state, headRefName, baseRefName, mergedAt, mergeCommitSha, mergedBy, url}` 으로 반환:

```bash
gh pr view "$PR_NUM" \
  --json number,state,headRefName,baseRefName,mergedAt,mergeCommit,mergedBy,url \
  | jq '{
      number,
      state,
      headRefName,
      baseRefName,
      mergedAt,
      mergeCommitSha: (.mergeCommit.oid // null),
      mergedBy: (.mergedBy.login // null),
      url
    }'
```

- squash 머지면 `mergeCommit.oid` 가 squash 커밋 SHA 다.
- 크로스 리포면 `-R <owner>/<repo>` 를 붙인다.

## 번호 표기

PR 번호는 `#<번호>` 로 표기한다 (예: `#123`). 셸 명령에는 `#` 없이 숫자만 넘긴다.
