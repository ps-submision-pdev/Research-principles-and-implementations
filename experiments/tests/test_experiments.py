"""Tests for the experiment: unknown ids, closure on cycles, the completeness check, and A/B/C on real data
with a fake model (no network)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from buddy.kb_build.rank import rank  # noqa: E402
from closure import closure  # noqa: E402
from completeness import check  # noqa: E402
import run  # noqa: E402

USAGE = {"attempts": 1, "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}


class FakeLLM:
    model = "fake"

    def __init__(self):
        self.calls = []

    def ask_json(self, messages, schema, prompt_version):
        self.calls.append(prompt_version)
        replies = {"rank_v2": {"ranked": [{"code": "ZZ9999", "reason": "invented"}, {"code": "MA2206", "reason": "maths"}]},
                   "prereq_v1": {"prerequisites": []}, "skills_v1": {"skills": []},
                   "foundations_v1": {"foundations": []}}
        return {"ok": True, "data": replies[prompt_version], "usage": USAGE, "cached": False}


def test_an_unknown_id_from_the_model_is_rejected():
    available = {"slots": [{"slot": "IDE-I", "semester": 4, "options": ["MA2206"]}]}
    db = {"MA2206": {"title": {"value": "Numerical Methods"}, "ltpc": {"value": {"l": 3, "t": 0, "p": 0, "c": 3.0}},
                     "owner_department": {"value": "Mathematics"}, "description": {"value": "text"},
                     "objectives": {"value": None}, "outcomes": {"value": None}}}
    out = rank({"goal_text": "g", "goal_keywords": [], "weaknesses": [], "known_topics": [], "planning_semester": 4},
               available, {"results": []}, db, FakeLLM(), {"options_per_slot": 2, "description_chars": 50}, "rank_v2")
    verdicts = {d["said"]["code"]: d["verdict"] for d in out["decisions"]}
    assert verdicts["ZZ9999"] == "dropped:code not in the candidate list"
    assert [i["code"] for i in out["by_slot"]["IDE-I"]] == ["MA2206"]


def test_closure_terminates_on_a_cycle_and_flags_unresolved_codes():
    db = {"XA1000": {"prerequisite": {"value": "XB1000"}}, "XB1000": {"prerequisite": {"value": "XA1000 and ZZ0000"}}}
    out = closure(["XA1000"], db, already_done=[])
    assert out["added"] == ["XB1000"]
    assert out["unresolved"] == [("XB1000", "ZZ0000")]
    assert ("XA1000", "XB1000") in out["edges"] and ("XB1000", "XA1000") in out["edges"]


def test_the_checker_catches_a_missing_field_and_a_fact_without_a_source():
    record = {"title": "T", "credits": None, "l": 3, "t": 0, "p": 0, "semester": 4, "slot": None,
              "provenance": {"page": 2, "url": "https://x"}, "skills": [{"skill": "s", "quote": None}],
              "prerequisites": [{"code": "XB1000", "quote": None}]}
    kb = {"courses": {"XA1000": record}, "core": {}, "later_core": {}, "slots": [], "foundations": []}
    out = check(kb, {"XA1000": {}, "XB1000": {}}, None, [], {"kb_min_courses": 1, "kb_max_courses": 15})
    kinds = {(g["kind"], g["item"]) for g in out["gaps"]}
    assert ("missing_field", "XA1000.credits") in kinds
    assert ("unresolved", "XA1000 -> XB1000") in kinds
    assert ("no_source", "XA1000 skill 's'") in kinds and ("no_source", "XA1000 prerequisite XB1000") in kinds


def test_a_b_and_c_run_on_the_real_inputs_with_a_fake_model():
    inputs = run.load_inputs("chem_data_s4")
    calls = {}
    for variant in ("A", "B", "C"):
        llm = FakeLLM()
        result = run.run_variant(variant, None if variant == "B" else llm, inputs)
        calls[variant] = llm.calls
        assert len(result["records"]) == 14 and result["gap_total"] >= 0
    assert calls["B"] == [] and calls["C"] == ["rank_v2"]
    assert sorted(calls["A"]) == ["foundations_v1", "prereq_v1", "rank_v2", "skills_v1"]
