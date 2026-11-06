# Research principles and implementations

Notes on research papers we use for the Personalised Learning Buddy project, and how each is (or is not) implemented in our KB-building pipeline.

## Paper: KnowPlan

**Name of paper.** KnowPlan: From Heterogeneous University Catalogs to Personalized Degree Plans (Cao et al.; UC San Diego, Yale, UNC Chapel Hill).

**Link.** https://arxiv.org/pdf/2608.06530

### What it talks about

Degree planning from public university sources, split into two stages. **CatalogBrowse** is a web-exploration agent that, given only a university, crawls pages/JSON/PDFs and outputs provenance-linked JSON (courses and prerequisites, program requirements, gen-ed rules). It picks pages by expected gain on a fixed checklist of "obligations" per unit access cost, and stops only when a deterministic closure certificate passes. **DegreeMap** builds a requirement graph and solves for a plan with lexicographic CP-SAT (feasibility, then time, workload, preference fit, future flexibility). Reported: 96.2% inventory recall, 47% fewer page accesses than an exhaustive crawl, 100% hard feasibility.

### What in it is implementable for us

1. A fixed obligation checklist as the KB schema: index entry, entity, required fields, resolved typed references, provenance.
2. Provenance on every fact (source URL).
3. Closure over references (pull in prerequisites until all resolve).
4. A deterministic completeness check that flags gaps instead of guessing.
5. Evaluation against a gold KB (paired comparison) and a masked-source test.
6. Hard constraints first, soft preferences only rank what remains valid.
7. LLM kept to a narrow, validated role (cannot emit ids/URLs/actions).

### If we do implement it, how can we implement it?

Schema: typed entities with required fields, ids for references, source URL per fact. Pipeline: candidates -> scope selection -> prerequisite closure (script) -> completeness report (script) -> KB JSON with provenance. Evaluation: compare the generated KB to the hand-built KB (entity and prerequisite-edge precision/recall) and log tokens/calls per variant.

### Gaps in the research

Has no persona, so it never decides what is relevant to one learner. Who authored the obligations is not stated; their weights are not given; the set is called fixed but also grows during parsing. Does not say how action-outcome estimates are produced. No direct LLM-vs-rule ablation (the LLM-driven ReAct baseline differs in several ways, so it is confounded). Targets degree planning on structured catalogs, not an adaptive learning buddy over messy material.

### Special notes, unique things about the paper, and my personal keep-in-mind

Unique: closure certificate instead of a learned stopping rule; LLM allowed only as a schema-bound fallback (removing it left recall at 96.0 vs 96.2 but cut rule-parsing equivalence from 77.8 to 67.1).

Our twist: add an LLM for persona-relevance scope selection, restricted to ids that exist in our extracted data, then let code expand and verify.

Keep in mind: ingestion must stay persona-agnostic; the KB is built by hand for the submission, so the pipeline is for showing scope and for comparison; understand how it works before writing code; always note what each full-scale part collapses to in the mini-project (script, hand choice, LLM call, or skipped).

## Experiment plan: does adding an LLM change the KB?

Three variants over the same extracted IIT Patna data and the same persona ("wants ML, weak maths grades"):

- **A. Previous pipeline (baseline).** Scope selection, closure and completeness check as currently implemented.
- **B. Paper-style (rules only).** Scope selection by department/topic rules; closure and completeness check by script.
- **C. Hybrid (ours).** Scope selection by one LLM call over candidate ids, with the output validated; closure and completeness check by script.

Metrics, each compared with the hand-built KB: entity precision and recall; prerequisite-edge precision and recall; unresolved references and missing required fields (from the completeness report); provenance coverage (share of facts with a source URL); tokens (input/output), number of LLM calls and wall time.

Hypothesis to test, not a claim: B and C produce nearly the same KB, with C using far fewer tokens than A.

## Results

Every number here is copied from `results.json`, produced by `python3 Research/experiments/run.py` from the mini-project folder; none is estimated. The full tables are in `results.md`.

### How it was run

The run differs from the plan above in three ways. The persona is `personas/chem_data_s4.json`: a 2nd-year Chemical Engineering student who wants computing and data skills and is weak at maths. Variant B uses the existing keyword-fallback ranking rather than separate topic rules. And the mini-project already had a full pipeline, so A is that pipeline. The model was `nvidia/nemotron-3-ultra-550b-a55b:free` via OpenRouter, at temperature 0.

**A** is the full mini-project build: the model ranks the elective options, proposes prerequisites, picks foundation courses for each weakness and lists skills. **B** uses no model at all: keyword-fallback ranking, prerequisites stated in the database only, then the same closure and completeness check. **C** uses the model for ranking only (course ids validated by code), and does everything else like B. A was run once (its token cost comes from the token log), B twice and C three times, each C run with a fresh cache so it was a real model call.

**There is no hand-built gold KB, so this is agreement, not accuracy.** Precision and recall cannot be computed; the variants are compared with each other and with A. Only 4 of the 14 KB courses have a prerequisite stated in the database, so prerequisite links are reported as counts, not percentages.

### What each variant produced

**A** kept the elective options CS2207 (Introduction to Data Science), MA2206 (Introduction to Numerical Methods), MA3107 (Partial Differential Equations) and CS3106 (Computer Graphics), alongside the same 10 core courses as every variant. It has 14 prerequisite links (5 stated in the database and 9 proposed by the model, each with a quote found in the course text), 84 skills and 6 foundation links. All 112 of its facts have a source. It made 4 model calls, using 15,279 input and 29,551 output tokens (44,830 in total). Its original wall time was not measured, so none is reported.

**B** kept CE3105 (Green Building), CS2207, MA2206 and MA3107. It has the 5 stated prerequisite links and nothing else; all 19 of its facts have a source. It made no model call and used 0 tokens. Its two runs produced byte-identical KBs.

**C** kept exactly A's four options in all 3 runs. Like B, it has only the 5 stated prerequisite links, all 19 facts sourced. Each run made 1 model call: 2,097 input tokens, and 2,053, 2,349 and 2,780 output tokens. The runs took 92, 53 and 102 seconds.

In every variant the closure added no course, and the completeness check found no gap: no missing field, no unresolved reference and no fact without a source.

### How much they agree

On the 4 elective options, A and C agree completely (Jaccard 1.0 for all three C runs), and the three C runs agree with each other completely. A and B agree on 3 of the 5 distinct options (Jaccard 0.6), and so do B and C. Over all 14 records, the same pairs score 1.0 and 0.867. All variants share the same 5 stated prerequisite links; A has 9 more from the model.

### Reading

**The hypothesis is only half supported.** C picked exactly A's courses in all three runs, for about 4.2-4.9k tokens, roughly a tenth of A's 44.8k. But B did not match C. It kept Green Building instead of Computer Graphics, because when no keyword matches, the fallback picks by alphabetical code. So rules alone do not produce the same KB here; the one model ranking call is what separates B from C.

**C matching A is partly by construction.** A's ranking step uses the same prompt (`rank_v2`) as C. A's other three model steps (prerequisites, skills, foundations) do not change which courses are selected; they add content: 9 model prerequisite links, 84 skills and 6 foundation links. That content costs about 40k of A's 44.8k tokens.

**The model was stable but not identical.** At temperature 0, the three C runs chose the same courses in the same order, but their output length differed (2,053 to 2,780 tokens), so the reasons are worded differently.

**Agreement is not accuracy.** Whether Computer Graphics is a better pick than Green Building for this student is a judgment. A hand-built `Research/gold_chem_data_s4.json` (written by hand, never generated) would let `run.py` compute precision and recall.

## Full-scale version vs. what we build

- **Agent discovers sources and picks pages by expected gain** becomes a Python script over a hand-picked list of pages.
- **Rules plus LLM fallback to structured JSON** becomes one LLM call per page into a fixed JSON schema.
- **Closure certificate over everything crawled** becomes a short closure loop plus a checker script.
- **Per-persona relevance over a large catalog** becomes one validated LLM call over a small id list.
- **Constraint-solver planning** becomes an LLM call or a topological sort.

## Source

Cao et al., KnowPlan: From Heterogeneous University Catalogs to Personalized Degree Plans, arXiv 2608.06530.
