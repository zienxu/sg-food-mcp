# sg-food-mcp

An MCP server exposing Singapore hawker food nutrition (HPB data, CC0), plus a
photo-to-calories estimator built on top of it. Design rationale lives in
DECISIONS.md — read it before proposing changes to the data model.

## Environment

- **Use `.venv`** (Python 3.12.7). It has `mcp`, `rapidfuzz`, `pandas`.
  `.venv-1` and `.venv-2` are abandoned empty shells — ignore them, and don't
  install into them. If Pylance reports `rapidfuzz` unresolved, the VS Code
  interpreter is pointed at the wrong one.
- Run things as `.venv/bin/python ...`, not bare `python3`.

## Hard rules

- **Never `print()` anywhere reachable from the MCP server.** Stdout carries the
  JSON-RPC frames; writing to it corrupts them. The failure mode is the client
  silently failing to connect with no useful error. Use `logging` to stderr.
- **Never return `kcal_per_100` or `per100_unit` from a tool.** They stay in the
  CSV and are stripped in `data.lookup()`. See DECISIONS.md → Calories.
- **`data/dishes.csv` is committed on purpose.** The source is CC0. Don't add it
  to `.gitignore` or replace it with a download step — a stranger must be able to
  clone and run.
- **Read the CSV with `na_values=["-", "", "NA"]`** if you use pandas. Nulls in
  the source are `-`, not blank; without this every numeric column loads as text
  and comparisons fail silently. `src/data.py` uses stdlib `csv` and handles this
  in `_to_float`.
- **Aliases in `other_names` are pipe-separated** (`milo peng|milo ice`), not
  comma-separated. Commas appear inside dish names.

## Layout

- `src/data.py` — loads the CSV and owns `search()`, `lookup()`, `categories()`.
  Plain functions with no MCP dependency, **by design**: the MCP server wraps
  them for stdio clients, and the estimator imports them directly (the Anthropic
  SDK's tool runner speaks Python functions, not MCP). Put new lookup logic here,
  not in the server.
- `src/server.py` — the MCP server. Thin wrappers over `data.py`, stdio only.
  Built on SDK v2's `MCPServer`; v1 tutorials using `FastMCP` fail on import.
- `scripts/smoke_test.py` — starts the real server over stdio and calls every
  tool. Run it after any change to `server.py` or `data.py`.
- `data/dishes.csv` — 1,163 rows, normalised schema. `data/raw/food_db.csv` is
  the untouched source; `data/dishes_draft.csv` is kept for diffing.
- `notebooks/`, `scripts/peek.py` — one-off exploration, unlike
  `scripts/smoke_test.py`, which is part of the workflow.

## Running

- Smoke test: `.venv/bin/python scripts/smoke_test.py`
- Inspector: `npx @modelcontextprotocol/inspector .venv/bin/python src/server.py`
  Never `mcp dev` — it runs the server in a fresh uv environment without
  rapidfuzz, so the import fails.

## Conventions

- Tool descriptions are prompts. When a model picks the wrong tool, rewrite the
  description before debugging the code.
- Keep tool outputs small — `search()` returns the `BRIEF` field subset for this
  reason. Don't widen it without a reason.
- `input_mode` is `tap` for beverages and `photo` otherwise. Anything that routes
  a drink through the camera is a bug (DECISIONS.md → Drinks).
