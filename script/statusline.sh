#!/bin/bash

# 색상 설정
GREEN='\033[32m'
RED='\033[31m'
GRAY='\033[38;5;245m'
RESET='\033[0m'

input=$(cat)

# 1. JSON 데이터 추출
MODEL=$(echo "$input" | jq -r '.model.display_name')
PCT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
COST=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')
DURATION_MS=$(echo "$input" | jq -r '.cost.total_duration_ms // 0')
FIVE_H=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // 0')
WEEK=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // 0')
DIR=$(echo "$input" | jq -r '.workspace.current_dir')

# 2. 진행률 표시줄 생성
BAR_WIDTH=10
FILLED=$((PCT * BAR_WIDTH / 100))
EMPTY=$((BAR_WIDTH - FILLED))
BAR=""
[ "$FILLED" -gt 0 ] && printf -v FILL "%${FILLED}s" && BAR="${FILL// /▓}"
[ "$EMPTY" -gt 0 ] && printf -v PAD "%${EMPTY}s" && BAR="${BAR}${PAD// /░}"

# 3. 비용 및 시간 포맷팅
COST_FMT=$(printf '$%.2f' "$COST")
DURATION_SEC=$((DURATION_MS / 1000))
MINS=$((DURATION_SEC / 60))
SECS=$((DURATION_SEC % 60))

# --- [Git 캐시 로직 시작] ---
CACHE_FILE="/tmp/statusline-git-cache-$(echo -n "$DIR" | md5sum | cut -c1-8)"
CACHE_MAX_AGE=5 # 5초 유지

# 캐시가 상했는지(5초 지났는지) 확인하는 함수
cache_is_stale() {
    [ ! -f "$CACHE_FILE" ] && return 0
    local mtime
    mtime=$(stat -c %Y "$CACHE_FILE" 2>/dev/null) || return 0
    [ $(($(date +%s) - mtime)) -gt $CACHE_MAX_AGE ]
}

if cache_is_stale; then
    if git -C "$DIR" rev-parse --git-dir > /dev/null 2>&1; then
        B=$(git -C "$DIR" branch --show-current 2>/dev/null)
        # 소스 추가/삭제 라인 수 (HEAD 대비, staged+unstaged 합산. 미추적 새 파일은 미포함)
        NUMSTAT=$(git -C "$DIR" diff HEAD --numstat 2>/dev/null)
        A=$(echo "$NUMSTAT" | awk '{a+=$1} END{print a+0}')
        D=$(echo "$NUMSTAT" | awk '{d+=$2} END{print d+0}')
        # 프로젝트(repo)명 = main .git 의 부모 디렉터리명 (워크트리여도 항상 본체 repo 를 가리킴)
        COMMON=$(git -C "$DIR" rev-parse --git-common-dir 2>/dev/null)
        case "$COMMON" in /*) ;; *) COMMON="$DIR/$COMMON" ;; esac
        R=$(basename "$(dirname "$COMMON")")
        # 링크된 워크트리면 워크트리명, 아니면 빈값
        GD=$(git -C "$DIR" rev-parse --git-dir 2>/dev/null)
        case "$GD" in */worktrees/*) W=$(basename "$GD") ;; *) W="" ;; esac
        echo "$B|$A|$D|$R|$W" > "$CACHE_FILE"
    else
        echo "||||" > "$CACHE_FILE" # Git 아님을 캐싱
    fi
fi

# 캐시 파일에서 읽어오기
IFS='|' read -r BRANCH ADDED DELETED REPO WORKTREE < "$CACHE_FILE"
# --- [Git 캐시 로직 끝] ---

# 4. 출력 문자열 조립
output="[$MODEL] | $BAR $PCT% | 📦 ${REPO:-${DIR##*/}}"
[ -n "$WORKTREE" ] && output+=" | 🌳 $WORKTREE"

if [ -n "$BRANCH" ]; then
    GIT_STATUS=""
    [ "$ADDED" -gt 0 ] && GIT_STATUS="${GREEN}+${ADDED}${RESET}"
    [ "$DELETED" -gt 0 ] && GIT_STATUS="${GIT_STATUS}${GIT_STATUS:+ }${RED}-${DELETED}${RESET}"
    output+=" | 🌿 $BRANCH $GIT_STATUS"
fi

output+="\n 💰 $COST_FMT | ⏱️ ${MINS}m ${SECS}s | 5h: $(printf '%.0f' "$FIVE_H")% | 7d: $(printf '%.0f' "$WEEK")%"

echo -e "${output}"