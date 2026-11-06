# Results (chem_data_s4, model openrouter/nvidia/nemotron-3-ultra-550b-a55b:free, temperature 0)

Mode: agreement (no gold KB: agreement is not accuracy). Records with stated prerequisites: 4 -> edge metrics: counts only (fewer than 5 records have stated prerequisites). B's two runs identical: True.

| Run | Kept options (horizon slots) | Records | Edges (explicit/model) | Closure added | Gaps | Provenance | Tokens in/out | LLM calls | Wall s |
|---|---|---|---|---|---|---|---|---|---|
| A | CS2207, CS3106, MA2206, MA3107 | 14 | 5/9 | 0 | 0  | 1.0 of 112 facts | 15279/29551 | 4 | not measured |
| B | CE3105, CS2207, MA2206, MA3107 | 14 | 5/0 | 0 | 0  | 1.0 of 19 facts | 0/0 | 0 | 0.04 |
| C1 | CS2207, CS3106, MA2206, MA3107 | 14 | 5/0 | 0 | 0  | 1.0 of 19 facts | 2097/2053 | 1 | 91.79 |
| C2 | CS2207, CS3106, MA2206, MA3107 | 14 | 5/0 | 0 | 0  | 1.0 of 19 facts | 2097/2349 | 1 | 52.58 |
| C3 | CS2207, CS3106, MA2206, MA3107 | 14 | 5/0 | 0 | 0  | 1.0 of 19 facts | 2097/2780 | 1 | 102.45 |

| Pair | Options Jaccard | Records Jaccard | Edges (left / right / shared) |
|---|---|---|---|
| A vs B | 0.6 | 0.867 | 14 / 5 / 5 |
| A vs C1 | 1.0 | 1.0 | 14 / 5 / 5 |
| A vs C2 | 1.0 | 1.0 | 14 / 5 / 5 |
| A vs C3 | 1.0 | 1.0 | 14 / 5 / 5 |
| B vs C1 | 0.6 | 0.867 | 5 / 5 / 5 |
| B vs C2 | 0.6 | 0.867 | 5 / 5 / 5 |
| B vs C3 | 0.6 | 0.867 | 5 / 5 / 5 |
| C1 vs C2 | 1.0 | 1.0 | 5 / 5 / 5 |
| C1 vs C3 | 1.0 | 1.0 | 5 / 5 / 5 |
| C2 vs C3 | 1.0 | 1.0 | 5 / 5 / 5 |
