# Amsig Basket

A paper model portfolio tracking a basket of long-term crypto convictions, with fixed rules and an append-only price history. The rules are in [METHODOLOGY.md](METHODOLOGY.md).

## First run

```
pip install -r requirements.txt
python fetch_prices.py check      # make sure every id points at the right coin
python fetch_prices.py backfill   # fetches daily prices since 2026-01-01 (takes a few minutes)
python compute_index.py           # builds the index for every scheme
```

`check` matters most for CC (`canton`) and SYRUP (`syrup`). If either id is wrong, find the right one in the URL of the coin's CoinGecko page and update `config.json`.

The backfill is slow without an API key because of CoinGecko's rate limits. A free Demo key from coingecko.com speeds it up: `export COINGECKO_API_KEY=...` before running.

## Publishing order

1. Commit `METHODOLOGY.md` and `config.json` first, before running the backfill. That commit's timestamp is the proof the basket wasn't chosen by looking at the chart.
2. Set `live_start` in `config.json` to that commit's date and commit again.
3. Run the backfill and commit `data/`.
4. Add the `COINGECKO_API_KEY` secret in the repo settings (optional) and the daily job takes over from there.

## Files

| File | What it is |
|---|---|
| `config.json` | assets, CoinGecko ids, and every weighting scheme |
| `fetch_prices.py` | fetches prices and appends to `data/prices.csv`; never edits existing rows |
| `compute_index.py` | builds `data/index.csv`, `data/summary.csv`, `data/weights.csv` |
| `.github/workflows/daily.yml` | runs both scripts every day at 01:12 UTC and commits the data |

## Trying other weightings

Add a scheme to `config.json` under `schemes` and rerun `compute_index.py`. Options:

- `"weighting"`: `"equal"`, `"custom"` (give `"weights"`, any numbers, they get normalised), or `"mcap"` (optional `"cap"`, e.g. `0.25`)
- `"rebalance"`: `"none"`, `"monthly"` or `"quarterly"`
- `"group"`: `"official"`, `"benchmark"` or `"lab"`

Lab schemes are free to change. The two official schemes should not change after the rules are published, except through the change log.

## Not built yet

Removing an asset under the exit rules (sell to cash) isn't automated. When the first removal happens, it needs a small addition to `compute_index.py`.
