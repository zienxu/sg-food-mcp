import run


def test_summarize_counts_refusal_as_kcal_miss():
    rows = [
        {"latency": 1.0, "dish_ok": True, "kcal_ok": True, "refused": False},
        {"latency": 2.0, "dish_ok": False, "kcal_ok": False, "refused": True},
    ]
    m = run._summarize("gemini", rows)
    assert m["n"] == 2
    assert m["dish_correct_n"] == 1
    assert m["kcal_ok_n"] == 1
    assert m["refused_n"] == 1
    assert m["median_latency_s"] == 1.5


def test_score_backend_flags_refusal_as_miss(monkeypatch):
    monkeypatch.setattr(run.estimate, "estimate", lambda path: {
        "dish": None, "kcal": None, "confidence": None,
        "assumptions": [], "question": "huh?"})
    m = run.score_backend("gemini", [("x.jpg", "ban-mian-dry", 676.0)])
    assert m["dish_correct_n"] == 0
    assert m["kcal_ok_n"] == 0
    assert m["refused_n"] == 1


def test_merge_replaces_only_matching_backend_row(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "RESULTS", tmp_path / "results.md")
    base = {"n": 1, "dish_correct_n": 1, "kcal_ok_n": 1, "refused_n": 0,
            "median_latency_s": 1.0, "cost_per_photo": 0.0}
    run.merge_and_write({**base, "backend": "gemini"})
    run.merge_and_write({**base, "backend": "ollama", "refused_n": 1, "kcal_ok_n": 0})
    run.merge_and_write({**base, "backend": "gemini", "n": 2, "dish_correct_n": 2})

    text = (tmp_path / "results.md").read_text()
    assert text.count("| gemini |") == 1
    assert text.count("| ollama |") == 1
    assert "2/2" in text
