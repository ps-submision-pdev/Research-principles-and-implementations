# Prompt for Claude Code: paper-inspired KB building, with and without an LLM

Paste everything below the line into Claude Code, started from the project folder that contains the KB pipeline.

---

Context
I'm building a submission for the "Personalised Learning Buddy" problem. The KB is built from IIT Patna's public academics pages. Persona: "wants to learn ML but has weak maths grades". The pipeline must be persona-agnostic: given any persona, it decides what goes into the KB.

I'm adapting ideas from the KnowPlan paper (arXiv 2608.06530): a fixed schema checklist, provenance on every fact, deterministic closure over references, and a deterministic completeness check. The paper uses an LLM only as a narrow, schema-bound fallback and never to decide relevance. My addition is an LLM call for persona relevance. I want to measure whether it changes the KB and what it costs in tokens.

Step 0: inspect first, change nothing
1. Read the repo. Find the current KB-building pipeline, the extracted data, and any existing token or cost logging or summary. Tell me in a few lines what you found: entity types, fields, how prerequisites are represented, how the LLM is called now, and where token numbers come from.
2. Find or ask me for the hand-built KB, which is the gold reference. If it doesn't exist, tell me and stop.
3. Show me a plan and wait for my go-ahead before writing code. If anything I describe doesn't match the repo, say so.

Step 1: shared schema (fixed by hand)
Typed schema (pydantic or dataclasses). Each KB entity has an id, title, type, department, the required fields the data actually supports (prerequisites, syllabus topics, credits, semester), and a source URL on every fact. References such as prerequisites must be entity ids, with an explicit "unresolved" marker where the source only has free text. List any field the data lacks.

Step 2: three variants over the same extracted data and persona
- A (baseline): the pipeline exactly as it works today. Don't change its behaviour. Only add token and call logging if missing.
- B (paper-style, rules only): scope chosen by department/topic rules from config (no LLM, no ML or maths hardcoded in code, so the persona maps to rules through config). Then deterministic prerequisite closure, then the deterministic completeness check.
- C (hybrid): one LLM call that gets the persona text and a list of candidate entities as (id, title, department, short description) only. It may only choose ids from that list. Validate the output, retry once on an unknown id, then fail loudly. Output JSON with selected ids and a one-line reason each. The same closure and completeness check as B run afterwards. Keep the prompt in its own file. Use the LLM client the repo already uses, or ask me.

Record which ids came from the LLM and which were added by closure.

Step 3: completeness check (deterministic)
Print a report of entities missing required fields, unresolved references, and facts without a source URL. Flag gaps only; never fill or guess. Exit non-zero if any gap exists.

Step 4: comparison harness
One command runs A, B and C on the same input and writes a results JSON and a markdown table. Metrics, each against the hand-built KB:
- entity precision and recall
- prerequisite-edge precision and recall
- number of gaps from the completeness report
- share of facts with provenance
- input tokens, output tokens, number of LLM calls, wall time
Run each LLM variant at least 3 times and report the spread, since the LLM output is not deterministic. Do not invent numbers. Every number in the table must come from a run.

Step 5: write up
Update the results table in README.md in the Research folder with the real numbers, plus a short, honest reading: where B or C matches the gold KB, where they differ, and the token difference versus A. Say plainly if the results do not support the hypothesis that the rules-only or hybrid KB is almost the same as the baseline.

Step 6: tests
Unknown id from the LLM is rejected. Closure terminates on cycles. The checker catches a missing field. A, B and C all run on a tiny fixture.

Constraints
- Keep it small and readable. No new frameworks unless the repo already uses them.
- Explain each file in a sentence as you create it. I want to understand how it works before building further.
- Work in small steps. Show me the Step 0 plan first.
- Do not push to GitHub until I say so.

Pushing (only after I approve)
Repo: https://github.com/ps-submision-pdev/Research-principles-and-implementations. Put README.md (paper table, experiment plan, results) at the root and the code under a clear folder. If the push fails with an access error, tell me and stop.
