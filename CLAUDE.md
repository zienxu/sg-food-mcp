# sg-food-mcp
Python 3.10+, MCP Python SDK v2 (`from mcp.server import MCPServer`), pandas, rapidfuzz, pytest.
Data: data/dishes.csv (derived, committed). data/raw/ is gitignored — never commit it.
Run: python server.py · Inspect: mcp dev server.py · Test: pytest
Vision: src/vision.py only. Backend chosen by VISION_BACKEND in .env (gemini | ollama).

Rules
- Read docs/spec.md first. Do ONE numbered step per request, then stop.
- Never print() to stdout in server code; use logging. Stdout carries the MCP protocol.
- Tools return per-serving kcal only, never per-100g.
- Rows with input_mode=tap (drinks) never go through photo estimation.
- The model names the dish; calories come only from dishes.csv.
- Secrets live in .env only. Never commit. Log non-obvious choices in DECISIONS.md.