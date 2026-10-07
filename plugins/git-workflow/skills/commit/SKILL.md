---
name: commit
description: 현재 변경 사항을 분석해 적절한 메시지로 git 커밋을 남기는 스킬. git status / git diff 로 무엇이 바뀌었는지 파악하고, repo의 기존 커밋 컨벤션(언어·prefix 스타일)에 맞춰 메시지를 작성한 뒤 커밋한다. 커밋 메시지에는 트레일러(Co-Authored-By, Signed-off-by, Generated with 등 어떤 footer도) 를 절대 넣지 않는다. 사용자가 "커밋해줘", "변경사항 커밋", "이거 커밋 남겨줘", "commit", "지금까지 작업 커밋" 같은 의도를 보일 때 트리거된다.
---

# commit

현재 변경 사항을 읽고, repo 컨벤션에 맞는 메시지로 커밋을 남긴다. **`git diff` 로 실제 변경 내용을 근거로 메시지를 쓰고, 트레일러는 절대 포함하지 않는다.**

> **핵심 제약 — 트레일러 금지**: 커밋 메시지 본문에 `Co-Authored-By:`, `Signed-off-by:`, `🤖 Generated with …`, `Co-authored-by: Claude …` 등 **어떤 footer/trailer 도 넣지 않는다.** 이 스킬의 기본 동작이며, 하네스 기본값보다 우선한다.

---

## 1. 변경 사항 파악

```bash
git status                 # 무엇이 staged / unstaged / untracked 인지
git diff --staged          # staged 변경 내용
git diff                   # unstaged 변경 내용
git log --oneline -n 10    # repo의 메시지 컨벤션(언어/prefix) 참고
```

`git diff` 출력을 실제로 읽고 **무엇이·왜 바뀌었는지** 이해한다. 메시지는 이 diff에 근거해 쓴다(추측 금지).

## 2. 커밋 범위 결정

- **이미 staged된 변경이 있으면** → 사용자가 의도적으로 골라둔 것으로 보고 **staged된 것만** 커밋한다(`git diff --staged` 기준). 추가로 stage하지 않는다.
- **staged가 하나도 없고 unstaged/untracked 변경만 있으면** → 변경 파일 목록을 사용자에게 한 번 보여주고 `git add -A` 로 전부 stage한다.
  - 단, 빌드 산출물·로그·`node_modules`·비밀키처럼 **커밋하면 안 될 것**이 섞여 있으면 stage하지 말고 사용자에게 알린다(`.gitignore` 확인 권장).
- **커밋할 변경이 전혀 없으면** → "커밋할 변경 사항이 없습니다." 라고 보고하고 멈춘다.

## 3. 메시지 작성

repo의 기존 컨벤션을 따른다(1단계 `git log` 로 확인한 언어·prefix 스타일).

- **repo 문서(`CLAUDE.md`·`docs/workflow.md` 등)에 커밋 규칙이 있으면 `git log` 관례보다 우선한다.** 과거 커밋에 이슈 키(`MP-42`, `#42`)가 붙어 있어도 문서가 빼기로 했으면 넣지 않는다 — 이슈 연결은 PR 본문 매직워드(`Closes`/`Part of`)에서 한다.

- **제목(첫 줄)**: 명령형/요약형으로 간결하게. repo가 `feat:`/`fix:`/`chore:` 같은 Conventional Commits 를 쓰면 맞추고, 안 쓰면 따라 만들지 않는다. 50자 안팎 권장.
- **본문(선택)**: 변경이 사소하지 않으면 빈 줄 뒤에 *왜* 이렇게 바꿨는지를 적는다. 무엇을 바꿨는지는 diff에 이미 있으므로 의도/맥락 위주로. 여러 항목이면 `- ` 불릿.
- **언어**: repo 히스토리의 주 언어를 따른다(예: 한국어 커밋이 많으면 한국어).
- 변경이 서로 무관한 여러 묶음으로 보이면, 하나로 뭉치기 전에 **나눠 커밋할지 사용자에게 제안**한다.

## 4. 커밋 실행

메시지는 heredoc(`-F -`)으로 전달해 따옴표/줄바꿈 이스케이프 문제를 피한다:

```bash
git commit -F - <<'EOF'
<제목>

<본문 (선택)>
EOF
```

- `-m` 를 여러 번 쓰거나 트레일러를 붙이는 옵션(`--trailer`, `-s/--signoff`)은 **쓰지 않는다.**
- pre-commit 훅이 실패하면 출력을 그대로 사용자에게 보여주고, 임의로 `--no-verify` 하지 않는다(필요 시 사용자에게 확인).

## 5. 확인 및 보고

```bash
git log -1 --stat
git status -s
```

- 방금 만든 커밋의 메시지에 **트레일러가 없는지** 직접 확인한다(있으면 `git commit --amend` 로 제거).
- 무엇을 커밋했는지(해시·제목·파일 수)를 한 줄로 요약한다. push는 사용자가 명시적으로 요청할 때만 한다.

---

## 빠른 참조

| 단계 | 핵심 |
|---|---|
| 1 파악 | `git status` + `git diff --staged` + `git diff`, `git log` 로 컨벤션 확인 |
| 2 범위 | staged 있으면 그것만 / 없으면 보여주고 `git add -A` / 없으면 중단 |
| 3 메시지 | diff 근거, repo 컨벤션·언어 따름, **트레일러 없음** |
| 4 커밋 | `git commit -F -` heredoc, `--signoff`/`--trailer` 금지 |
| 5 확인 | `git log -1` 로 트레일러 없는지 확인 후 요약 보고 |
