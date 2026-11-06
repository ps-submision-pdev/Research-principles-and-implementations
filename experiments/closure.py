"""Deterministic prerequisite closure over STATED prerequisites only (the paper's closure idea).

closure(selected, db, already_done) -> {added, unresolved, edges}
Starting from the KB's courses, follow the course codes named in each course's database prerequisite
field. A prerequisite that is in the KB or already passed is satisfied. One that is neither is pulled
in ("added") and followed in turn. A code the database does not hold is "unresolved" (flagged, never
guessed). A visited set means every course is expanded once, so a cycle (A needs B, B needs A) ends.
"""
from __future__ import annotations

import re

CODE = re.compile(r"\b[A-Z]{2}\d{4}\b")


def stated(code: str, db: dict) -> list[str]:
    raw = (db.get(code, {}).get("prerequisite", {}) or {}).get("value") or ""
    return [c for c in dict.fromkeys(CODE.findall(raw)) if c != code]


def closure(selected: list, db: dict, already_done: list) -> dict:
    done, kb = set(already_done), set(selected)
    added, unresolved, edges, seen = [], [], [], set()
    todo = sorted(selected)
    while todo:
        code = todo.pop(0)
        if code in seen:
            continue
        seen.add(code)
        for pre in stated(code, db):
            edges.append((code, pre))
            if pre not in db:
                unresolved.append((code, pre))
            elif pre not in kb and pre not in done:
                kb.add(pre)
                added.append(pre)
                todo.append(pre)
    return {"added": added, "unresolved": unresolved, "edges": sorted(set(edges))}
