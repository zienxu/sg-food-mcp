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

READ_ONLY = ToolAnnotations(read_only_hint=True)


@server.tool(annotations=READ_ONLY)
def search_dishes(
    query: Annotated[str, Field(description=(
        "A dish or drink name as the user wrote it. English, Singlish and "
        "hawker names all work, e.g. 'kopi peng', 'cai fan', 'char kuay teow'."
    ))],
) -> list[dict]:
    """Find Singapore hawker dishes and drinks by name. Call this first for
    any food or drink the user mentions; you need its id for lookup_dish.

    Returns up to 10 matches, best first, each with per-serving kcal and the
    serving size. Serving sizes vary: some rows are one plate, others one
    stick or one piece, so check serving_default_desc before comparing.

    Several variants often match (there are 6 kinds of chicken rice). Ask the
    user which one, or choose using the dish names. Never average variants.

    input_mode 'tap' marks drinks; ask the user which drink rather than
    guessing from a description.
    """
    hits = data.search(query)
    log.info("search_dishes %r -> %d hits", query, len(hits))
    return hits


@server.tool(annotations=READ_ONLY)
def lookup_dish(
    dish_id: Annotated[str, Field(description=(
        "The id of a dish, exactly as returned by search_dishes, "
        "e.g. 'steamed-chicken-rice'."
    ))],
) -> dict[str, Any]:
    """Get full per-serving nutrition for one dish: kcal, protein, carbs,
    fat, serving size, and portion_note describing what one serving looks
    like.

    Only pass an id returned by search_dishes. Never construct or guess one.

    For rows served by the piece, stick or scoop (satay, siew mai, waffles),
    the figures are for ONE unit. Multiply by the number the user ate.
    """
    row = data.lookup(dish_id)
    if row is None:
        raise ToolError(
            f"No dish with id {dish_id!r}. Call search_dishes to find a valid id."
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
