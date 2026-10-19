import logging, sys

import data
import vision

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger("sg-food.estimate")

CONFIDENCE_THRESHOLD = 0.6
PORTION_MULTIPLIER = {"small": 0.75, "regular": 1.0, "large": 1.4}


def _result(dish=None, kcal=None, confidence=None, assumptions=None, question=None):
    return {"dish": dish, "kcal": kcal, "confidence": confidence,
            "assumptions": assumptions or [], "question": question}


def estimate(image_path):
    vr = vision.identify_dish(image_path)
    candidates = vr.get("candidates") or []
    if not candidates:
        return _result(question="I couldn't identify a dish in that photo. Can you describe it?")

    top = candidates[0]
    name, confidence = top["name"], top["confidence"]

    if confidence < CONFIDENCE_THRESHOLD:
        return _result(dish=name, confidence=confidence,
                        question=f"I'm not confident this is {name}. Can you confirm or tell me what it is?")

    hits = data.search(name, limit=1)
    if not hits:
        return _result(dish=name, confidence=confidence,
                        question=f"I couldn't find '{name}' in the database. Can you describe it differently?")

    dish = hits[0]
    if dish["input_mode"] == "tap":
        return _result(dish=dish["dish_name"], confidence=confidence,
                        question=f"{dish['dish_name']} is a drink — use the tap list instead of a photo.")

    portion = vr.get("portion_hint", "unclear")
    if portion not in PORTION_MULTIPLIER:
        return _result(dish=dish["dish_name"], confidence=confidence,
                        question=f"Is this a small, regular, or large portion of {dish['dish_name']}?")

    multiplier = PORTION_MULTIPLIER[portion]
    kcal = round(dish["kcal_default"] * multiplier)
    return _result(
        dish=dish["dish_name"], kcal=kcal, confidence=confidence,
        assumptions=[f"{portion} portion = x{multiplier} of the default serving ({dish['kcal_default']} kcal)"],
    )
