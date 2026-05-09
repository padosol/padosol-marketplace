---
name: simplify-save
description: |
  Use when reviewing changed code for quality issues, performing code cleanup audits, or when the user invokes /simplify.
  Covers code reuse, quality patterns, and efficiency review with structured report saved to file.
  Args: [output-dir] - save directory (default: docs/simplify)
---

# Simplify: Code Review, Cleanup, and Report

Review all changed files for reuse, quality, and efficiency. Fix issues found, then save a structured report.

## Arguments

- First argument (optional): output directory for the report (default: `docs/simplify`)
- Example: `/simplify docs/reviews` saves to `docs/reviews/`

## Phase 1: Identify Changes

Run `git diff` (or `git diff HEAD` if there are staged changes) to see what changed. If there are no git changes, review the most recently modified files that the user mentioned or that you edited earlier in this conversation.

Save the diff output — you will pass it to the review agents and use it in the final report.

## Phase 2: Launch Three Review Agents in Parallel

Use the Agent tool to launch all three agents concurrently in a single message. Pass each agent the full diff so it has the complete context.

### Agent 1: Code Reuse Review

For each change:

1. **Search for existing utilities and helpers** that could replace newly written code. Look for similar patterns elsewhere in the codebase — common locations are utility directories, shared modules, and files adjacent to the changed ones.
2. **Flag any new function that duplicates existing functionality.** Suggest the existing function to use instead.
3. **Flag any inline logic that could use an existing utility** — hand-rolled string manipulation, manual path handling, custom environment checks, ad-hoc type guards, and similar patterns are common candidates.

### Agent 2: Code Quality Review

Review the same changes for hacky patterns:

1. **Redundant state**: state that duplicates existing state, cached values that could be derived, observers/effects that could be direct calls
2. **Parameter sprawl**: adding new parameters to a function instead of generalizing or restructuring existing ones
3. **Copy-paste with slight variation**: near-duplicate code blocks that should be unified with a shared abstraction
4. **Leaky abstractions**: exposing internal details that should be encapsulated, or breaking existing abstraction boundaries
5. **Stringly-typed code**: using raw strings where constants, enums (string unions), or branded types already exist in the codebase
6. **Unnecessary comments**: comments explaining WHAT the code does (well-named identifiers already do that), narrating the change, or referencing the task/caller — delete; keep only non-obvious WHY (hidden constraints, subtle invariants, workarounds)

### Agent 3: Efficiency Review

Review the same changes for efficiency:

1. **Unnecessary work**: redundant computations, repeated file reads, duplicate network/API calls, N+1 patterns
2. **Missed concurrency**: independent operations run sequentially when they could run in parallel
3. **Hot-path bloat**: new blocking work added to startup or per-request/per-render hot paths
4. **Recurring no-op updates**: state/store updates that fire unconditionally — add a change-detection guard
5. **Memory**: unbounded data structures, missing cleanup, event listener leaks
6. **Overly broad operations**: reading entire files when only a portion is needed, loading all items when filtering for one

## Phase 3: Fix Issues

Wait for all three agents to complete. Aggregate their findings and fix each issue directly. If a finding is a false positive or not worth addressing, note it and move on — do not argue with the finding, just skip it.

Track each finding in a structured list with: category (reuse/quality/efficiency), short item name, description (what/why), severity (Quality/Efficiency only — High/Medium/Low), action taken (Fixed / Skip with reason), and optional before/after diff snippet (3~10 lines) for fixed code changes.

## Phase 3.5: Verify Build

If any code was changed in Phase 3, run the project build command (e.g., `./gradlew build`, `npm test`) to confirm no regressions. Record the result for the report.

## Phase 4: Save Report

After fixes are applied and verified, save the review report as a markdown file.

### Output path

1. Parse the skill argument for a custom output directory. If none provided, use `docs/simplify/`.
2. Ensure the directory exists (create if needed via `mkdir -p`).
3. File name format: `YYYY-MM-DD-<brief-topic>.md` where topic is a 2-4 word kebab-case summary of what was reviewed.

### Report structure

Findings are rendered as scannable cards (no per-section tables). 모든 finding 은 단일 `## Findings` 섹션 아래 카테고리/심각도/상태가 H3 헤더에 인라인으로 노출되어, 표 cell wrap 없이 본문 (What / Why / Action) 이 자연스럽게 흐른다.

Use this template:

```markdown
# Simplify Review: <topic summary>

**Date:** <YYYY-MM-DD>
**Target:** <brief description of what changed>
**Issues:** <N> reuse · <M> quality · <K> efficiency · **Build:** <BUILD SUCCESSFUL / FAILED>

---

## Findings

### #1 · Reuse · <Item Name> · **Fixed**

- **What:** <one-line description of the duplication / missed utility>
- **Why:** <why it matters — maintenance cost, drift risk, etc.>
- **Action:** <concretely what was done — replaced X with util Y>

```diff
- old hand-rolled code
+ replaced with shared util
```

### #2 · Quality [H] · <Item Name> · **Skip**

- **What:** <one-line description>
- **Why:** <why it matters>
- **Action:** Skip — <specific reason, e.g., "out of scope for this change", "false positive: caller already validates">

### #3 · Efficiency [M] · <Item Name> · **Fixed**

- **What:** <one-line description>
- **Why:** <impact — hot path, N+1, memory>
- **Action:** <what was done>

---

## Summary

- `<file path>` — <what was changed>
- `<file path>` — <what was changed>
```

H3 헤더 규칙:
- `### #<N> · <Category>[ [<Severity>]] · <Item Name> · **<Status>**`
- Category: `Reuse` / `Quality` / `Efficiency` (필수)
- Severity 인라인 라벨 `[H]` / `[M]` / `[L]` — Quality / Efficiency 만 (Reuse 는 생략)
- Status: `**Fixed**` 또는 `**Skip**` (마지막에 항상 위치)

본문 규칙:
- 항상 3개 bullet: `**What:**` / `**Why:**` / `**Action:**` (순서 고정)
- Fixed 항목 중 코드 변경이 있는 경우 H3 카드 끝에 ` ```diff ` snippet 3~10 lines 첨부 (Before/After 명시). 설정/문서만 변경이면 생략 가능
- Skip 의 Action 은 `Skip — <구체적 이유>` 형태 (단순 "Skip" 금지)

### After saving

Confirm to the user: the report path, the number of findings (fixed vs skipped), and build status.

If the user wants the report to include precise per-model token usage and estimated cost for this session, chain `/track-tokens` (token-tracker plugin) and append its markdown output to the report file — it reads the transcript JSONL directly so the numbers are authoritative, not estimated.

If the work is happening on a feature branch with an open PR and the user wants the review visible on GitHub, suggest chaining `/post-review` (github-flow plugin) — it posts the saved report as a PR comment, idempotent on re-run.
