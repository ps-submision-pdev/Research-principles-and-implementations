"""Completeness check (deterministic): flags gaps, never fills or guesses. Exit code 1 if any gap.

check(kb, db, available, already_done, settings) -> {gaps: [{kind, item}], counts}
Reuses buddy/kb_build/checks.py (size, course exists, slot membership) and adds the paper's checks:
    missing_field  a full course record without title, credits, L, T, P, semester, or provenance page/URL
    unresolved     a prerequisite code that is not in the database, or not in the KB / already passed /
                   pulled in by closure
    no_source      a fact without a source: a record with no provenance URL, a prerequisite edge with no
                   quote, a skill with no quote (model skills whose quote was not found)
Rank reasons and foundations are model judgments, not facts, and are not counted here.
Run: python3 Research/experiments/completeness.py <slice.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from buddy.kb_build import checks  # noqa: E402

REQUIRED = ("title", "credits", "l", "t", "p", "semester")


def check(kb: dict, db: dict, available: dict | None, already_done: list, settings: dict, closure_added=()) -> dict:
    gaps = [{"kind": "size", "item": w} for w in checks.check_size(len(kb["courses"]), settings)]
    gaps += [{"kind": "course_exists", "item": p} for p in checks.check_course_exists(kb, db)]
    if available is not None:
        gaps += [{"kind": "slot_membership", "item": p} for p in checks.check_slot_membership(kb, available)]
    known = set(kb["courses"]) | set(already_done) | set(closure_added)
    for code, r in sorted(kb["courses"].items()):
        gaps += [{"kind": "missing_field", "item": f"{code}.{f}"} for f in REQUIRED if r.get(f) in (None, "")]
        prov = r.get("provenance") or {}
        gaps += [{"kind": "missing_field", "item": f"{code}.provenance.{f}"} for f in ("page", "url") if not prov.get(f)]
        if not prov.get("url"):
            gaps.append({"kind": "no_source", "item": f"{code} record"})
        for e in r["prerequisites"]:
            if e["code"] not in db or e["code"] not in known:
                gaps.append({"kind": "unresolved", "item": f"{code} -> {e['code']}"})
            if not e.get("quote"):
                gaps.append({"kind": "no_source", "item": f"{code} prerequisite {e['code']}"})
        gaps += [{"kind": "no_source", "item": f"{code} skill {s['skill']!r}"} for s in r["skills"] if not s.get("quote")]
    counts = {}
    for g in gaps:
        counts[g["kind"]] = counts.get(g["kind"], 0) + 1
    return {"gaps": gaps, "counts": counts}


def main() -> int:
    kb = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    db = json.loads((ROOT / "data/db/resolved.json").read_text(encoding="utf-8"))
    import yaml
    settings = yaml.safe_load((ROOT / "config/kb_build.yaml").read_text(encoding="utf-8"))
    persona = json.loads((ROOT / "personas" / f"{kb['persona_id']}.json").read_text(encoding="utf-8"))
    out = check(kb, db, None, persona["already_done"], settings)
    for g in out["gaps"]:
        print(f"GAP {g['kind']}: {g['item']}")
    print("gaps:", out["counts"] or "none")
    return 1 if out["gaps"] else 0


if __name__ == "__main__":
    sys.exit(main())
