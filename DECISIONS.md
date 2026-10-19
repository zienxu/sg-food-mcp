# Decisions

## Data
- **Source**: Singapore Food Insights Database (HPB), via a CC0 Kaggle
  mirror. 1,163 rows, hawker subset. Verified against HPB by spot-check.
- **Nulls are `-`**, not blank. Must pass `na_values=["-", "", "NA"]`
  or every numeric column loads as text and comparisons fail silently.
- **Kept all 1,163 rows.** Considered filtering to dishes I eat; rejected.
  Hand-written columns scale with dishes I eat, not rows in the file.
  A missing dish is a worse failure than a noisy search result.

## Calories
- **Expose per-serving only.** Per-100g stays in the CSV, never returned
  by a tool. A model can't estimate grams from a photo, and offering both
  creates a decision point where a wrong pick is ~3x off and looks
  identical to a right one.
- **No derived alternative-serving figure.** Only 182/1,163 rows (16%)
  have an alternative serving, and the dataset gives no calorie value for
  it — deriving one needs regex over free text like "1 cup(s) = 450ml".
  Kept the raw text column; dropped the derivation.
- **Range comes from asking the user**, not from the data.

## Drinks
- **Drinks use a tap interface, not the camera.** The dataset has 16 kopi
  variants spanning 33 kcal (Kopi O kosong) to 240 kcal (Iced Kopi) — a
  7x spread across drinks that are visually identical. No vision model
  resolves this. Routing drinks to taps removes the largest single error
  source in the app.
- `input_mode` column encodes this: `tap` for Category == Beverages,
  `photo` otherwise.

## Search
- **`other_names` is hand-written.** No scraped dataset has aliases.
  Critical example: "peng" (Singlish for iced) appears nowhere in the
  source data but is how people actually type.

- **Aliases are pipe-separated**, not comma-separated. Dish names in the
  source contain commas ("Economic rice (1 vegetable, 2 meats)"), so a
  comma delimiter would split names in half.
- **A typed substring outranks fuzzy distance.** "kopi peng" should return
  Iced Kopi first regardless of what edit distance thinks is closest.
  `search()` floors substring matches at 95 for this reason.
- **"ckt" is a hand-written alias for char-kway-teow**, same reasoning as
  "peng": no fuzzy distance gets from an acronym to the full name.

## Server
- **Lookup logic lives in `src/data.py`, not in the server.** `search()`,
  `lookup()` and `categories()` are plain functions with no MCP dependency.
  The MCP server wraps them for stdio clients; the estimator imports them
  directly, because the Anthropic SDK's tool runner takes Python functions
  and the Messages API's MCP connector needs a URL server, not a stdio one.
  One implementation, two callers, no divergence.
- **No `print()` anywhere reachable from the server.** Stdout carries the
  JSON-RPC frames and printing to it corrupts them. The failure looks like
  the client silently failing to connect, with no useful error. Logging
  goes to stderr.
- **Tool return types are `list[dict]` / `dict[str, Any]`, never bare `dict`.**
  A bare `dict` produces no output schema, so the SDK falls back to
  unstructured text for that one tool.
- **Unknown ids raise `ToolError` with a next step** ("call search_dishes"),
  rather than returning null. A model reads the error and recovers; a null
  it has to interpret.
- **Testing uses the Inspector via npx, not `mcp dev`.** `mcp dev` wraps the
  server in `uv run --with mcp`, a fresh environment that lacks the
  project's other dependencies.
- **The smoke test uses the SDK's own stdio client, not pytest.** It spawns
  the server exactly as a client would, which is the only way to catch a
  stray print() corrupting the protocol.
- **Tool parameters are named after the fields they come from.** `lookup_dish`
  first took `dish_id` while `search_dishes` returned `id`; the model copied
  the field name it had just been handed and the call failed validation, then
  retried. A model chains tools by matching names, so a mismatch costs a
  round trip and shows the user an error.

## Integrity
- **Zero duplicate IDs across all 1,163 rows**, checked after normalisation.
- **`data/dishes_draft.csv` is kept alongside the final file** so the
  normalisation can be diffed rather than taken on trust.

## Vision backend (decided before step 5)
- Free backends only. Claude's API has no lasting free tier, so the estimator runs on Gemini's free tier (default) and a local Ollama model behind one interface (src/vision.py, chosen by VISION_BACKEND). Running both on the same photos gives a hosted-vs-open-weight comparison at $0.
- Gemini model: Gemini 3 Flash (exact id in .env). Not gemini-2.5-flash, which was retired on 16 Oct 2026. The id lives in .env because ids change fast.
- Ollama model: qwen2.5vl:7b.
- Step 5 imports search() directly instead of calling the MCP server over the protocol. It is the fastest route, and the MCP server stays the public piece.
- Portion answer to kcal: small / regular / large = x0.75 / x1.0 / x1.4 of the default serving. Assumptions, not measured; step 6 tests them.
- Confidence threshold: 0.6, set before seeing results. Any later change gets reported as tuned on the same photos.

## Estimator (step 5)
- **The installed HTTP client is `httpx2`, not `httpx`.** Both the pip package and the import name are `httpx2` in this venv — a fork/successor of httpx with an identical API. `import httpx` fails; `vision.py` does `import httpx2 as httpx`.
- **Retry is one shared `_retry_post` helper**, stdlib `time.sleep` with exponential backoff (1s/2s/4s, 3 retries), triggered only on HTTP 429 per spec. No `tenacity`/`backoff` dependency added for two call sites.
- **Both backends are asked for JSON** (Gemini: `responseMimeType`+`responseSchema`; Ollama: `format: "json"`), but `vision._normalize()` still validates and clamps every field and falls back to an empty result on anything malformed — forced-JSON mode is a reliability aid, not a parsing guarantee.
- **`estimate()` only acts on the top vision candidate.** A non-match or a tap-dish (drink) hit asks a question instead of falling through to candidate #2/#3. Revisit only if step 6's evals show this costs accuracy.
- **`load_dotenv()` lives in `src/vision.py` only** — the first (and so far only) `.env` consumer in the repo.
- **Gemini's API key goes in an `x-goog-api-key` header, not a `?key=` query param.** `httpx2` logs the full request URL at INFO; a query param would put the key in stderr on every call. Caught by a real smoke-test run against `evals/photos/001.jpg`, not by the unit tests (they stub the network boundary and never see a real URL).

## Eval (step 6)
- **Refusals count as a kcal miss, not an exclusion.** All three accuracy
  metrics (dish correct, kcal ±20%, refusal rate) share one denominator —
  the full labelled set — so a backend can't inflate its kcal accuracy by
  refusing on the hard photos. Decided before running either backend.
- **results.md is hand-rolled markdown, not `DataFrame.to_markdown()`.**
  `tabulate` isn't installed; not worth adding a dependency for one table.
- **Results: Gemini 13.0% dish-correct / 39.1% kcal ±20%, Ollama 0.0% /
  21.7%** (23 eval photos, both $0/photo, 0% refusals). Gemini is both
  faster (1.73s vs 16.71s median) and more accurate.
- **Low accuracy traces to the eval photos, not the pipeline.** Several of
  the 23 photos are dishes the database has no entry for at all — the
  model still names *something*, `search()` still fuzzy-matches it to the
  closest dish it has, and that dish's kcal sometimes lands within ±20%
  by coincidence while the dish name is wrong. Zero refusals across 46
  calls (both backends) despite this confirms `estimate()` never says "I
  don't know this dish" — it always picks a nearest match instead of a
  question, because the confidence gate (0.6) is about the vision model's
  certainty in what it saw, not about whether that dish exists in the
  1,163-row set.
- **Limitation: the HPB/Kaggle set under-covers real SG hawker food.**
  1,163 rows is a sample, not the full space of dishes a camera will see
  at a hawker centre — stalls run regional/fusion variants, plating
  differs, and some common dishes are simply missing. A bigger or
  user-extensible database would raise dish-correct further than any
  vision-side change could. Not fixed in this step; flagged for whoever
  picks up data coverage next.

## App (step 7)
- **Tap list shows only the 6 `is_favourite` rows, not all 189 `input_mode=tap`
  rows.** The full tap set (every kopi/teh variant) stays reachable through
  search_dishes via the MCP tools; `is_favourite` is a hand-curated shortlist
  for a one-screen tap UI, not the complete drinks menu.