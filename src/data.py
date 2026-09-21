import csv
from pathlib import Path

from rapidfuzz import fuzz

CSV = Path(__file__).resolve().parent.parent / "data" / "dishes.csv"

NUMERIC = ("kcal_default", "kcal_per_100", "protein_g", "carbs_g", "fat_g")

# Never leaves this module. Per-100g is kept in the CSV but withheld from
# callers: a model can't estimate grams from a photo, so offering both figures
# creates a ~3x error that looks identical to a right answer.
PRIVATE = ("kcal_per_100", "per100_unit", "_terms")

# Search results stay small — a model pays for every token returned.
BRIEF = ("id", "dish_name", "category", "serving_default_desc",
         "kcal_default", "input_mode")

def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def _terms(r):
    names = [r["dish_name"]] + (r.get("other_names") or "").split("|")
    return [n.strip().lower() for n in names if n.strip()]

def load():
    rows = []
    with open(CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for k in NUMERIC:
                r[k] = _to_float(r.get(k))
            r["_terms"] = _terms(r)
            rows.append(r)
    return rows

DISHES = load()
BY_ID = {d["id"]: d for d in DISHES}

def search(query, limit=10):
    q = (query or "").strip().lower()
    if not q:
        return []
    hits = []
    for d in DISHES:
        score = max(fuzz.WRatio(q, t) for t in d["_terms"])
        # A typed substring beats fuzzy distance: "kopi peng" should outrank
        # whatever WRatio thinks is close to it.
        if any(q in t for t in d["_terms"]):
            score = max(score, 95)
        if score >= 60:
            hits.append((score, d))
    hits.sort(key=lambda h: (-h[0], h[1]["dish_name"]))
    return [{k: d[k] for k in BRIEF} for _, d in hits[:limit]]

def lookup(dish_id):
    d = BY_ID.get(dish_id)
    if d is None:
        return None
    return {k: v for k, v in d.items() if k not in PRIVATE}

def categories():
    counts = {}
    for d in DISHES:
        counts[d["category"]] = counts.get(d["category"], 0) + 1
    return [{"category": c, "dish_count": n} for c, n in sorted(counts.items())]
