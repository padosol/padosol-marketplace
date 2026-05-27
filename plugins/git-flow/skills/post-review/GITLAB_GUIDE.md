# post-review · GITLAB_GUIDE

`GF_HOST=gitlab` 일 때 post-review SKILL.md 가 따르는 호스트별 명령. 인증된 `glab` CLI 기준. SKILL 본문의 `<가이드: 섹션명>` 은 아래 동명 섹션을 가리킨다. "PR/코멘트" 는 GitLab 에선 MR/note, 번호는 iid.

변수: `PR_NUM`(MR iid), `PREFIX`(마커 prefix, 예 `<!-- padosol-review:simplify -->`), `BODY_FILE`(note 본문 파일), `CID`(note id).

## 현재 브랜치의 열린 PR 번호

```bash
glab mr view --output json 2>/dev/null | jq -r '.iid // empty'
```

## PR 상태 조회

GitHub 와 동일하게 `OPEN`/`MERGED`/`CLOSED` 로 정규화 (`opened` → `OPEN`):

```bash
glab mr view "$PR_NUM" --output json | jq -r '.state | ascii_upcase | sub("OPENED"; "OPEN")'
```

## 마커로 기존 코멘트 찾기

`PREFIX` 로 시작하는 note 의 id 1건 출력 (없으면 빈 문자열):

```bash
glab mr note list "$PR_NUM" --output json 2>/dev/null \
  | jq -r --arg p "$PREFIX" '[.[] | select(.body | startswith($p))][0].id // empty'
```

## 코멘트 생성

본문 파일을 그대로 게시하고 새 note id 출력 (출력 메시지에서 id 추출):

```bash
glab mr note "$PR_NUM" --message "$(cat "$BODY_FILE")" 2>&1 \
  | grep -Eo '#note_[0-9]+|/notes/[0-9]+' | grep -Eo '[0-9]+' | head -1
```

## 코멘트 갱신

`CID` note 본문을 파일 내용으로 교체. 프로젝트 id 가 필요:

```bash
proj="$(glab repo view --output json | jq -r '.id')"
glab api -X PUT "projects/${proj}/merge_requests/${PR_NUM}/notes/${CID}" \
  -f "body=$(cat "$BODY_FILE")"
```

## 코멘트 앵커 형식

URL 뒤에 붙이는 fragment:

```
#note_<id>
```
