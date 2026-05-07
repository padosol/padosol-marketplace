---
name: lol-patch-crawler
description: |
  리그 오브 레전드 공식 패치노트 페이지를 크롤링해 챔피언/아이템/아레나 변경 내역을 구조화된 JSON 으로 변환한다. 패치 하이라이트 이미지를 시각 분석해 buff/nerf/adjust direction 정답값을 추출하고, 텍스트 휴리스틱으로 보충한다. Sonnet 서브에이전트에 위임해 메인 컨텍스트가 HTML 로 잠식되지 않도록 격리하며 결과를 `docs/patch/{버전}.json` 에 저장한다. 사용자가 "롤 패치", "LoL 패치노트", "리그 오브 레전드 패치", "패치노트 분석", "패치 데이터 추출", "/lol-patch-crawler" 같은 표현을 쓰거나 leagueoflegends.com 의 patch URL (예: /news/game-updates/patch-XX-X-notes/) 을 제공하면 트리거.
---

# LoL Patch Notes Crawler

리그 오브 레전드 공식 패치노트 페이지에서 HTML을 추출하고, Sonnet 서브에이전트가 분석하여 구조화된 JSON 데이터를 생성하는 스킬입니다.

## 워크플로우

기본 (HTML 파일을 만들지 않는 인메모리 모드):

```
URL → Sonnet 서브에이전트 ─[bash: patch_crawler.py URL --stdout]→ HTML(stdout) → JSON 생성 → docs/patch/{버전}.json
```

레거시 (HTML 파일을 같이 보존하고 싶을 때만):

```
URL → patch_crawler.py → docs/patch/{버전}.html → Sonnet 서브에이전트가 Read → JSON 저장
```

## 사용 시나리오

- 사용자가 LoL 패치노트 URL을 제공하고 크롤링을 요청할 때
- 저장된 HTML 파일을 JSON으로 변환하고 싶을 때
- 패치노트 변경사항을 프로그래밍에 활용하고 싶을 때

## 사용법

사용자가 패치노트 URL을 제공하면:

```
/lol-patch-crawler https://www.leagueoflegends.com/ko-kr/news/game-updates/patch-26-1-notes/
```

이 스킬을 실행하는 메인 Claude는 **HTML을 직접 읽지 않고**, Agent 도구로 `general-purpose` 서브에이전트(`model: "sonnet"`)를 띄워 작업을 위임합니다. 서브에이전트는 다음을 수행합니다:

1. `python "${CLAUDE_PLUGIN_ROOT}/skills/lol-patch-crawler/scripts/patch_crawler.py" <URL> --stdout` 을 Bash로 실행 → HTML이 자기 컨텍스트로 들어옴(파일 안 만듦)
2. stdout에 받은 HTML을 분석해 JSON 생성
3. `docs/patch/{버전}.json` 에 Write

이렇게 하면 HTML이 메인 컨텍스트를 잠식하지 않고, `docs/patch/*.html` 파일도 남지 않습니다.

### HTML 파일도 보존하고 싶을 때 (옵션)

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/lol-patch-crawler/scripts/patch_crawler.py" \
  "https://www.leagueoflegends.com/ko-kr/news/game-updates/patch-26-1-notes/"
# → docs/patch/26.1.html 생성
```

이후 서브에이전트에는 URL 대신 그 HTML 파일 경로를 넘기면 됩니다.

## 의존성

```bash
pip install requests beautifulsoup4
```

---

# Claude JSON 생성 가이드

HTML 파일이 제공되면 아래 지침에 따라 JSON을 생성합니다.

## JSON 출력 스키마

```json
{
  "version": "26.1",
  "url": "https://www.leagueoflegends.com/ko-kr/news/game-updates/league-of-legends-patch-26-1-notes/",
  "date": "2026-01-08",
  "rift": {
    "champions": [
      {
        "targetName": "챔피언명",
        "type": "champion",
        "direction": "buff",
        "changes": [
          { "statName": "속성명", "before": "이전값", "after": "새값" }
        ]
      }
    ],
    "items": [
      {
        "targetName": "아이템명",
        "type": "item",
        "direction": "nerf",
        "changes": [
          { "statName": "속성명", "before": "이전값", "after": "새값" }
        ]
      }
    ],
    "systems": []
  },
  "arena": {
    "champions": [
      {
        "targetName": "챔피언명",
        "type": "champion",
        "direction": "adjust",
        "changes": [...]
      }
    ],
    "items": [
      {
        "targetName": "아이템명",
        "type": "item",
        "direction": "buff",
        "changes": [...]
      }
    ],
    "systems": [
      {
        "targetName": "귀빈명",
        "type": "prismatic",
        "direction": "buff",
        "changes": [...]
      }
    ]
  }
}
```

## 파싱 지침

### 1. 버전, URL, 날짜 추출

- 파일명에서 버전 추출: `26.1.html` → `"version": "26.1"`
- **url**: HTML 상단 주석 `<!-- url: ... -->`에서 추출. 없으면 사용자가 제공한 URL 사용
- **date**: HTML 상단 주석 `<!-- datetime: ... -->`에서 날짜 부분(YYYY-MM-DD)만 추출

### 2. 섹션 식별

| HTML 섹션 | JSON 경로 |
|-----------|-----------|
| `#patch-champions` | `rift.champions` |
| `#patch-new-items`, `#patch-returning-items`, `#patch-updated-items` | `rift.items` |
| `#patch-arena` 또는 "아레나" 텍스트 포함 섹션 | `arena.*` |
| "추가 패치 노트" 섹션 | 내용에 따라 rift 또는 arena로 분류 |

### 3. 변경사항 추출 패턴

변경사항은 주로 다음 형식으로 나타납니다:

```
속성명: 이전값 ⇒ 새값
속성명: 이전값 → 새값
속성명: 이전값 => 새값
```

- 구분자: `⇒`, `→`, `=>` 중 하나
- `<strong>` 태그 내 텍스트가 `statName`
- 콜론(`:`) 이후 구분자 앞까지가 `before`
- 구분자 이후가 `after`

### 4. 대상(targetName) 식별

- **챔피언**: `h3.change-title` 내 텍스트
- **아이템**: `h4.change-detail-title` 내 텍스트 (이미지 아이콘과 함께)
- **아레나 증강/귀빈/모루**: `<strong>` 태그 내 텍스트

### 5. 아레나 분류 규칙

| 키워드/패턴 | 분류 |
|-------------|------|
| "챔피언 (아레나)" | `arena.champions` |
| "아이템 (아레나)" | `arena.items` |
| "귀빈 (아레나)" | `arena.systems` (targetType: "prismatic") |
| "증강 (아레나)" | `arena.systems` (targetType: "augment") |
| "능력치 모루 (아레나)" | `arena.systems` (targetType: "anvil") |

### 6. 추가 패치 노트 분류

"추가 패치 노트" 섹션의 내용:

- `(아레나)` 키워드 포함 → `arena` 하위로 분류
- 그 외 → `rift` 하위로 분류 (대부분 챔피언)

### 7. type 필드 구조

모든 변경사항 항목에는 `type` 필드 포함:

| 배열 위치 | type 값 |
|-----------|---------|
| `rift.champions` | `"champion"` |
| `rift.items` | `"item"` |
| `rift.systems` | `"system"` |
| `arena.champions` | `"champion"` |
| `arena.items` | `"item"` |
| `arena.systems` | `"prismatic"`, `"augment"`, `"anvil"` |

`arena.systems` 예시:

```json
{
  "targetName": "귀빈명",
  "type": "prismatic",
  "changes": [...]
}
```

- `prismatic`: 귀빈
- `augment`: 증강
- `anvil`: 능력치 모루

### 8. direction 필드 (상향/하향/조정)

각 대상의 전반적인 변경 방향을 나타냅니다:

| 값 | 의미 |
|---|---|
| `"buff"` | 상향 (강화) |
| `"nerf"` | 하향 (약화) |
| `"adjust"` | 조정 (혼합 또는 판단 불가) |

#### 8-1. 1순위: 라이엇 공식 하이라이트 이미지 (필수 우선 적용)

라이엇은 패치 노트 상단 "패치 하이라이트" 섹션에 챔피언/아이템을 한글 라벨(`상향`/`하향`/`조정`) 행으로 분류한 이미지를 게시한다. **이 이미지가 direction의 정답지**이며, 텍스트 추정은 이미지에 등장하지 않는 항목에만 사용한다.

이미지 위치 (HTML 구조):
- `<h2 id="patch-patch-highlights">패치 하이라이트</h2>` 가 두 번 등장 (목차/본문). **첫 번째** h2의 부모(`<header class="header-primary">`) 바로 다음 형제 `<div class="content-border">` 안의 `<img>`가 하이라이트 이미지(보통 1920×1080 PNG, 도메인 `cmsassets.rgpub.io`).
- 이미지 URL은 patch_crawler.py의 stdout HTML에 그대로 남아 있으므로 별도 fetch 없이 src를 추출 가능.

분석 절차 (서브에이전트가 수행):
1. HTML에서 위 위치의 `<img src=...>` URL을 추출.
2. `curl -sL -o /tmp/patch_highlights.png "<URL>"` 로 다운로드.
3. `Read` 툴로 `/tmp/patch_highlights.png` 를 읽어 시각 분석.
4. 한글 라벨 행 매핑:
   - `🠗 하향` 행에 있는 챔피언/아이템 → `direction: "nerf"`
   - `🠕 상향` 행에 있는 챔피언/아이템 → `direction: "buff"`
   - `🔄 조정` 행에 있는 챔피언/아이템 → `direction: "adjust"`
5. **레이아웃 주의**: 라벨이 행 **위**가 아니라 **아래**에 있는 패치도 있다. 라벨과 챔피언 아이콘의 수직 위치 관계를 반드시 확인하고, 의심되면 이미지 좌측 패널 전체를 한 번 더 잘라 라벨↔챔피언 매핑을 재확인할 것. (이전 사례: `흐웨이/유미`를 라벨-위 가정으로 잘못 매핑한 적 있음.)
6. 이미지로 매핑된 direction은 **확정값**이며 8-2/8-3의 텍스트 휴리스틱이 다른 값을 도출하더라도 덮어쓰지 않는다.

#### 8-2. 2순위: 텍스트 휴리스틱 (이미지에 없는 항목만)

이미지의 어느 행에도 등장하지 않은 항목(예: 작은 변경만 받은 챔피언, 아이템, 시스템)에만 적용:

- 전체적으로 버프면 → `"buff"` (일부 nerf가 섞여도 전반적 강화면 buff)
- 전체적으로 너프면 → `"nerf"` (일부 buff가 섞여도 전반적 약화면 nerf)
- 거의 반반이거나 방향 판단 불가 → `"adjust"`

**개별 change 판단 로직:**

"높을수록 좋은" 속성 (숫자 증가 = 버프):
- 체력, 마나, 공격력, 방어력, 피해량, 회복량, 계수, 사거리 등

"낮을수록 좋은" 속성 (숫자 감소 = 버프):
- 재사용 대기시간(쿨다운), 마나 소모량, 낙하 시간 등

판단 불가 (adjust):
- 텍스트 변경 ("마법" → "물리")
- 시스템 재설계 (계수 공식 변경)
- 상충 변경 (기본 피해량↓ + 계수↑)

예시:

```json
{
  "targetName": "유나라",
  "type": "champion",
  "direction": "buff",
  "changes": [
    { "statName": "기본 체력", "before": "575", "after": "590" },
    { "statName": "공격력", "before": "53", "after": "55" }
  ]
}
```

## 실행 절차

이 스킬이 트리거되면 메인 Claude는 **반드시** Agent 도구를 호출해 Sonnet 서브에이전트에 작업을 위임한다. HTML을 메인이 직접 Read/Bash 캡처하지 않는다.

```
Agent({
  description: "패치노트 URL→JSON 변환",
  subagent_type: "general-purpose",
  model: "sonnet",
  prompt: <아래 위임 프롬프트>
})
```

위임 프롬프트에 포함할 내용:
1. **입력**: 패치노트 URL (예: `https://www.leagueoflegends.com/ko-kr/news/game-updates/patch-26-1-notes/`)
   - 사용자가 URL 대신 HTML 파일 경로를 줬다면, 그 경로를 그대로 전달하고 서브에이전트는 Read로 읽음
2. **출력 경로**: `docs/patch/{버전}.json` (버전은 URL 또는 파일명에서 추출)
3. **선행 명령**: URL 모드인 경우, 서브에이전트가 가장 먼저 다음을 Bash로 실행해 정제된 HTML을 stdout으로 받도록 지시:
   ```
   python "${CLAUDE_PLUGIN_ROOT}/skills/lol-patch-crawler/scripts/patch_crawler.py" "<URL>" --stdout
   ```
   - 이 stdout이 곧 분석 대상 HTML이다. **임시 파일도 만들지 말 것** — Bash 결과 그대로 분석.
   - `${CLAUDE_PLUGIN_ROOT}`는 Claude Code가 plugin 활성화 시 자동으로 plugin 루트 경로로 치환한다. 서브에이전트 위임 프롬프트에 이 변수 표기를 그대로 포함시킬 것.
4. **하이라이트 이미지 다운로드 + 분석 (direction 정답지)**: HTML stdout에서 `<h2 id="patch-patch-highlights">` 첫 등장 부모(`<header class="header-primary">`) 바로 다음 `<div class="content-border">` 안의 `<img src>`를 추출. 다음 명령으로 다운로드:
   ```
   curl -sL -o /tmp/patch_highlights_{버전}.png "<image-src>"
   ```
   다운로드 후 `Read` 툴로 PNG를 읽고 한글 라벨(`상향`/`하향`/`조정`) 행별 챔피언/아이템을 식별한다. 라벨이 행 위인지 아래인지 반드시 시각적으로 확인 후 매핑할 것 (좌측 패널 전체를 한 번 다시 잘라 검증 권장). 매핑된 direction은 확정값.
5. 이 SKILL.md의 "JSON 출력 스키마" / "파싱 지침" 전체를 그대로 복붙 (서브에이전트는 이 스킬을 자동으로 보지 않음)
6. **direction 결정 순서**: 4단계 이미지 매핑 결과를 우선 적용 → 이미지에 없는 항목만 텍스트 휴리스틱(`8-2`)으로 보충
7. 분석 → Write로 JSON 저장
8. 완료 후 저장된 파일 경로와 한 줄 요약만 회신하도록 지시 (HTML 본문은 회신에 담지 말 것)

서브에이전트가 끝나면 메인 Claude는 회신받은 파일 경로를 사용자에게 보고한다.

## 검증

생성된 JSON 확인:

```bash
# JSON 파일 존재 확인
ls docs/patch/26.1.json

# 내용 확인 (선택)
cat docs/patch/26.1.json | head -50
```

## 주의사항

- `rift.systems`는 현재 빈 배열로 유지 (향후 확장 가능)
- 변경사항이 없는 섹션은 빈 배열로 설정
- 모든 텍스트는 공백 정리 (trim)
- HTML 엔티티는 적절히 디코딩
