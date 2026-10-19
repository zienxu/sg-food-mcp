import pytest

import vision


def test_parse_gemini_response_happy():
    raw = {"candidates": [{"content": {"parts": [{"text":
        '{"candidates": [{"name": "char kway teow", "confidence": 0.92}], "portion_hint": "regular"}'
    }]}}]}
    out = vision._parse_gemini_response(raw)
    assert out == {"candidates": [{"name": "char kway teow", "confidence": 0.92}], "portion_hint": "regular"}


def test_parse_gemini_response_malformed_falls_back():
    assert vision._parse_gemini_response({}) == {"candidates": [], "portion_hint": "unclear"}


def test_parse_ollama_response_happy():
    raw = {"response": '{"candidates": [{"name": "laksa", "confidence": 0.8}], "portion_hint": "large"}'}
    out = vision._parse_ollama_response(raw)
    assert out["candidates"][0]["name"] == "laksa"


def test_parse_ollama_response_malformed_falls_back():
    assert vision._parse_ollama_response({}) == {"candidates": [], "portion_hint": "unclear"}


def test_normalize_caps_at_three_and_clamps_confidence():
    d = {"candidates": [{"name": f"x{i}", "confidence": 5} for i in range(5)], "portion_hint": "bogus"}
    out = vision._normalize(d)
    assert len(out["candidates"]) == 3
    assert out["candidates"][0]["confidence"] == 1.0  # clamped to max 1.0
    assert out["portion_hint"] == "unclear"  # invalid enum falls back


class _FakeResp:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise vision.httpx.HTTPStatusError("err", request=None, response=self)

    def json(self):
        return self._body


def test_retry_post_retries_on_429_then_succeeds(monkeypatch):
    queue = [_FakeResp(429), _FakeResp(429), _FakeResp(200, {"ok": True})]
    sleeps = []
    monkeypatch.setattr(vision.time, "sleep", lambda s: sleeps.append(s))
    resp = vision._retry_post(lambda: queue.pop(0))
    assert resp.json() == {"ok": True}
    assert sleeps == [1, 2]  # exponential backoff, two retries before success


def test_retry_post_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setattr(vision.time, "sleep", lambda s: None)
    with pytest.raises(vision.httpx.HTTPStatusError):
        vision._retry_post(lambda: _FakeResp(429), max_retries=2)


def test_identify_dish_dispatches_to_gemini(monkeypatch):
    monkeypatch.setenv("VISION_BACKEND", "gemini")
    monkeypatch.setattr(vision, "_call_gemini", lambda path: {"candidates": [{"content": {"parts": [
        {"text": '{"candidates":[],"portion_hint":"unclear"}'}]}}]})
    assert vision.identify_dish("x.jpg") == {"candidates": [], "portion_hint": "unclear"}


def test_identify_dish_dispatches_to_ollama(monkeypatch):
    monkeypatch.setenv("VISION_BACKEND", "ollama")
    monkeypatch.setattr(vision, "_call_ollama", lambda path: {"response": '{"candidates":[],"portion_hint":"unclear"}'})
    assert vision.identify_dish("x.jpg") == {"candidates": [], "portion_hint": "unclear"}


def test_identify_dish_unknown_backend_raises(monkeypatch):
    monkeypatch.setenv("VISION_BACKEND", "bogus")
    with pytest.raises(ValueError):
        vision.identify_dish("x.jpg")
