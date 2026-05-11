#!/usr/bin/env bash
# github-flow / scripts/host.sh — gh / glab 추상화.
#
# 모든 SKILL bash 는 호출 전에 host 결정:
#   source "${CLAUDE_PLUGIN_ROOT}/scripts/host.sh"
#   gf_detect_host   # → GF_HOST / GF_CLI / GF_HOST_NAME / GF_PR_NOUN / GF_REPO_NOUN export
#
# 그 다음부터는 host-agnostic helper 만 호출:
#   gf_pr_create / gf_pr_info / gf_pr_current_open_num / gf_pr_url
#   gf_pr_comments_find / gf_pr_comment_create / gf_pr_comment_update
#   gf_default_branch
#
# 결정 우선순위:
#   1. 환경변수 GF_HOST 명시 (테스트/오버라이드용)
#   2. .orch/settings.json 의 git_host (cwd 부터 부모 traverse)
#   3. gh / glab auth status 자동 감지
#      - gh 만 인증 → github
#      - glab 만 인증 → gitlab
#      - 둘 다 → 사용자에게 GF_HOST 명시 요구 (에러)
#      - 둘 다 미인증 → 에러

set -uo pipefail

gf_detect_host() {
    if [ -n "${GF_HOST:-}" ]; then
        case "$GF_HOST" in
            github|gitlab) ;;
            *) echo "ERROR: GF_HOST='$GF_HOST' 잘못된 값 (github|gitlab)" >&2; return 2 ;;
        esac
    else
        local d="$PWD" orch_settings=""
        while [ "$d" != "/" ]; do
            if [ -f "$d/.orch/settings.json" ]; then
                orch_settings="$d/.orch/settings.json"; break
            fi
            d="$(dirname "$d")"
        done
        if [ -n "$orch_settings" ] && command -v jq >/dev/null 2>&1; then
            local v
            v="$(jq -r '.git_host // empty' "$orch_settings" 2>/dev/null)"
            case "$v" in github|gitlab) GF_HOST="$v" ;; esac
        fi
    fi
    if [ -z "${GF_HOST:-}" ]; then
        local gh_ok=0 glab_ok=0
        command -v gh   >/dev/null 2>&1 && gh   auth status >/dev/null 2>&1 && gh_ok=1
        command -v glab >/dev/null 2>&1 && glab auth status >/dev/null 2>&1 && glab_ok=1
        if   [ $gh_ok -eq 1 ] && [ $glab_ok -eq 0 ]; then GF_HOST=github
        elif [ $gh_ok -eq 0 ] && [ $glab_ok -eq 1 ]; then GF_HOST=gitlab
        elif [ $gh_ok -eq 1 ] && [ $glab_ok -eq 1 ]; then
            echo "ERROR: gh / glab 양쪽 인증 — GF_HOST=github|gitlab 환경변수로 명시하거나 .orch/settings.json 의 git_host 설정" >&2
            return 2
        else
            echo "ERROR: gh / glab 모두 미인증 — 하나에 'gh auth login' 또는 'glab auth login' 후 재시도" >&2
            return 2
        fi
    fi
    case "$GF_HOST" in
        github) GF_CLI=gh   GF_HOST_NAME=GitHub GF_PR_NOUN=PR GF_REPO_NOUN=repo    ;;
        gitlab) GF_CLI=glab GF_HOST_NAME=GitLab GF_PR_NOUN=MR GF_REPO_NOUN=project ;;
    esac
    export GF_HOST GF_CLI GF_HOST_NAME GF_PR_NOUN GF_REPO_NOUN
}

# PR/MR 생성 — stdout 으로 URL 출력.
# gf_pr_create <base> <title> <body_file>
gf_pr_create() {
    local base="$1" title="$2" body_file="$3"
    case "$GF_CLI" in
        gh)
            gh pr create --base "$base" --title "$title" --body-file "$body_file"
            ;;
        glab)
            glab mr create \
                --target-branch "$base" \
                --title "$title" \
                --description "$(cat "$body_file")" \
                --yes
            ;;
    esac
}

# PR/MR 정보 — 표준화된 JSON 으로 반환:
#   {number, state(OPEN|MERGED|CLOSED), headRefName, baseRefName, mergedAt, url}
# gf_pr_info <num>
gf_pr_info() {
    local num="$1"
    case "$GF_CLI" in
        gh)
            gh pr view "$num" --json number,state,headRefName,baseRefName,mergedAt,url
            ;;
        glab)
            glab mr view "$num" --output json | jq '{
                number: .iid,
                state: (.state | ascii_upcase | sub("OPENED"; "OPEN")),
                headRefName: .source_branch,
                baseRefName: .target_branch,
                mergedAt: .merged_at,
                url: .web_url
            }'
            ;;
    esac
}

# 현재 브랜치의 open PR/MR 번호 (없으면 빈).
gf_pr_current_open_num() {
    case "$GF_CLI" in
        gh)   gh pr view --json number --jq '.number' 2>/dev/null || true ;;
        glab) glab mr view --output json 2>/dev/null | jq -r '.iid // empty' ;;
    esac
}

# PR/MR URL
gf_pr_url() {
    local num="$1"
    case "$GF_CLI" in
        gh)   gh pr view "$num" --json url --jq '.url' ;;
        glab) glab mr view "$num" --output json | jq -r '.web_url' ;;
    esac
}

# 본문 prefix 로 코멘트/노트 검색 — id 1건 출력 (없으면 빈).
# gf_pr_comments_find <num> <body_prefix>
gf_pr_comments_find() {
    local num="$1" prefix="$2"
    case "$GF_CLI" in
        gh)
            local repo
            repo="$(gh repo view --json owner,name --jq '"\(.owner.login)/\(.name)"')" || return 1
            gh api "repos/${repo}/issues/${num}/comments" \
                --jq "[.[] | select(.body | startswith(\"${prefix}\"))][0].id // empty"
            ;;
        glab)
            glab mr note list "$num" --output json 2>/dev/null \
                | jq -r --arg p "$prefix" \
                    '[.[] | select(.body | startswith($p))][0].id // empty'
            ;;
    esac
}

# 새 코멘트/노트 생성 — id 출력.
# gf_pr_comment_create <num> <body_file>
gf_pr_comment_create() {
    local num="$1" body_file="$2"
    case "$GF_CLI" in
        gh)
            local repo
            repo="$(gh repo view --json owner,name --jq '"\(.owner.login)/\(.name)"')" || return 1
            gh api -X POST "repos/${repo}/issues/${num}/comments" \
                -F "body=@${body_file}" --jq '.id'
            ;;
        glab)
            glab mr note "$num" --message "$(cat "$body_file")" 2>&1 \
                | grep -Eo '#note_[0-9]+|/notes/[0-9]+' | grep -Eo '[0-9]+' | head -1
            ;;
    esac
}

# 코멘트/노트 갱신.
# gf_pr_comment_update <num> <comment_id> <body_file>
gf_pr_comment_update() {
    local num="$1" cid="$2" body_file="$3"
    case "$GF_CLI" in
        gh)
            local repo
            repo="$(gh repo view --json owner,name --jq '"\(.owner.login)/\(.name)"')" || return 1
            gh api -X PATCH "repos/${repo}/issues/comments/${cid}" \
                -F "body=@${body_file}"
            ;;
        glab)
            local proj body
            proj="$(glab repo view --output json | jq -r '.id')" || return 1
            body="$(cat "$body_file")"
            glab api -X PUT "projects/${proj}/merge_requests/${num}/notes/${cid}" \
                -f "body=${body}"
            ;;
    esac
}

# host 의 default 브랜치 (orch settings.json 매칭 실패 시 fallback).
gf_default_branch() {
    case "$GF_CLI" in
        gh)   gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name' ;;
        glab) glab repo view --output json | jq -r '.default_branch' ;;
    esac
}
