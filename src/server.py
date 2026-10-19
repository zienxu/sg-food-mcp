import logging
import sys
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import Field

import data

# Stdout carries the JSON-RPC messages. Anything printed there corrupts the
# protocol, so all logging goes to stderr and this file never calls print().
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger("sg-food")

server = MCPServer(
    "sg-food",
    instructions=(
        "Nutrition data for Singapore hawker food and drinks, from the "
        "Health Promotion Board. Every figure is per serving."
    ),
)

# All four are set explicitly: unset hints fall back to the spec defaults
# (destructive, non-idempotent, open-world), which a client then displays.
READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)


@server.tool(annotations=READ_ONLY)
def search_dishes(
    query: Annotated[str, Field(description=(
        "A dish or drink name as the user wrote it. English, Singlish and "
        "hawker names all work, e.g. 'kopi peng', 'cai fan', 'char kuay teow'."
    ))],
) -> list[dict]:
    """Use this for any question about calories or nutrition of Singapore
    hawker food or drinks. Never answer such questions from memory.

    query: the dish name only, such as 'ckt' or 'kopi o kosong peng',
    not the whole question. Handles Singlish spellings and aliases.
    The kcal in each result is the complete calorie answer for one default
    serving. Do not call lookup_dish to confirm or repeat it.

    input_mode 'tap' marks a drink that cannot be identified from a photo.
    If nothing matches, tell the user the dish is not in the database.
    Do not guess a number."""
    hits = data.search(query)
    log.info("search_dishes %r -> %d hits", query, len(hits))
    return hits


@server.tool(annotations=READ_ONLY)
def lookup_dish(
    id: Annotated[str, Field(description=(
        "A dish id, copied from the 'id' field of a search_dishes result, "
        "e.g. 'steamed-chicken-rice'."
    ))],
) -> dict[str, Any]:
    """Fetch protein, carbs, fat, portion notes and source for ONE dish by id.

    Call this ONLY when the user explicitly asks for protein, carbs, fat,
    portion size or source. 
    
    Never call it for calories: calories are already in the search_dishes results, 
    so a calorie question needs no second call."""
    row = data.lookup(id)
    if row is None:
        raise ToolError(
            f"No dish with id {id!r}. Call search_dishes to find a valid id."
        )
    return row


@server.tool(annotations=READ_ONLY)
def list_categories() -> list[dict]:
    """List the food categories in the database, with a dish count for each.

    Use this when the user asks what the database covers, or when
    search_dishes returns nothing and you need to check whether that kind of
    food is included at all. Not needed before an ordinary search.
    """
    return data.categories()


if __name__ == "__main__":
    server.run()
