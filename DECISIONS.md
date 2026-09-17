# Decisions

## Data
- **Source**: Singapore Food Insights Database (HPB), via a CC0 Kaggle
  mirror. 1,163 rows, hawker subset. Verified against HPB by spot-check.
- **Nulls are `-`**, not blank. Must pass `na_values=["-", "", "NA"]`
  or every numeric column loads as text and comparisons fail silently.
- **Kept all 1,163 rows.** Considered filtering to dishes I eat; rejected.
  Hand-written columns scale with dishes I eat, not rows in the file.
  A missing dish is a worse failure than a noisy search result.

## Calories
- **Expose per-serving only.** Per-100g stays in the CSV, never returned
  by a tool. A model can't estimate grams from a photo, and offering both
  creates a decision point where a wrong pick is ~3x off and looks
  identical to a right one.
- **No derived alternative-serving figure.** Only 182/1,163 rows (16%)
  have an alternative serving, and the dataset gives no calorie value for
  it — deriving one needs regex over free text like "1 cup(s) = 450ml".
  Kept the raw text column; dropped the derivation.
- **Range comes from asking the user**, not from the data.

## Drinks
- **Drinks use a tap interface, not the camera.** The dataset has 16 kopi
  variants spanning 33 kcal (Kopi O kosong) to 240 kcal (Iced Kopi) — a
  7x spread across drinks that are visually identical. No vision model
  resolves this. Routing drinks to taps removes the largest single error
  source in the app.
- `input_mode` column encodes this: `tap` for Category == Beverages,
  `photo` otherwise.

## Search
- **`other_names` is hand-written.** No scraped dataset has aliases.
  Critical example: "peng" (Singlish for iced) appears nowhere in the
  source data but is how people actually type.

There were zero duplicate IDs across 1,163 rows, and that you kept the draft alongside the final