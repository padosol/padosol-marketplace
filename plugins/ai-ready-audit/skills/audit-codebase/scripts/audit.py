#!/usr/bin/env python3
"""
audit.py — 임의의 git 리포지토리에서 AI-Ready 신호(signal)를 추출.

목표: rubric에 매핑할 수 있는 mechanical signal을 JSON으로 출력.
점수 부여(judgment) 자체는 Claude가 SKILL.md 절차로 진행한다.

사용:
    python3 audit.py <repo_path> [--out signals.json]

표준 출력 또는 --out으로 JSON을 내보낸다. 의존성 없음 (Python 3.8+).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

# --- 디렉토리/파일 분류 -------------------------------------------------------

# 모듈 후보에서 제외할 디렉토리 (vendored / build / cache)
EXCLUDED_DIRS = {
    ".git", ".github", ".idea", ".vscode", ".claude", ".devcontainer",
    "node_modules", "vendor", "venv", ".venv", "__pycache__",
    "build", "dist", "out", "target", ".gradle", ".next", ".nuxt",
    "coverage", ".pytest_cache", ".mypy_cache", ".tox",
    ".terraform", "tmp", "temp", ".cache",
}

# 모듈로 보지 않는 top-level dir (코드 외)
NON_MODULE_DIRS = {
    "docs", "doc", "scripts", "tools", "examples", "example", "samples",
    "ci", "infra", "config", "tests", "test", "__tests__",
    "assets", "static", "public",
}

# 컨텍스트 파일 이름 패턴
CONTEXT_FILENAMES = [
    "CLAUDE.md", "AGENTS.md", "AI.md",
    "README.md", "README.rst", "README.txt",
    ".cursorrules", ".cursor/rules.md",
]

# 섹션 감지용 정규식 (heading + 흔한 한국어/영어 키워드)
SECTION_PATTERNS = {
    "has_quick_commands": re.compile(
        r"^#{1,6}\s*("
        r"quick\s*commands?|commands?\s*&?\s*scripts?|usage|how\s*to\s*run|"
        r"명령어|실행|사용법|빠른\s*시작|빌드\s*및\s*실행"
        r")\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    "has_key_files": re.compile(
        r"^#{1,6}\s*("
        r"key\s*files?|important\s*files?|files\s*to\s*know|core\s*files?|"
        r"핵심\s*파일|주요\s*파일|중요\s*파일|파일\s*구조"
        r")\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    "has_gotcha": re.compile(
        r"^#{1,6}\s*("
        r"gotchas?|pitfalls?|caveats?|warning|notes?|"
        r"non[\-\s]?obvious|hidden\s*rules?|"
        r"주의\s*사항?|함정|비\-?자명|숨은\s*규칙|함정"
        r")\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    "has_see_also": re.compile(
        r"^#{1,6}\s*("
        r"see\s*also|related|references?|cross[\-\s]?refs?|"
        r"참고|관련|연관|상호\s*참조"
        r")\b",
        re.IGNORECASE | re.MULTILINE,
    ),
}

# Tribal-knowledge Five Questions 매핑 (heading 또는 본문 키워드)
FIVE_Q_PATTERNS = {
    "q1_what_owned": re.compile(
        r"(owns?|configures?|responsib(le|ility)|역할|소유|책임|관리|담당)",
        re.IGNORECASE,
    ),
    "q2_modification_patterns": re.compile(
        r"(common\s*modifications?|how\s*to\s*(add|change|extend)|workflow|"
        r"수정\s*(패턴|방법)|추가\s*방법|확장\s*방법)",
        re.IGNORECASE,
    ),
    "q3_failure_patterns": re.compile(
        r"(failure\s*patterns?|gotchas?|pitfalls?|common\s*errors?|"
        r"실패\s*패턴|에러|문제|함정|주의)",
        re.IGNORECASE,
    ),
    "q4_dependencies": re.compile(
        r"(depends?\s*on|dependenc(y|ies)|cross[\-\s]?module|imports?|uses\s*services?|"
        r"의존(성)?|연관\s*모듈|호출\s*관계)",
        re.IGNORECASE,
    ),
    "q5_tribal_knowledge": re.compile(
        r"(historical|legacy\s*reason|deprecated\s*but\s*required|"
        r"non[\-\s]?obvious|hidden\s*rules?|gotcha|"
        r"이력|레거시|숨은|관습|관행|히스토리)",
        re.IGNORECASE,
    ),
}

ARCH_DOC_NAMES = re.compile(
    r"(architecture|arch|design|overview|system[\-_\s]design|"
    r"아키텍처|설계|구조)", re.IGNORECASE
)
DEP_DOC_NAMES = re.compile(
    r"(dependenc(y|ies)|module[\-_\s]map|imports?|"
    r"의존(성)?\s*(관계|맵|그래프))", re.IGNORECASE
)
DATAFLOW_DOC_NAMES = re.compile(
    r"(data[\-_\s]?flow|flow[\-_\s]?diagram|sequence|"
    r"데이터\s*흐름|시퀀스)", re.IGNORECASE
)
MERMAID_FENCE = re.compile(r"^```\s*mermaid\b", re.MULTILINE)

# CI 워크플로우 키워드
CI_HINTS = {
    "lint":      re.compile(r"\b(lint|eslint|prettier|ruff|flake8|black|spotless|ktlint|rubocop)\b", re.IGNORECASE),
    "test":      re.compile(r"\b(test|junit|jest|vitest|pytest|gradle\s*test|mvn\s*test|npm\s*test|pnpm\s*test|go\s*test|cargo\s*test)\b", re.IGNORECASE),
    "typecheck": re.compile(r"\b(typecheck|tsc|mypy|pyright|sorbet|flow\s*check)\b", re.IGNORECASE),
    "docs":      re.compile(r"\b(docs?|markdownlint|link[\-_\s]?check|broken[\-_\s]?link|vale|alex)\b", re.IGNORECASE),
    "freshness": re.compile(r"\b(stale|freshness|broken[\-_\s]?ref|dead[\-_\s]?link)\b", re.IGNORECASE),
}

# 워크스페이스/모노레포 매니페스트
WORKSPACE_MANIFESTS = [
    "pnpm-workspace.yaml", "lerna.json", "nx.json", "rush.json",
    "turbo.json", "settings.gradle", "settings.gradle.kts",
    "Cargo.toml",  # workspace
]


@dataclass
class ContextFile:
    path: str
    lines: int
    bytes_: int
    has_quick_commands: bool = False
    has_key_files: bool = False
    has_gotcha: bool = False
    has_see_also: bool = False
    five_question_hits: dict = field(default_factory=dict)  # qN -> bool
    has_mermaid: bool = False


@dataclass
class Module:
    path: str           # repo-relative
    name: str
    file_count: int
    has_readme: bool
    has_claude_md: bool
    has_agents_md: bool
    context_paths: list = field(default_factory=list)


# --- helper ----------------------------------------------------------------

def run_git(repo: Path, *args) -> list[str]:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo), *args],
            stderr=subprocess.DEVNULL, text=True, errors="replace",
        )
        return [ln for ln in out.splitlines() if ln]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


_REMOTE_BASENAME_RE = re.compile(r"[:/]([^/:]+/[^/]+?)(?:\.git)?/?$")


def detect_repo_name(repo: Path, override: str | None) -> str:
    """repo_path 에 박힐 정규화된 식별자.

    절대경로(/home/.../worktrees/ui)는 다음 audit 이 다른 위치에서 실행되면
    의미 없는 diff 가 되므로 alias 로 대체.

    우선순위:
      1) --repo-name 명시값
      2) `git remote get-url origin` 의 owner/repo basename
         (예: git@github.com:padosol/lol-ui.git → 'lol-ui')
      3) repo 디렉토리 basename (worktree 라면 'ui' 같은 부분명일 수 있음 — 마지막 fallback)
    """
    if override:
        return override
    remotes = run_git(repo, "remote", "get-url", "origin")
    if remotes:
        m = _REMOTE_BASENAME_RE.search(remotes[0])
        if m:
            return m.group(1).split("/")[-1]
    return repo.name


def list_tracked_files(repo: Path) -> list[Path]:
    files = run_git(repo, "ls-files")
    if files:
        return [repo / f for f in files]
    # git이 아닌 경우 walk
    out = []
    for root, dirs, fnames in os.walk(repo):
        # 제외 디렉토리 가지치기 (in-place로 수정)
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in fnames:
            out.append(Path(root) / f)
    return out


def detect_modules(repo: Path, tracked: list[Path]) -> list[Module]:
    """top-level 디렉토리를 모듈 후보로 본다. 모노레포 매니페스트가 있으면 그걸 우선."""
    # 모노레포 신호 체크
    monorepo_hint = any((repo / m).exists() for m in WORKSPACE_MANIFESTS)

    # top-level 디렉토리 후보
    candidates: dict[str, list[Path]] = {}
    for f in tracked:
        try:
            rel = f.relative_to(repo)
        except ValueError:
            continue
        parts = rel.parts
        if len(parts) < 2:
            continue
        top = parts[0]
        if top in EXCLUDED_DIRS or top in NON_MODULE_DIRS:
            continue
        if top.startswith("."):
            continue
        candidates.setdefault(top, []).append(f)

    modules: list[Module] = []
    for name, files in sorted(candidates.items()):
        if len(files) < 2 and not monorepo_hint:
            # 너무 작은 후보는 모듈이 아님
            continue
        m_path = repo / name
        ctx_paths = []
        has_readme = (m_path / "README.md").exists() or (m_path / "README.rst").exists()
        has_claude = (m_path / "CLAUDE.md").exists()
        has_agents = (m_path / "AGENTS.md").exists()
        for cn in CONTEXT_FILENAMES:
            p = m_path / cn
            if p.exists() and p.is_file():
                ctx_paths.append(str(p.relative_to(repo)))
        modules.append(Module(
            path=name,
            name=name,
            file_count=len(files),
            has_readme=has_readme,
            has_claude_md=has_claude,
            has_agents_md=has_agents,
            context_paths=ctx_paths,
        ))
    # 만약 후보가 0개면 (single-package 리포) repo 자체를 단일 모듈로
    if not modules:
        modules.append(Module(
            path=".",
            name=repo.name,
            file_count=len(tracked),
            has_readme=(repo / "README.md").exists() or (repo / "README.rst").exists(),
            has_claude_md=(repo / "CLAUDE.md").exists(),
            has_agents_md=(repo / "AGENTS.md").exists(),
            context_paths=[
                cn for cn in CONTEXT_FILENAMES if (repo / cn).exists()
            ],
        ))
    return modules


def find_context_files(repo: Path, tracked: list[Path]) -> list[Path]:
    """context로 분류할 만한 markdown/rule 파일을 모은다."""
    out = []
    targets = set(CONTEXT_FILENAMES)
    for f in tracked:
        if f.name in targets:
            out.append(f)
        elif f.name.endswith(".md") and any(seg in {"docs", "doc"} for seg in f.parts):
            out.append(f)
    return out


def analyze_context_file(repo: Path, path: Path) -> ContextFile:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    lines = text.count("\n") + 1
    cf = ContextFile(
        path=str(path.relative_to(repo)),
        lines=lines,
        bytes_=len(text.encode("utf-8")),
        has_mermaid=bool(MERMAID_FENCE.search(text)),
    )
    for key, pat in SECTION_PATTERNS.items():
        setattr(cf, key, bool(pat.search(text)))
    for q, pat in FIVE_Q_PATTERNS.items():
        cf.five_question_hits[q] = bool(pat.search(text))
    return cf


def detect_arch_and_dep_docs(context_files: list[ContextFile]) -> dict:
    has_arch = has_dep = has_dataflow = has_diagram = False
    arch_docs = []
    dep_docs = []
    for cf in context_files:
        name = Path(cf.path).name.lower()
        if ARCH_DOC_NAMES.search(name):
            has_arch = True
            arch_docs.append(cf.path)
        if DEP_DOC_NAMES.search(name):
            has_dep = True
            dep_docs.append(cf.path)
        if DATAFLOW_DOC_NAMES.search(name):
            has_dataflow = True
        if cf.has_mermaid:
            has_diagram = True
    return {
        "has_architecture_doc": has_arch,
        "has_dependency_map": has_dep,
        "has_data_flow_diagram": has_dataflow,
        "has_any_diagram": has_diagram,
        "arch_doc_paths": arch_docs,
        "dep_doc_paths": dep_docs,
    }


def detect_ci(repo: Path, tracked: list[Path]) -> dict:
    workflow_dir = repo / ".github" / "workflows"
    workflows = []
    if workflow_dir.is_dir():
        for f in workflow_dir.iterdir():
            if f.suffix in {".yml", ".yaml"}:
                workflows.append(f)

    other_ci = []
    for name in ("Jenkinsfile", ".gitlab-ci.yml", ".circleci/config.yml", "azure-pipelines.yml"):
        p = repo / name
        if p.exists():
            other_ci.append(name)

    hits = {k: False for k in CI_HINTS}
    for wf in workflows:
        try:
            text = wf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for k, pat in CI_HINTS.items():
            if pat.search(text):
                hits[k] = True

    return {
        "github_workflow_count": len(workflows),
        "other_ci_files": other_ci,
        "has_lint_ci": hits["lint"],
        "has_test_ci": hits["test"],
        "has_typecheck_ci": hits["typecheck"],
        "has_doc_ci": hits["docs"],
        "has_freshness_ci": hits["freshness"],
    }


PATH_REF_RE = re.compile(r"`([^`\n]{2,160})`")
LINK_REF_RE = re.compile(r"\]\(([^)\s]+)\)")

def find_broken_refs(repo: Path, context_files: list[ContextFile], limit: int = 50) -> list[dict]:
    """문서에서 백틱/링크 path를 추출, 실제 존재 여부 검사."""
    broken = []
    for cf in context_files:
        full = repo / cf.path
        try:
            text = full.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        candidates: set[str] = set()
        for m in PATH_REF_RE.finditer(text):
            s = m.group(1).strip()
            if not _looks_like_path(s):
                continue
            candidates.add(s)
        for m in LINK_REF_RE.finditer(text):
            s = m.group(1).split("#", 1)[0].strip()
            if not s or s.startswith(("http", "mailto:", "#")):
                continue
            candidates.add(s)

        doc_dir = full.parent
        for s in candidates:
            if _ref_exists(s, repo, doc_dir):
                continue
            broken.append({"doc": cf.path, "ref": s})
            if len(broken) >= limit:
                return broken
    return broken


def _looks_like_path(s: str) -> bool:
    if " " in s or "\t" in s:
        return False
    if not (("/" in s) or s.endswith((".md", ".py", ".ts", ".js", ".java", ".kt", ".go", ".rs", ".sh", ".yml", ".yaml", ".json", ".tsx", ".jsx"))):
        return False
    if s.startswith(("http://", "https://", "mailto:", "git@", "ssh://")):
        return False
    if any(c in s for c in "*?<>|"):  # glob/illegal
        return False
    return True


# frontend / monorepo 컨벤션에서 흔히 생기는 false-positive 제거용 prefix 후보.
# 예: lol-ui 의 CLAUDE.md 가 'app/X.tsx', 'widgets/Y.tsx' 로 src/ 루트 기준 상대경로를 쓰는데
#     audit 가 doc_dir / repo 루트만 검사하면 broken 으로 잡힘.
_CODE_ROOT_HINTS = ("src", "lib", "packages")


def _ref_exists(ref: str, repo: Path, doc_dir: Path) -> bool:
    """
    문서의 path 참조를 다음 순서로 풀이:
      1) absolute (repo 루트 기준)
      2) doc_dir 기준 (가장 흔한 case)
      3) repo 루트 기준
      4) 코드 루트 prefix (src/ lib/ packages/) 자동 보강 — frontend 컨벤션
      5) doc_dir 의 상위 디렉토리 (모듈 CLAUDE.md 가 모듈 루트 prefix 를 생략하는 경우)
    """
    candidates: list[Path] = []
    if ref.startswith("/"):
        candidates.append(repo / ref.lstrip("/"))
    else:
        candidates.append(doc_dir / ref)
        candidates.append(repo / ref)
        # 4) 코드 루트 prefix 자동 보강 (repo 루트에 src/ 등이 있을 때만)
        for hint in _CODE_ROOT_HINTS:
            hint_dir = repo / hint
            if hint_dir.is_dir():
                candidates.append(hint_dir / ref)
        # 5) 모듈 CLAUDE.md fallback — doc_dir 가 repo 직속이 아닐 때
        #    예: module/infra/persistence/clickhouse/CLAUDE.md 가 'config/Application.kt' 표기
        try:
            rel = doc_dir.relative_to(repo)
            if rel != Path(".") and rel.parts:
                # 모듈 루트의 src/main/kotlin, src/main/java 같은 표준 경로도 시도
                for sub in ("src/main/kotlin", "src/main/java", "src/main/resources", "src"):
                    candidates.append(doc_dir / sub / ref)
        except ValueError:
            pass
    return any(p.exists() for p in candidates)


def aggregate_signals(
    repo: Path,
    modules: list[Module],
    context_files: list[ContextFile],
    arch: dict,
    ci: dict,
    broken_refs: list[dict],
) -> dict:
    core_modules = modules
    n_modules = len(core_modules)
    n_with_context = sum(
        1 for m in core_modules if m.has_claude_md or m.has_agents_md or m.has_readme
    )
    n_with_strong_context = sum(  # CLAUDE/AGENTS = stronger AI context than just README
        1 for m in core_modules if m.has_claude_md or m.has_agents_md
    )

    line_dist = [cf.lines for cf in context_files if "CLAUDE" in cf.path or "AGENTS" in cf.path]
    section_counts = {k: sum(1 for cf in context_files if getattr(cf, k)) for k in SECTION_PATTERNS}

    five_q_module_hits = {q: 0 for q in FIVE_Q_PATTERNS}
    for m in modules:
        # 모듈의 모든 컨텍스트 파일 hit 통합
        merged = {q: False for q in FIVE_Q_PATTERNS}
        for cf in context_files:
            if cf.path.startswith(m.path):
                for q, hit in cf.five_question_hits.items():
                    if hit:
                        merged[q] = True
        for q, hit in merged.items():
            if hit:
                five_q_module_hits[q] += 1

    return {
        "core_modules_total": n_modules,
        "core_modules_with_context": n_with_context,
        "core_modules_with_strong_context": n_with_strong_context,
        "navigation_coverage_ratio": round(n_with_strong_context / n_modules, 3) if n_modules else 0.0,
        "claude_md_count": sum(1 for cf in context_files if cf.path.endswith("CLAUDE.md")),
        "agents_md_count": sum(1 for cf in context_files if cf.path.endswith("AGENTS.md")),
        "claude_md_locations": [cf.path for cf in context_files if cf.path.endswith("CLAUDE.md")],
        "claude_md_line_distribution": line_dist,
        "context_files_total": len(context_files),
        "context_files_with_commands_section": section_counts["has_quick_commands"],
        "context_files_with_key_files_section": section_counts["has_key_files"],
        "context_files_with_gotcha_section": section_counts["has_gotcha"],
        "context_files_with_xref_section": section_counts["has_see_also"],
        "modules_answering_q1_what_owned": five_q_module_hits["q1_what_owned"],
        "modules_answering_q2_modification_patterns": five_q_module_hits["q2_modification_patterns"],
        "modules_answering_q3_failure_patterns": five_q_module_hits["q3_failure_patterns"],
        "modules_answering_q4_dependencies": five_q_module_hits["q4_dependencies"],
        "modules_answering_q5_tribal_knowledge": five_q_module_hits["q5_tribal_knowledge"],
        "five_question_module_coverage_pct": [
            round(five_q_module_hits[q] / n_modules * 100, 1) if n_modules else 0.0
            for q in FIVE_Q_PATTERNS
        ],
        **arch,
        **ci,
        "broken_path_refs_in_docs": len(broken_refs),
        "broken_refs_sample": broken_refs[:20],
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Extract AI-Ready signals from a git repo.")
    p.add_argument("repo", help="repo path (git working tree).")
    p.add_argument("--out", help="write JSON to this path (default: stdout)")
    p.add_argument("--pretty", action="store_true", help="pretty-print JSON")
    p.add_argument(
        "--repo-name",
        help="signals.json 의 repo_path 에 박힐 alias (미지정 시 git origin URL 또는 repo 디렉토리명에서 자동 추론). "
             "절대경로 노출 + worktree 위치별 노이즈 제거 목적.",
    )
    args = p.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not repo.exists():
        print(f"ERROR: repo path not found: {repo}", file=sys.stderr)
        return 2

    tracked = list_tracked_files(repo)
    modules = detect_modules(repo, tracked)
    context_paths = find_context_files(repo, tracked)
    context_files = [analyze_context_file(repo, p) for p in context_paths]
    arch = detect_arch_and_dep_docs(context_files)
    ci = detect_ci(repo, tracked)
    broken_refs = find_broken_refs(repo, context_files)
    signals = aggregate_signals(repo, modules, context_files, arch, ci, broken_refs)

    payload = {
        "schema_version": "1.1",
        "tool": "ai-ready-audit/audit.py",
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        # repo_path 는 worktree 위치 노이즈 제거를 위해 alias 로 정규화 (예: 'lol-ui').
        # 디버그용 절대경로는 schema 1.1 부터 별도 안 두고, 필요 시 재실행.
        "repo_path": detect_repo_name(repo, args.repo_name),
        "git_head": (run_git(repo, "rev-parse", "HEAD") or [None])[0],
        "totals": {
            "tracked_files": len(tracked),
        },
        "signals": signals,
        "modules": [asdict(m) for m in modules],
        "context_files": [asdict(cf) for cf in context_files],
    }

    out_text = json.dumps(payload, indent=2 if args.pretty else None, ensure_ascii=False)
    if not out_text.endswith("\n"):
        out_text += "\n"
    if args.out:
        Path(args.out).write_text(out_text, encoding="utf-8")
        print(f"wrote signals → {args.out} ({len(out_text):,} bytes)")
    else:
        sys.stdout.write(out_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
