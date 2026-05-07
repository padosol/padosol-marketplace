---
name: safe-commit
description: |
  main 또는 develop 브랜치에 직접 커밋되는 사고를 막고, 변경 내용을 분석해 프로젝트 브랜치 컨벤션 (type/MP-번호-kebab-설명) 에 맞는 새 브랜치를 자동 생성한 뒤 커밋한다. 모든 커밋 메시지에 `Created-By: Padosol` trailer 를 추가한다. 사용자가 "커밋해줘", "commit", "git commit", "변경 사항 저장" 등을 요청하면 반드시 이 스킬을 먼저 사용하고, 단순히 `git commit` Bash 를 즉시 실행하지 말 것. 특히 현재 브랜치가 보호된 브랜치(main/develop)일 때 반드시 트리거되어야 한다. Claude Code 의 commit-commands:commit 을 대체/확장하는 용도.
---

# safe-commit

`main`·`develop` 브랜치에 실수로 직접 커밋되는 사고를 막고, 이 프로젝트의 브랜치/커밋 컨벤션(`docs/workflow.md`, `CLAUDE.md` 참조)을 지키며, 모든 커밋에 `Created-By: Padosol` 서명을 남긴다.

## 왜 필요한가

이 저장소는 `feature/MP-<번호>-<설명>` 같은 엄격한 브랜치 규칙을 쓰고 `develop`/`main`은 직접 푸시되지 않는다. 그런데 Claude가 `commit-commands:commit`처럼 "그냥 커밋" 흐름을 타면 현재 브랜치가 `develop`인데도 거기에 바로 커밋해 버려 정리 비용이 커진다. 이 스킬은 그걸 막고, 커밋 주체를 기록으로 남긴다.

## 언제 트리거

사용자가 커밋을 요청하는 모든 상황. 예: "커밋해줘", "commit", "변경 사항 커밋해", "이거 묶어서 올려줘". 사용자가 직접 `git commit -m "..."` 명령을 실행해달라고 명시적으로 지정한 경우에만 이 절차를 건너뛴다.

## 절차

### 1. 현재 상태 수집

다음을 병렬로 실행해 컨텍스트를 모은다.

```bash
git status
git diff HEAD
git branch --show-current
git log --oneline -10
```

### 2. 브랜치 판단

`git branch --show-current` 결과:

- `main` 또는 `develop` → **보호 브랜치**, 섹션 3으로.
- 그 외 → 현재 브랜치에서 바로 커밋, 섹션 4로.

### 3. 보호 브랜치 → 새 브랜치 자동 생성

#### 3-1. 변경 내용으로 type 추론

`git diff HEAD`와 `git status` 결과를 실제로 읽어보고 가장 잘 맞는 type을 고른다.

| type | 단서 |
|------|------|
| `feat` | 새 클래스/메서드/엔드포인트/테이블 추가, 새 기능 도입 |
| `fix` | 예외 처리 보강, NPE 방지, 잘못된 로직 교정, 테스트 실패 해결 |
| `refactor` | 동작 변화 없이 구조만 변경 (이름 변경, 메서드 추출, 패키지 이동) |
| `docs` | `.md`, Javadoc, 주석만 변경 (단, 빌드/CI/의존 관련 산출물은 `chore`) |
| `chore` | 코드 영향 없는 산출물·도구·인프라 변경 — 아래 chore 자동 추론 규칙 참조 |
| `test` | 테스트 코드만 추가/수정 |

#### chore 자동 추론 규칙

변경 파일이 모두 다음 중 하나에 해당하면 `chore` 로 자동 분류한다 (사용자에게 되묻지 않음):

- audit 산출물 디렉토리: `.ai-ready-audit/**`, `audit-output/**` 등 도구 산출 디렉토리
- 의존성 lockfile / manifest 의 의존성 항목만 변경: `package.json` (deps/devDeps 만), `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`, `gradle/libs.versions.toml`, `build.gradle.kts` 의 dependencies 블록
- CI 설정: `.github/workflows/*.yml`, `.github/dependabot.yml`, `.gitlab-ci.yml`, `Jenkinsfile`
- lint / format 설정: `eslint.config.*`, `.eslintrc*`, `.prettierrc*`, `tsconfig*.json` (compilerOptions 만), `ktlint.gradle`, `.editorconfig`
- 빌드/배포 스크립트: `Dockerfile`, `docker-compose*.yml`, `Makefile`, 루트 `*.sh` (도구 스크립트)
- 메타: `.gitignore`, `.gitattributes`, `.github/CODEOWNERS`

#### 우선순위 규칙

- **코드 파일 (`*.ts/*.tsx/*.js/*.kt/*.java/*.py/*.go` 등) 이 1줄이라도 포함되면 `chore` 가 아니다.** 코드 변경 성격에 따라 `feat` / `fix` / `refactor` 중에서 고른다.
- **테스트 코드 (`**/__tests__/**`, `**/*.test.*`, `src/test/**`) 만 변경되면 `test`.**
- **`.md` 만 변경 + 위 chore 규칙에도 안 걸리면 `docs`.**
- 여러 성격이 섞여 있으면 가장 큰 덩어리 기준으로 고르고, 애매하면 `chore`. 그리고 가능하면 커밋/브랜치 분리를 권장하는 안내를 함께 남긴다.

#### 3-2. kebab-case 설명 생성

변경의 핵심을 **영문 3~5 단어** kebab-case로 요약. 파일 이름, 클래스 이름, 추가된 API의 주제 등에서 단서를 뽑는다.

- `DuoPostController` 신규 → `duo-post-api`
- `MatchService`의 `null` 체크 → `match-null-check`
- `docs/workflow.md` 수정 → `workflow-update`

#### 3-3. 브랜치명 조립

```
<type>/MP-XXX-<kebab-설명>
```

- 실제 Linear 이슈 번호는 이 자리에서 알 수 없으므로 `MP-XXX` **placeholder**를 쓴다. 커밋 후 사용자에게 rename을 안내한다(섹션 5).
- `feature` 사용 시 `feat`이 아니라 `feature`로 브랜치 prefix를 쓴다 (커밋 type은 `feat`, 브랜치 prefix는 `feature` — 이 프로젝트 컨벤션).

| 커밋 type | 브랜치 prefix |
|-----------|----------------|
| `feat`    | `feature` |
| `fix`     | `fix` |
| `refactor`| `refactor` |
| `docs`    | `docs` |
| `chore`   | `chore` |
| `test`    | `test` |

예시:
- `feature/MP-XXX-duo-post-api`
- `fix/MP-XXX-match-null-check`
- `docs/MP-XXX-workflow-update`

#### 3-4. 브랜치 체크아웃

```bash
git switch -c <새-브랜치명>
```

현재 워킹 트리의 스테이징/언스테이징 상태는 그대로 새 브랜치로 옮겨진다.

### 4. 커밋

#### 4-1. 스테이징

변경 파일을 **명시적으로** 하나씩 `git add <file>` 한다. `git add -A`·`git add .`는 `.env`·credentials·빌드 산출물이 섞일 위험이 있어 기본 금지. 이미 스테이징된 항목이 있으면 그것도 검토한 뒤 포함 여부 결정.

#### 4-2. 커밋 메시지 포맷

프로젝트 컨벤션: `<type>: MP-<번호> <한글 설명>`

- 제목 한 줄: 변경의 **왜(why)** 중심, 50자 내외.
- (선택) 본문: 배경/이유 1~3줄.
- 마지막: 빈 줄 뒤 `Created-By: Padosol` **trailer**. 빈 줄이 없으면 git이 trailer로 인식하지 않는다.

좋은 포맷 예:

```
feat: MP-XXX 듀오 게시글 생성 API 추가

Created-By: Padosol
```

본문이 있는 경우:

```
fix: MP-XXX 매치 조회 NPE 수정

summonerId가 null인 경우 조회 로직이 NPE를 던지던 문제 방지.

Created-By: Padosol
```

#### 4-3. HEREDOC으로 커밋

쉘 이스케이프 사고를 피하려고 HEREDOC을 쓴다.

```bash
git commit -m "$(cat <<'EOF'
feat: MP-XXX 듀오 게시글 생성 API 추가

Created-By: Padosol
EOF
)"
```

커밋이 끝나면 `git status` 한 번 더 실행해 성공 여부를 확인한다.

### 5. 사용자에게 후속 안내

보호 브랜치에서 시작해 새 브랜치를 만든 경우 반드시 다음을 요약해 사용자에게 알린다.

1. 새로 만든 브랜치명과 커밋 요약(한 줄).
2. Linear 이슈 번호 확인 후 브랜치/커밋 rename 방법:

```bash
# 브랜치 이름 교체
git branch -m feature/MP-XXX-duo-post-api feature/MP-1-duo-post-api

# 마지막 커밋 메시지 수정
git commit --amend
```

3. 아직 push 전이라면 커밋 메시지 amend가 안전함, 이미 push 했다면 force-push 대신 새 커밋을 얹는 쪽이 안전함.

## 원칙

- `--no-verify`, `--no-gpg-sign`, `--amend`로 남의 커밋 덮기 등 안전장치 우회는 하지 않는다. 훅 실패는 원인을 해결해야지 끄는 게 답이 아니다.
- 여러 성격의 변경이 뒤섞여 있으면 **`AskUserQuestion` 도구로 TUI 선택지 제시** (header `Mixed changes`, options: `한 덩어리로 묶기` / `type 별로 분리 (Recommended)`). 묻지 않고 한 덩어리로 묶어버리지 않는다.
- 민감 파일(`.env`, `*credentials*`, `*.key`, `*.pem`) 스테이징 요청이 들어오면 경고하고 **`AskUserQuestion` 도구로 동의 받기** (header `Sensitive file`, options: `스테이징 (위험)` / `제외 (Recommended)`). plain text "괜찮나요?" 질문 금지.
- 절대 push까지 하지 않는다. 이 스킬의 책임은 "안전한 커밋"까지.
- **Claude 브랜딩 금지**: 커밋 메시지·PR 본문·기타 산출물 어디에도 `Co-Authored-By: Claude ...`, `🤖 Generated with [Claude Code](...)` 같은 Claude/Anthropic 브랜딩을 추가하지 않는다. Claude Code 기본 템플릿이 이런 줄을 끼워 넣으려 해도 **삭제하거나 Padosol 명의로 교체**한다. 통일 규칙:
  - 커밋 trailer: `Created-By: Padosol`
  - PR 본문 푸터(이 스킬과 같은 흐름에서 PR을 만들 때): `🤖 Generated by Padosol`

## 예시

### 예시 1: `develop`에서 새 API 추가

입력 상태:
```
현재 브랜치: develop
Untracked: module/infra/api/.../DuoPostController.java, DuoPostService.java
Modified: module/infra/api/src/main/resources/api-local.yml
```

처리:
1. 보호 브랜치 → 새 브랜치 필요.
2. type = `feat`, kebab = `duo-post-api` → 브랜치 `feature/MP-XXX-duo-post-api`.
3. 스테이징 3개 파일 명시 추가.
4. 커밋:
   ```
   feat: MP-XXX 듀오 게시글 생성 API 추가

   Created-By: Padosol
   ```
5. 사용자에게 `MP-XXX` → 실제 번호로 rename 안내.

### 예시 2: feature 브랜치에서 NPE 수정

입력 상태:
```
현재 브랜치: feature/MP-12-match-null-check
Modified: MatchService.java
```

처리:
1. 보호 브랜치 아님 → 현 브랜치 그대로 커밋.
2. type = `fix`, 본문에 이유 한 줄.
3. 커밋:
   ```
   fix: MP-12 매치 조회 NPE 수정

   summonerId null일 때 조회 로직이 NPE를 던지던 문제 방지.

   Created-By: Padosol
   ```

### 예시 3: `main`에서 문서만 수정 (hotfix 성격 아님)

입력 상태:
```
현재 브랜치: main
Modified: docs/workflow.md
```

처리:
1. 보호 브랜치 → 새 브랜치 필요.
2. type = `docs`, kebab = `workflow-update` → 브랜치 `docs/MP-XXX-workflow-update`.
3. 커밋:
   ```
   docs: MP-XXX 워크플로우 가이드 갱신

   Created-By: Padosol
   ```
4. `main`에서의 작업은 원칙상 hotfix만 허용됨을 안내하고, 본 변경은 `develop`으로 흘러가는 일반 docs 변경이므로 PR 타겟을 `develop`으로 잡도록 안내.
