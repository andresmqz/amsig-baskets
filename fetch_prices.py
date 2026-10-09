"""
Amsig Basket price fetcher.

Pulls daily USD prices and market caps from CoinGecko and appends them to
data/prices.csv. The file is append-only: a (date, asset) row that already
exists is never changed, so history can't be edited after the fact.

Usage:
    python fetch_prices.py check      # confirm every CoinGecko id resolves to the right coin
    python fetch_prices.py backfill   # first run: fetch everything since backfill_start
    python fetch_prices.py update     # daily run: fetch only the missing days

Both backfill and update do the same thing (fill whatever is missing), so
running update on an empty file also works.

Optional: set COINGECKO_API_KEY to a free Demo key for higher rate limits.
"""

import csv
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).parent
CONFIG = json.loads((ROOT / "config.json").read_text())
PRICES = ROOT / "data" / "prices.csv"
FIELDS = ["date", "asset", "price_usd", "market_cap_usd"]

API = "https://api.coingecko.com/api/v3"
KEY = os.environ.get("COINGECKO_API_KEY")
HEADERS = {"accept": "application/json"}
if KEY:
    HEADERS["x-cg-demo-api-key"] = KEY
PAUSE = 2.5 if KEY else 6.0  # seconds between calls, keyless limits are tight


def get(path, params=None, tries=5):
    for attempt in range(tries):
        r = requests.get(f"{API}{path}", params=params, headers=HEADERS, timeout=30)
        if r.status_code == 429:
            wait = 30 * (attempt + 1)
            print(f"  rate limited, waiting {wait}s")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"Gave up on {path} after {tries} tries")


def today_utc():
    return datetime.now(timezone.utc).date()


def load_existing():
    if not PRICES.exists():
        return {}
    seen = {}
    with PRICES.open() as f:
        for row in csv.DictReader(f):
            seen[(row["date"], row["asset"])] = row
    return seen


def last_date_per_asset(existing):
    last = {}
    for (d, a) in existing:
        if a not in last or d > last[a]:
            last[a] = d
    return last


def fetch_daily(cg_id, start: date):
    """Daily points from start up to yesterday (UTC). Today's point is a live price, so it's dropped."""
    days = (today_utc() - start).days + 2
    data = get(f"/coins/{cg_id}/market_chart",
               {"vs_currency": "usd", "days": days, "interval": "daily"})
    caps = {int(ts): v for ts, v in data.get("market_caps", [])}
    out = {}
    for ts, price in data.get("prices", []):
        ts = int(ts)
        d = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date()
        if d < start or d >= today_utc():
            continue
        if d.isoformat() in out:  # keep the first (00:00 UTC) point of each day
            continue
        out[d.isoformat()] = (price, caps.get(ts))
    return out


def fill():
    start_default = date.fromisoformat(CONFIG["backfill_start"])
    existing = load_existing()
    last = last_date_per_asset(existing)
    new_rows = []

    for ticker, meta in CONFIG["assets"].items():
        start = start_default
        if ticker in last:
            start = date.fromisoformat(last[ticker]) + timedelta(days=1)
        if start >= today_utc():
            print(f"{ticker:6} up to date")
            continue
        print(f"{ticker:6} fetching from {start}")
        points = fetch_daily(meta["coingecko_id"], start)
        added = 0
        for d, (price, cap) in sorted(points.items()):
            if (d, ticker) in existing:
                continue
            new_rows.append({"date": d, "asset": ticker, "price_usd": price,
                             "market_cap_usd": "" if cap is None else cap})
            added += 1
        first = min(points) if points else "none"
        print(f"       +{added} rows (first available: {first})")
        time.sleep(PAUSE)

    if not new_rows:
        print("Nothing new.")
        return

    PRICES.parent.mkdir(exist_ok=True)
    write_header = not PRICES.exists()
    with PRICES.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        new_rows.sort(key=lambda r: (r["date"], r["asset"]))
        w.writerows(new_rows)
    print(f"Appended {len(new_rows)} rows to {PRICES.relative_to(ROOT)}")


def check():
    print("Checking CoinGecko ids. Confirm each name and symbol is the coin you mean.\n")
    for ticker, meta in CONFIG["assets"].items():
        try:
            c = get(f"/coins/{meta['coingecko_id']}",
                    {"localization": "false", "tickers": "false", "community_data": "false",
                     "developer_data": "false", "market_data": "false"})
            print(f"{ticker:6} -> {c['name']} ({c['symbol'].upper()})   id={meta['coingecko_id']}")
        except Exception as e:
            print(f"{ticker:6} -> FAILED for id={meta['coingecko_id']}: {e}")
        time.sleep(PAUSE)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "update"
    if cmd == "check":
        check()
    elif cmd in ("backfill", "update"):
        fill()
    else:
        sys.exit(__doc__)
