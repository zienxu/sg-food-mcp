import estimate


def test_happy_path_returns_kcal(monkeypatch):
    monkeypatch.setattr(estimate.vision, "identify_dish", lambda path: {
        "candidates": [{"name": "char kway teow", "confidence": 0.9}], "portion_hint": "regular"})
    out = estimate.estimate("x.jpg")
    assert out["kcal"] == 989  # regular = x1.0 of kcal_default
    assert out["question"] is None


def test_low_confidence_returns_question_not_kcal(monkeypatch):
    monkeypatch.setattr(estimate.vision, "identify_dish", lambda path: {
        "candidates": [{"name": "char kway teow", "confidence": 0.3}], "portion_hint": "regular"})
    out = estimate.estimate("x.jpg")
    assert out["kcal"] is None
    assert out["question"]


def test_unclear_portion_returns_question_not_kcal(monkeypatch):
    monkeypatch.setattr(estimate.vision, "identify_dish", lambda path: {
        "candidates": [{"name": "char kway teow", "confidence": 0.9}], "portion_hint": "unclear"})
    out = estimate.estimate("x.jpg")
    assert out["kcal"] is None
    assert out["question"]


def test_tap_dish_refuses_to_estimate(monkeypatch):
    monkeypatch.setattr(estimate.vision, "identify_dish", lambda path: {
        "candidates": [{"name": "kopi o kosong", "confidence": 0.9}], "portion_hint": "regular"})
    out = estimate.estimate("x.jpg")
    assert out["kcal"] is None
    assert "drink" in out["question"]


def test_no_db_match_returns_question(monkeypatch):
    monkeypatch.setattr(estimate.vision, "identify_dish", lambda path: {
        "candidates": [{"name": "xqzxqzxqzxqz", "confidence": 0.9}], "portion_hint": "regular"})
    out = estimate.estimate("x.jpg")
    assert out["kcal"] is None
    assert out["question"]


def test_no_candidates_returns_question(monkeypatch):
    monkeypatch.setattr(estimate.vision, "identify_dish", lambda path: {
        "candidates": [], "portion_hint": "unclear"})
    out = estimate.estimate("x.jpg")
    assert out["kcal"] is None
    assert out["question"]


def test_large_portion_applies_multiplier(monkeypatch):
    monkeypatch.setattr(estimate.vision, "identify_dish", lambda path: {
        "candidates": [{"name": "char kway teow", "confidence": 0.9}], "portion_hint": "large"})
    out = estimate.estimate("x.jpg")
    assert out["kcal"] == round(989.0 * 1.4)
