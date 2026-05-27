# post-review · GITHUB_GUIDE

`GF_HOST=github` 일 때 post-review SKILL.md 가 따르는 호스트별 명령. 인증된 `gh` CLI 기준. SKILL 본문의 `<가이드: 섹션명>` 은 아래 동명 섹션을 가리킨다.

변수: `PR_NUM`(PR 번호), `PREFIX`(마커 prefix, 예 `<!-- padosol-review:simplify -->`), `BODY_FILE`(코멘트 본문 파일), `CID`(코멘트 id).

대부분의 코멘트 API 는 `owner/repo` 가 필요하므로 먼저 한 번 구한다:

```bash
repo="$(gh repo view --json owner,name --jq '"\(.owner.login)/\(.name)"')"
```

## 현재 브랜치의 열린 PR 번호

```bash
gh pr view --json number --jq '.number' 2>/dev/null || true
```

## PR 상태 조회

`OPEN`/`MERGED`/`CLOSED`:

```bash
gh pr view "$PR_NUM" --json state --jq '.state'
```

## 마커로 기존 코멘트 찾기

`PREFIX` 로 시작하는 코멘트의 id 1건 출력 (없으면 빈 문자열):

```bash
gh api "repos/${repo}/issues/${PR_NUM}/comments" \
  --jq "[.[] | select(.body | startswith(\"${PREFIX}\"))][0].id // empty"
```

## 코멘트 생성

본문 파일을 그대로 게시하고 새 코멘트 id 출력:

```bash
gh api -X POST "repos/${repo}/issues/${PR_NUM}/comments" \
  -F "body=@${BODY_FILE}" --jq '.id'
```

## 코멘트 갱신

`CID` 코멘트 본문을 파일 내용으로 교체:

```bash
gh api -X PATCH "repos/${repo}/issues/comments/${CID}" \
  -F "body=@${BODY_FILE}"
```

## 코멘트 앵커 형식

URL 뒤에 붙이는 fragment:

```
#issuecomment-<id>
```
