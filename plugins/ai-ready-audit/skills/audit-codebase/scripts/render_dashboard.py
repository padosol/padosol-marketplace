#!/usr/bin/env python3
"""
render_dashboard.py — scorecard.json + rubric.json → 한국어 HTML 대시보드.

사용:
    python3 render_dashboard.py <scorecard.json> --signals <signals.json> --out report.html

scorecard.json 스키마(요약):
{
  "repo_name": "...",
  "repo_path": "...",
  "scanned_at": "ISO datetime",
  "git_head": "abc123...",
  "scores": {
    "A": { "score": 10, "reason": "..." },
    "B": { "score": 14, "items": { "B1": {"score":3, "reason":"..."}, ... } },
    ...
  }
}
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Any

HERE = Path(__file__).parent
DEFAULT_RUBRIC = HERE.parent / "references" / "rubric.json"
DEFAULT_TEMPLATE = HERE.parent / "assets" / "dashboard_template.html"


def grade_for(score: int, thresholds: list[dict]) -> dict:
    for t in sorted(thresholds, key=lambda x: -x["min"]):
        if score >= t["min"]:
            return t
    return thresholds[-1]


def grade_class(level: str) -> str:
    # CSS class 만들기. "AI-Native / Agentic-Ready" → "grade-AI-Native"
    head = level.split("/")[0].strip().replace(" ", "-")
    return f"grade-{head}"


def bar_class(ratio: float) -> str:
    if ratio >= 0.85: return "bar-good"
    if ratio >= 0.6:  return "bar-ok"
    if ratio >= 0.3:  return "bar-warn"
    return "bar-bad"


def html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def render_category_cards(rubric: dict, scorecard: dict) -> str:
    parts = []
    for cat in rubric["categories"]:
        cid = cat["id"]
        sc = scorecard["scores"].get(cid, {})
        score = int(sc.get("score", 0))
        max_p = cat["points"]
        ratio = score / max_p if max_p else 0
        reason = sc.get("reason", "")

        # subitems 표시
        sub_html = ""
        if cat.get("scoring_type") == "subitems":
            rows = []
            for it in cat["items"]:
                isc = sc.get("items", {}).get(it["id"], {})
                isc_v = int(isc.get("score", 0))
                rows.append(
                    f'<tr><td><strong>{it["id"]}</strong> {html_escape(it["name"])}</td>'
                    f'<td style="text-align:right">{isc_v}/{it["points"]}</td></tr>'
                )
            sub_html = (
                '<table style="margin-top:12px; font-size:13px;">'
                + "".join(rows) + "</table>"
            )

        parts.append(f"""
<div class="cat-card">
  <div class="cat-id">{cid}</div>
  <h3>{html_escape(cat["name"])}</h3>
  <div class="scoreline"><span class="score">{score}</span><span class="max">/{max_p}</span></div>
  <div class="bar {bar_class(ratio)}"><div style="width:{ratio*100:.0f}%"></div></div>
  <div class="desc">{html_escape(cat["what_it_measures"])}</div>
  {f'<div class="reason">{html_escape(reason)}</div>' if reason else ''}
  {sub_html}
</div>
""")
    return "\n".join(parts)


@dataclass
class RoiItem:
    rank: int
    label: str
    current: int
    max_p: int
    gap: int
    effort: str
    roi: float
    action_hint: str


def compute_roi(rubric: dict, scorecard: dict) -> list[RoiItem]:
    weights = rubric["effort_weights"]
    out: list[RoiItem] = []
    for cat in rubric["categories"]:
        sc = scorecard["scores"].get(cat["id"], {})
        if cat.get("scoring_type") == "subitems":
            for it in cat["items"]:
                isc = sc.get("items", {}).get(it["id"], {})
                cur = int(isc.get("score", 0))
                gap = it["points"] - cur
                if gap <= 0: continue
                effort = it.get("effort", "medium")
                roi = gap / weights.get(effort, 3)
                out.append(RoiItem(
                    rank=0,
                    label=f'{cat["id"]}{it["id"][1:]} · {it["name"]}',
                    current=cur, max_p=it["points"], gap=gap,
                    effort=effort, roi=roi,
                    action_hint=isc.get("action_hint") or it.get("full_criteria", ""),
                ))
        else:
            cur = int(sc.get("score", 0))
            gap = cat["points"] - cur
            if gap <= 0: continue
            effort = cat.get("effort", "medium")
            roi = gap / weights.get(effort, 3)
            # 다음 단계 criteria 찾기
            next_level = next((lv for lv in cat.get("levels", []) if lv["score"] > cur), None)
            hint = sc.get("action_hint") or (next_level["criteria"] if next_level else cat["what_it_measures"])
            out.append(RoiItem(
                rank=0, label=f'{cat["id"]} · {cat["name"]}',
                current=cur, max_p=cat["points"], gap=gap,
                effort=effort, roi=roi, action_hint=hint,
            ))
    out.sort(key=lambda x: -x.roi)
    for i, item in enumerate(out, 1):
        item.rank = i
    return out


def render_roi_rows(roi: list[RoiItem]) -> str:
    rows = []
    for item in roi:
        rows.append(f"""
<tr>
  <td><span class="roi-rank">{item.rank}</span></td>
  <td>{html_escape(item.label)}</td>
  <td>{item.current}</td>
  <td>{item.max_p}</td>
  <td><strong>+{item.gap}</strong></td>
  <td class="effort-{item.effort}">{item.effort}</td>
  <td>{html_escape(item.action_hint)}</td>
</tr>
""")
    return "\n".join(rows) if rows else "<tr><td colspan='7' class='muted' style='text-align:center;'>모든 항목 만점입니다 🎉</td></tr>"


def render_broken_refs_section(signals: dict) -> str:
    refs = signals.get("broken_refs_sample", [])
    n = signals.get("broken_path_refs_in_docs", 0)
    if not refs:
        return ""
    items = "".join(f'<li><code>{html_escape(r["doc"])}</code> → <code>{html_escape(r["ref"])}</code></li>' for r in refs[:30])
    return f"""
<h2>문서 내 의심 참조 ({n}건)</h2>
<div class="warn-box">
  context 문서에서 백틱/링크로 참조된 경로 중 audit이 실제로 찾지 못한 항목입니다.
  실제로는 깊은 경로에 존재할 수 있으니 <strong>샘플링 검증 필수</strong>.
  (E1. Reference Accuracy 점수에 영향)
</div>
<ul class="ref-list">{items}</ul>
"""


def main() -> int:
    p = argparse.ArgumentParser(description="Render AI-Ready dashboard HTML.")
    p.add_argument("scorecard", help="path to scorecard.json (Claude가 작성)")
    p.add_argument("--rubric", default=str(DEFAULT_RUBRIC))
    p.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    p.add_argument("--signals", help="path to signals.json from audit.py (선택)")
    p.add_argument("--out", required=True, help="output HTML path")
    args = p.parse_args()

    rubric = json.loads(Path(args.rubric).read_text(encoding="utf-8"))
    scorecard = json.loads(Path(args.scorecard).read_text(encoding="utf-8"))
    template_text = Path(args.template).read_text(encoding="utf-8")
    signals = (
        json.loads(Path(args.signals).read_text(encoding="utf-8"))["signals"]
        if args.signals else {}
    )

    total = sum(int(scorecard["scores"].get(c["id"], {}).get("score", 0)) for c in rubric["categories"])
    grade = grade_for(total, rubric["grade_thresholds"])
    roi = compute_roi(rubric, scorecard)

    # 메타 카드용 숫자
    nav_pct = round(signals.get("navigation_coverage_ratio", 0.0) * 100, 1)
    primary_ctx = signals.get("claude_md_count", 0) + signals.get("agents_md_count", 0)

    html = template_text
    repls = {
        "REPO_NAME": scorecard.get("repo_name", "(unknown)"),
        "REPO_PATH": scorecard.get("repo_path", ""),
        "GIT_HEAD_SHORT": (scorecard.get("git_head") or "")[:8] or "n/a",
        "SCANNED_AT": scorecard.get("scanned_at", ""),
        "TOTAL_SCORE": str(total),
        "GRADE_LEVEL": grade["level"],
        "GRADE_DESC": grade["desc"],
        "GRADE_CLASS": grade_class(grade["level"]),
        "TRACKED_FILES": str(scorecard.get("tracked_files", "?")),
        "MODULES_TOTAL": str(signals.get("core_modules_total", "?")),
        "CONTEXT_PRIMARY_COUNT": str(primary_ctx),
        "NAV_COVERAGE_PCT": str(nav_pct),
        "BROKEN_REF_COUNT": str(signals.get("broken_path_refs_in_docs", "?")),
        "CATEGORY_CARDS": render_category_cards(rubric, scorecard),
        "ROI_ROWS": render_roi_rows(roi),
        "BROKEN_REFS_SECTION": render_broken_refs_section(signals),
        "RUBRIC_VERSION": rubric.get("version", "?"),
        "SCORECARD_PATH": args.scorecard,
    }
    for k, v in repls.items():
        html = html.replace("{{" + k + "}}", v)

    Path(args.out).write_text(html, encoding="utf-8")
    print(f"wrote dashboard → {args.out} ({len(html):,} bytes, total score {total}, grade {grade['level']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
