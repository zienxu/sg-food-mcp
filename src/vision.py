import base64, json, logging, mimetypes, os, sys, time
from pathlib import Path

import httpx2 as httpx
from dotenv import load_dotenv

load_dotenv()

# Stdout carries the MCP protocol for server.py; keep the convention here too.
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger("sg-food.vision")

PROMPT = (
    "You are looking at a photo of food, likely Singapore hawker food or a drink. "
    "Identify the dish and how much is in the photo.\n\n"
    "Respond with ONLY this JSON, no other text:\n"
    '{"candidates": [{"name": "<dish name>", "confidence": <0-1 float>}], '
    '"portion_hint": "<small|regular|large|unclear>"}\n\n'
    "Rules:\n"
    "- List at most 3 candidates, most likely first.\n"
    "- confidence is your probability this candidate is correct, from 0 to 1.\n"
    "- portion_hint is the serving size shown relative to a normal hawker-stall "
    "serving: \"small\", \"regular\", \"large\", or \"unclear\" if you can't tell.\n"
    "- Name the dish the way a Singaporean hawker menu would (e.g. "
    "\"char kway teow\", \"kopi o kosong\"), not a generic description."
)


def _retry_post(post_fn, max_retries=3):
    # Only HTTP 429 retries (per spec); any other status raises immediately.
    for attempt in range(max_retries + 1):
        resp = post_fn()
        if resp.status_code == 429 and attempt < max_retries:
            wait = 2 ** attempt
            log.info("429 from vision backend, retrying in %ds", wait)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp


def _call_gemini(image_path):
    model = os.environ["GEMINI_MODEL"]
    api_key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    mime = mimetypes.guess_type(image_path)[0] or "image/jpeg"
    b64 = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")
    body = {
        "contents": [{"parts": [
            {"text": PROMPT},
            {"inlineData": {"mimeType": mime, "data": b64}},
        ]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "candidates": {"type": "ARRAY", "items": {
                        "type": "OBJECT",
                        "properties": {"name": {"type": "STRING"}, "confidence": {"type": "NUMBER"}},
                        "required": ["name", "confidence"],
                    }},
                    "portion_hint": {"type": "STRING", "enum": ["small", "regular", "large", "unclear"]},
                },
                "required": ["candidates", "portion_hint"],
            },
        },
    }
    # Header, not a ?key= query param: httpx2 logs the request URL at INFO,
    # and a query param would put the key in that log line.
    headers = {"x-goog-api-key": api_key}
    resp = _retry_post(lambda: httpx.post(url, headers=headers, json=body, timeout=30))
    return resp.json()


def _call_ollama(image_path):
    model = os.environ["OLLAMA_MODEL"]
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    b64 = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")
    body = {"model": model, "prompt": PROMPT, "images": [b64], "format": "json", "stream": False}
    resp = _retry_post(lambda: httpx.post(f"{host}/api/generate", json=body, timeout=60))
    return resp.json()


def _normalize(d):
    out = []
    for c in (d.get("candidates") or [])[:3]:
        name = str(c.get("name", "")).strip()
        try:
            conf = float(c.get("confidence", 0))
        except (TypeError, ValueError):
            conf = 0.0
        if name:
            out.append({"name": name, "confidence": max(0.0, min(1.0, conf))})
    out.sort(key=lambda c: -c["confidence"])
    portion = d.get("portion_hint")
    if portion not in ("small", "regular", "large", "unclear"):
        portion = "unclear"
    return {"candidates": out, "portion_hint": portion}


def _parse_gemini_response(raw):
    try:
        text = raw["candidates"][0]["content"]["parts"][0]["text"]
        return _normalize(json.loads(text))
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
        log.info("could not parse gemini response: %s", e)
        return {"candidates": [], "portion_hint": "unclear"}


def _parse_ollama_response(raw):
    try:
        return _normalize(json.loads(raw.get("response", "")))
    except (TypeError, json.JSONDecodeError) as e:
        log.info("could not parse ollama response: %s", e)
        return {"candidates": [], "portion_hint": "unclear"}


def identify_dish(image_path):
    backend = os.environ.get("VISION_BACKEND", "gemini")
    if backend == "gemini":
        return _parse_gemini_response(_call_gemini(image_path))
    if backend == "ollama":
        return _parse_ollama_response(_call_ollama(image_path))
    raise ValueError(f"Unknown VISION_BACKEND: {backend!r}")
