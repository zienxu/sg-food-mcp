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

## Integrity
- **Zero duplicate IDs across all 1,163 rows**, checked after normalisation.
- **`data/dishes_draft.csv` is kept alongside the final file** so the
  normalisation can be diffed rather than taken on trust.