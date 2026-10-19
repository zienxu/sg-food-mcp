"""Score a vision backend against evals/labels.csv.

Run: .venv/bin/python evals/run.py --backend gemini|ollama
Writes/updates evals/results.md with one row per backend.
"""
import argparse
import csv
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import data
import estimate

LABELS = ROOT / "evals" / "labels.csv"
PHOTOS = ROOT / "evals" / "photos"
RESULTS = ROOT / "evals" / "results.md"
GEMINI_THROTTLE_S = 4  # shortcut: fixed delay to stay under the free-tier rate limit; raise if it still 429s
HEADER = "| Backend | Dish correct | Kcal within ±20% | Median latency | Cost/photo | Refusal rate |"
SEP = "| --- | --- | --- | --- | --- | --- |"


def read_labels() -> list[tuple[str, str, float]]:
    with open(LABELS, newline="") as f:
        return [(row["filename"], row["dish"], float(row["kcal_truth"])) for row in csv.DictReader(f)]


def score_backend(backend: str, labels: list[tuple[str, str, float]]) -> dict:
    os.environ["VISION_BACKEND"] = backend
    rows = []
    for filename, dish_id, kcal_truth in labels:
        t0 = time.monotonic()
        out = estimate.estimate(str(PHOTOS / filename))
        latency = time.monotonic() - t0
        expected = data.BY_ID[dish_id]["dish_name"]
        dish_ok = (out["dish"] or "").strip().lower() == expected.strip().lower()
        kcal_ok = out["kcal"] is not None and kcal_truth > 0 and abs(out["kcal"] - kcal_truth) <= 0.2 * kcal_truth
        refused = out["question"] is not None
        print(f"  {filename}: dish_ok={dish_ok} kcal_ok={kcal_ok} refused={refused} ({latency:.1f}s)")
        rows.append({"latency": latency, "dish_ok": dish_ok, "kcal_ok": kcal_ok, "refused": refused})
        if backend == "gemini":
            time.sleep(GEMINI_THROTTLE_S)
    return _summarize(backend, rows)


def _summarize(backend: str, rows: list[dict]) -> dict:
    n = len(rows)
    return {
        "backend": backend,
        "n": n,
        "dish_correct_n": sum(r["dish_ok"] for r in rows),
        "kcal_ok_n": sum(r["kcal_ok"] for r in rows),
        "refused_n": sum(r["refused"] for r in rows),
        "median_latency_s": statistics.median(r["latency"] for r in rows) if rows else 0.0,
        "cost_per_photo": 0.0,
    }


def format_row(m: dict) -> str:
    def pct(count, n):
        return f"{100 * count / n:.1f}% ({count}/{n})" if n else "n/a"

    return (
        f"| {m['backend']} | {pct(m['dish_correct_n'], m['n'])} | {pct(m['kcal_ok_n'], m['n'])} | "
        f"{m['median_latency_s']:.2f}s | ${m['cost_per_photo']:.2f} | {pct(m['refused_n'], m['n'])} |"
    )


def merge_and_write(metrics: dict) -> None:
    existing = {}
    if RESULTS.exists():
        for line in RESULTS.read_text().splitlines():
            if line.startswith("|") and line not in (HEADER, SEP) and not line.startswith("| ---"):
                existing[line.split("|")[1].strip()] = line
    existing[metrics["backend"]] = format_row(metrics)
    RESULTS.write_text("\n".join([HEADER, SEP] + list(existing.values())) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True, choices=["gemini", "ollama"])
    args = parser.parse_args()
    metrics = score_backend(args.backend, read_labels())
    merge_and_write(metrics)
    print(format_row(metrics))
    print(f"wrote {RESULTS}")


if __name__ == "__main__":
    main()
