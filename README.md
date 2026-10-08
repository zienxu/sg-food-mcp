# sg-food-mcp

Look up the calories in Singapore hawker food using the Health Promotion
Board's own figures, so an AI assistant answers from the official database
instead of guessing from memory.

**Status: in progress.** The lookup half works today. The photo estimator is
the next piece. This README says plainly what is and isn't built.

## The problem

Ask any AI assistant how many calories are in a plate of chicken rice and it
will give you a confident number from memory. It has no idea which of the six
kinds of chicken rice you meant, and no source for the figure it quotes.

Singapore has an official answer: HPB's Food Insights Database. This project
puts that database behind an AI assistant, so the assistant identifies the
dish and the database supplies the number. The model never states a calorie
figure of its own.

## The case that shaped the design

The database has 16 kopi variants. These five are all served in the same
400ml cup, and they are indistinguishable in a photograph:

| Drink | kcal per 400ml cup |
|---|---|
| Iced Kopi O kosong (no milk, no sugar) | 40 |
| Iced Kopi O siu dai (no milk, less sugar) | 88 |
| Iced Kopi C (evaporated milk) | 160 |
| Iced Kopi siu dai (condensed milk, less sugar) | 188 |
| Iced Kopi (condensed milk) | 240 |

Six times the calories, same photo. Across all 16 kopi rows the spread runs
from 33 to 240 kcal.

**So drinks don't go through the camera.** They get a tap menu of your usual
orders instead. The data is finer-grained than any camera can resolve, and
pretending otherwise would have made the drinks answers confidently wrong.
Finding that out early removed the single largest source of error in the app
before it was built.

## Three other decisions

- **Per-serving figures only.** The source also carries per-100g values, and
  they're withheld from the assistant. A model can't estimate grams from a
  photo, so offering both creates a choice where the wrong pick is roughly
  3x off and looks exactly as confident as the right one.
- **All 1,163 rows kept.** Trimming the database to the dishes I actually eat
  was tempting and rejected: a missing dish is a worse failure than a noisy
  search result, and the hand-written columns scale with my diet anyway, not
  with the size of the file.
- **No invented ranges.** Only 16% of rows describe a larger portion, and the
  source gives no calorie figure for it. Rather than derive one, the app will
  ask the user "regular or large?" and say which answer it used.

The full log, including the decisions that were reversed, is in
[DECISIONS.md](DECISIONS.md).

## What works today

- **1,163 dishes and drinks** from HPB, normalised into one table, with
  per-serving calories, protein, carbs and fat.
- **Search that matches how people actually type.** "kopi peng" and "cai fan"
  appear nowhere in the official data, so 30 rows carry hand-written aliases.
  Typing `kopi peng` returns Iced Kopi first.
- **Portion descriptions for the 22 dishes I eat most**, in plain language
  ("standard hawker plate, 1 bowl of rice"), written against the serving size
  HPB actually weighed.
- **A working connection to Claude.** Ask "how many calories in kopi peng?"
  and it searches the database and answers 240 kcal, citing the serving size.
- **Per-piece items handled.** Satay is 57 kcal per stick, so ten sticks is
  570. The database figure is per stick, and the assistant is told to multiply.

## What's next

1. A photo estimator: name the dish from a picture, then take the number from
   the database.
2. **A 30-photo test set, built before the estimator**, so accuracy gets
   measured rather than demoed on the pictures that happen to work.
3. A question instead of a guess when the portion is unclear.

## Run it

Needs Python 3.12.

```bash
git clone https://github.com/zienxu/sg-food-mcp.git
cd sg-food-mcp
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/smoke_test.py          # should print "smoke test passed"
```

To use it from an AI assistant, point an MCP client at `.mcp.json`; to poke
the tools directly in a browser:

```bash
npx @modelcontextprotocol/inspector .venv/bin/python src/server.py
```

## Data and licence

Singapore Food Insights Database, Health Promotion Board, via a
[CC0 mirror on Kaggle](https://www.kaggle.com/datasets/adisongoh/singapore-hawker-food-nutritional-information)
uploaded by Adison Goh. The CSV is committed to this repo so it runs with no
download step. Nutrition figures are HPB's; the aliases, portion
descriptions and code are mine.
