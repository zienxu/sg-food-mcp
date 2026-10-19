# Spec — sg-food-mcp

## Steps (one per session)
1. Data + search. src/data.py loads dishes.csv once; src/search.py fuzzy-matches name + other_names
   (exact/alias first). tests/test_search.py: "ckt", "kopi o kosong peng", "chicken rice", "laksa"
   each return the right dish in the top 3.
2. MCP server. server.py with search_dishes(query) -> up to 10 {id, name, serving, kcal, input_mode};
   lookup_dish(id) -> adds protein/carbs/fat, portion_note, source; list_categories() -> counts.
   Passes in `mcp dev server.py`.
3. [ME] Connect to Claude Desktop; rewrite docstrings until it picks the right tool 3 times in a row.
4. README v1: what it is, one-command install, Claude Desktop config, HPB + Kaggle credit (CC0).
5. Estimator. src/vision.py: identify_dish(image_path) -> {candidates[{name, confidence}], portion_hint}.
   Backend selected by VISION_BACKEND in .env: "gemini" (GEMINI_API_KEY) or "ollama" (local model).
   src/estimate.py: vision -> search() (direct import, same functions the MCP server exposes)
   -> {dish, kcal, confidence, assumptions, question}. Below the confidence threshold, return a
   question instead of a number. Retry with backoff on 429s.
6. Eval. evals/run.py --backend gemini|ollama scores evals/labels.csv: % dish correct,
   % kcal within +-20%, median latency, cost per photo ($0, reported honestly), refusal rate.
   Writes evals/results.md with one row per backend.
7. App. app.py (Streamlit): photo upload -> estimate; drinks via a tap list of is_favourite rows;
   today's log in session state only (no database).
8. [ME] Deploy only if abuse is handled (per-session call limit or an access code). Otherwise
   ship the repo + walkthrough video and skip the live link.
9. README final: results table, decisions and tradeoffs (from DECISIONS.md), how to run.

## Decisions (settled before step 5)
- Gemini model: Gemini 3 Flash. The exact id is copied from AI Studio into GEMINI_MODEL in .env, not hard-coded.
- Ollama model: qwen2.5vl:7b (OLLAMA_MODEL in .env).
- Portion answer -> kcal: small / regular / large = x0.75 / x1.0 / x1.4 of the default serving. These are assumptions, tested in step 6. If portion_hint is "unclear", ask the user.
- Confidence threshold: 0.6. If the top candidate's confidence is below it, return a question instead of a number.