"""Start the real server over stdio, the way Claude does, and call every tool.

Run: .venv/bin/python scripts/smoke_test.py
A stray print() in the server makes this fail at startup.
"""
import asyncio
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

SERVER = StdioServerParameters(
    command=sys.executable,
    args=[str(Path(__file__).resolve().parent.parent / "src" / "server.py")],
)


async def main():
    async with Client(SERVER) as client:
        # server exposes exactly the three tools we expect
        tools = sorted(t.name for t in (await client.list_tools()).tools)
        assert tools == ["list_categories", "lookup_dish", "search_dishes"], tools

        # search finds the right dish and tags drinks as tap, not photo
        r = await client.call_tool("search_dishes", {"query": "kopi peng"})
        hits = r.structured_content["result"]
        assert hits[0]["dish_name"] == "Iced Kopi", hits[0]
        assert hits[0]["input_mode"] == "tap"

        # lookup returns correct kcal and never leaks the per-100 fields
        r = await client.call_tool("lookup_dish", {"dish_id": "steamed-chicken-rice"})
        row = r.structured_content
        assert row["kcal_default"] == 488, row
        assert "kcal_per_100" not in row and "per100_unit" not in row

        # unknown dish id comes back as an error, not a crash
        r = await client.call_tool("lookup_dish", {"dish_id": "not-a-dish"})
        assert r.is_error, "unknown id should be an error"

        # categories list has the expected count
        r = await client.call_tool("list_categories", {})
        assert len(r.structured_content["result"]) == 15

    print("smoke test passed: 3 tools, search, lookup, error path, categories")


asyncio.run(main())
