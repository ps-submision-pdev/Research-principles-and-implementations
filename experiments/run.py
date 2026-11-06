"""Run variants A, B and C on the same data and persona, compare them, write Research/results.json + results.md.

Run from the mini-project root:  python3 Research/experiments/run.py [--persona chem_data_s4]
    A  the full build: the model ranks, proposes prerequisites, foundations and skills. Built once from the
       main LLM cache (data/cache/llm/), so no new tokens; its token cost is read from the main token log
       (data/logs/llm_calls.jsonl, the first real call of each of its four prompts). Never estimated.
    B  no model at all: keyword-fallback rank, database prerequisites only, no foundations, no skills.
       Run twice; the two slices must be byte-identical.
    C  the model for rank only (ids validated by buddy/kb_build/rank.py); everything else as B.
       Run three times, each with a NEW empty cache folder (Research/runs/cache/C<n>), so each is a real call.
Every variant then gets the same closure (closure.py) and completeness check (completeness.py).
There is no hand-built gold KB unless Research/gold_<persona>.json exists (written by hand, never generated).
Without it this is AGREEMENT, not accuracy: variants are compared with each other and with A.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from itertools import combinations
from pathlib import Path

import yaml
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
RESEARCH, ROOT = HERE.parent, HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from buddy.kb_build.persona import load_persona  # noqa: E402
from buddy.kb_build.slice import build_slice  # noqa: E402
from buddy.llm import LLMClient  # noqa: E402
from closure import closure  # noqa: E402
from completeness import check  # noqa: E402

STEPS = ("rank", "prerequisites", "skills", "foundations")
A_PROMPTS = ("rank_v2", "prereq_v1", "skills_v1", "foundations_v1")
VARIANTS = {"A": dict.fromkeys(STEPS, True), "B": dict.fromkeys(STEPS, False),
            "C": {"rank": True, "prerequisites": False, "skills": False, "foundations": False}}


def load_inputs(persona_id: str) -> dict:
    db = json.loads((ROOT / "data/db/resolved.json").read_text(encoding="utf-8"))
    return {"db": db, "entries": json.loads((ROOT / "data/db/list_entries.json").read_text(encoding="utf-8")),
            "rules": json.loads((ROOT / "data/kb/rules.json").read_text(encoding="utf-8")),
            "settings": yaml.safe_load((ROOT / "config/kb_build.yaml").read_text(encoding="utf-8")),
            "trust": yaml.safe_load((ROOT / "config/trust.yaml").read_text(encoding="utf-8")),
            "persona": load_persona(ROOT / "personas" / f"{persona_id}.json", db=db)}


def run_variant(variant: str, llm, inputs: dict) -> dict:
    """Build one slice with the variant's model switches, then closure, completeness and the measures."""
    settings = {**inputs["settings"], "use_model": VARIANTS[variant]}
    start = time.perf_counter()
    kb, extra = build_slice(inputs["persona"], inputs["db"], inputs["entries"], inputs["rules"], llm, settings, inputs["trust"])
    wall = round(time.perf_counter() - start, 2)
    usage = [extra[s]["usage"] for s in STEPS]
    closed = closure(sorted(kb["courses"]), inputs["db"], inputs["persona"]["already_done"])
    gaps = check(kb, inputs["db"], extra["available"], inputs["persona"]["already_done"], settings, closed["added"])
    facts = [bool(r["provenance"].get("url")) for r in kb["courses"].values()]
    facts += [bool(e.get("quote")) for r in kb["courses"].values() for e in r["prerequisites"]]
    facts += [bool(s.get("quote")) for r in kb["courses"].values() for s in r["skills"]]
    failed = [d["said"]["error"] for s in STEPS for d in extra[s]["decisions"]
              if d["verdict"] == "fallback" and isinstance(d["said"], dict) and "error" in d["said"]]
    return {
        "variant": variant, "rank_source": kb["rank_source"], "model_failures": failed, "wall_seconds": wall,
        "calls": sum(1 for u in usage if u["attempts"]), "attempts": sum(u["attempts"] for u in usage),
        "prompt_tokens": sum(u["prompt_tokens"] for u in usage), "completion_tokens": sum(u["completion_tokens"] for u in usage),
        "options": {s["slot"]: s["options"] for s in kb["slots"] if s["full_records"]},
        "records": sorted(kb["courses"]),
        "edges": sorted([c, e["code"], e["source"]] for c, r in kb["courses"].items() for e in r["prerequisites"]),
        "skills": sum(len(r["skills"]) for r in kb["courses"].values()), "foundations": len(kb["foundations"]),
        "closure_added": closed["added"], "closure_unresolved": closed["unresolved"],
        "gaps": gaps["counts"], "gap_total": len(gaps["gaps"]),
        "provenance_share": round(sum(facts) / len(facts), 3) if facts else None, "facts": len(facts),
        "_slice": kb,
    }


def logged_cost_of_a() -> dict:
    """A's real cost: the first real (not cached) successful call of each of A's prompts in the main log."""
    found = {}
    for line in (ROOT / "data/logs/llm_calls.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e["prompt_version"] in A_PROMPTS and not e["cached"] and e["ok"] and e["prompt_version"] not in found:
            found[e["prompt_version"]] = e
    missing = [p for p in A_PROMPTS if p not in found]
    return {"calls": len(found), "prompt_tokens": sum(e["prompt_tokens"] for e in found.values()),
            "completion_tokens": sum(e["completion_tokens"] for e in found.values()), "missing_from_log": missing,
            "per_prompt": {p: found[p]["prompt_tokens"] + found[p]["completion_tokens"] for p in found}}


def jaccard(a: list, b: list) -> float:
    """Shared items / all items of two lists of codes; 1.0 when both are empty."""
    a, b = set(a), set(b)
    return 1.0 if not a | b else round(len(a & b) / len(a | b), 3)


def option_set(run: dict) -> list:
    return sorted(c for codes in run["options"].values() for c in codes)


def compare(runs: dict, gold: dict | None) -> dict:
    names = sorted(runs)
    pair = {}
    for x, y in combinations(names, 2):
        rx, ry = runs[x], runs[y]
        ex, ey = {tuple(e[:2]) for e in rx["edges"]}, {tuple(e[:2]) for e in ry["edges"]}
        pair[f"{x} vs {y}"] = {"options_jaccard": jaccard(option_set(rx), option_set(ry)),
                               "records_jaccard": jaccard(rx["records"], ry["records"]),
                               "edges": {"left": len(ex), "right": len(ey), "shared": len(ex & ey)}}
    out = {"pairwise": pair}
    if gold:
        out["gold"] = {}
        g_ids, g_edges = set(gold.get("records", [])), {tuple(e) for e in gold.get("edges", [])}
        for n in names:
            ids, edges = set(runs[n]["records"]), {tuple(e[:2]) for e in runs[n]["edges"]}
            out["gold"][n] = {"entity_precision": round(len(ids & g_ids) / len(ids), 3) if ids else None,
                              "entity_recall": round(len(ids & g_ids) / len(g_ids), 3) if g_ids else None,
                              "edges_shared_with_gold": len(edges & g_edges), "gold_edges": len(g_edges)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", default="chem_data_s4")
    args = ap.parse_args()
    load_dotenv(ROOT / ".env")
    inputs = load_inputs(args.persona)
    runs_dir = RESEARCH / "runs"
    runs_dir.mkdir(exist_ok=True)
    runs = {}

    a_llm = LLMClient(timeout=120, cache_dir=ROOT / "data/cache/llm", log_file=runs_dir / "llm_calls_A_rebuild.jsonl")
    a = run_variant("A", a_llm, inputs)
    cost = logged_cost_of_a()
    a.update({"rebuild_calls_from_cache": a["calls"], "calls": cost["calls"], "prompt_tokens": cost["prompt_tokens"],
              "completion_tokens": cost["completion_tokens"], "wall_seconds": None, "cost_source": cost})
    runs["A"] = a
    print(f"A: rebuilt from the main cache ({a['rebuild_calls_from_cache']} new calls); logged cost {cost}")

    b = [run_variant("B", None, inputs) for _ in range(2)]
    b_identical = json.dumps(b[0]["_slice"], sort_keys=True) == json.dumps(b[1]["_slice"], sort_keys=True)
    runs["B"] = b[0]
    print(f"B: 2 runs, byte-identical slices: {b_identical}")

    for n in (1, 2, 3):
        cache = runs_dir / "cache" / f"C{n}"
        shutil.rmtree(cache, ignore_errors=True)
        llm = LLMClient(timeout=120, cache_dir=cache, log_file=runs_dir / "llm_calls_C.jsonl")
        runs[f"C{n}"] = run_variant("C", llm, inputs)
        r = runs[f"C{n}"]
        print(f"C{n}: rank_source {r['rank_source']}, calls {r['calls']}, tokens {r['prompt_tokens']}+{r['completion_tokens']}, "
              f"wall {r['wall_seconds']}s, failures {r['model_failures'] or 'none'}, options {r['options']}")

    gold_path = RESEARCH / f"gold_{args.persona}.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8")) if gold_path.exists() else None
    stated = sum(1 for c in runs["A"]["records"] if any(e[0] == c and e[2] == "explicit" for e in runs["A"]["edges"]))
    for name, r in runs.items():
        (runs_dir / f"{name}.slice.json").write_text(json.dumps(r.pop("_slice"), indent=1, sort_keys=True) + "\n",
                                                     encoding="utf-8")
    result = {"persona": args.persona, "model": a_llm.model, "temperature": 0,
              "mode": "gold" if gold else "agreement (no gold KB: agreement is not accuracy)",
              "records_with_stated_prerequisites": stated,
              "edge_metrics": "counts only (fewer than 5 records have stated prerequisites)" if stated < 5 else "meaningful",
              "b_runs_identical": b_identical, "runs": runs, "comparison": compare(runs, gold)}
    (RESEARCH / "results.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    write_table(result)
    print("wrote Research/results.json and Research/results.md")
    return 0


def write_table(result: dict) -> None:
    rows = ["| Run | Kept options (horizon slots) | Records | Edges (explicit/model) | Closure added | Gaps | Provenance | Tokens in/out | LLM calls | Wall s |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in result["runs"].items():
        kinds = [e[2] for e in r["edges"]]
        rows.append(f"| {name} | {', '.join(option_set(r))} | {len(r['records'])} | {kinds.count('explicit')}/"
                    f"{len(kinds) - kinds.count('explicit')} | {len(r['closure_added'])} | {r['gap_total']} {r['gaps'] or ''} | "
                    f"{r['provenance_share']} of {r['facts']} facts | {r['prompt_tokens']}/{r['completion_tokens']} | "
                    f"{r['calls']} | {r['wall_seconds'] if r['wall_seconds'] is not None else 'not measured'} |")
    pairs = ["| Pair | Options Jaccard | Records Jaccard | Edges (left / right / shared) |", "|---|---|---|---|"]
    for k, v in result["comparison"]["pairwise"].items():
        e = v["edges"]
        pairs.append(f"| {k} | {v['options_jaccard']} | {v['records_jaccard']} | {e['left']} / {e['right']} / {e['shared']} |")
    text = [f"# Results ({result['persona']}, model {result['model']}, temperature {result['temperature']})", "",
            f"Mode: {result['mode']}. Records with stated prerequisites: {result['records_with_stated_prerequisites']} "
            f"-> edge metrics: {result['edge_metrics']}. B's two runs identical: {result['b_runs_identical']}.", ""]
    (RESEARCH / "results.md").write_text("\n".join(text + rows + [""] + pairs) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
