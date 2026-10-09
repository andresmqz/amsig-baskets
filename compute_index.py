"""
Amsig Basket index calculator.

Reads data/prices.csv and config.json, builds an index (base 100) for every
scheme in the config, and writes:

    data/index.csv     one column per scheme, one row per day
    data/summary.csv   return, volatility, drawdown, Sharpe, vs BTC, per period
    data/weights.csv   each scheme's current (drifted) weights on the last day

Periods: "full" covers everything. Once live_start is set in config.json,
"backtest" covers the days before it and "live" covers the days from it on.

Usage:
    python compute_index.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
CONFIG = json.loads((ROOT / "config.json").read_text())
DATA = ROOT / "data"
DAYS_PER_YEAR = 365  # crypto trades every day


def load_prices():
    df = pd.read_csv(DATA / "prices.csv", parse_dates=["date"])
    prices = df.pivot(index="date", columns="asset", values="price_usd").sort_index()
    caps = df.pivot(index="date", columns="asset", values="market_cap_usd").sort_index()
    return prices, caps


def capped(weights: pd.Series, cap: float) -> pd.Series:
    """Cap each weight and spread the excess over the uncapped names, repeating until none exceed the cap."""
    w = weights / weights.sum()
    if cap * len(w) < 1:
        return pd.Series(1 / len(w), index=w.index)
    for _ in range(100):
        over = w > cap + 1e-12
        if not over.any():
            break
        excess = (w[over] - cap).sum()
        w[over] = cap
        under = ~over & (w < cap)
        w[under] += excess * w[under] / w[under].sum()
    return w


def target_weights(scheme, assets, caps_row):
    kind = scheme["weighting"]
    if kind == "equal":
        return pd.Series(1 / len(assets), index=assets)
    if kind == "custom":
        w = pd.Series({a: float(scheme["weights"][a]) for a in assets})
        return w / w.sum()
    if kind == "mcap":
        w = caps_row[assets].astype(float)
        if w.isna().any() or (w <= 0).any():
            missing = list(w[w.isna() | (w <= 0)].index)
            raise ValueError(f"missing market cap for {missing} on {caps_row.name.date()}")
        return capped(w, scheme.get("cap", 1.0))
    raise ValueError(f"unknown weighting {kind}")


def rebalance_dates(index, rule):
    if rule == "none":
        return set()
    s = pd.Series(index, index=index)
    if rule == "monthly":
        firsts = s.groupby([index.year, index.month]).min()
    elif rule == "quarterly":
        firsts = s.groupby([index.year, index.quarter]).min()
    else:
        raise ValueError(f"unknown rebalance rule {rule}")
    return set(firsts.iloc[1:])  # the first period is the launch, not a rebalance


def build(scheme, prices, caps, start):
    assets = scheme["assets"]
    px = prices[assets]
    first_full = px.dropna().index.min()
    if pd.isna(first_full):
        raise ValueError("no date where every asset has a price")
    begin = max(start, first_full)
    px = px.loc[begin:].ffill()
    gaps = int(prices.loc[begin:, assets].isna().sum().sum())

    base = CONFIG["base_value"]
    rebal = rebalance_dates(px.index, scheme["rebalance"])
    units = target_weights(scheme, assets, caps.loc[begin]) * base / px.iloc[0]
    levels = []
    for d, row in px.iterrows():
        value = float((units * row).sum())
        if d in rebal:
            units = target_weights(scheme, assets, caps.loc[d]) * value / row
        levels.append(value)
    series = pd.Series(levels, index=px.index)
    drifted = units * px.iloc[-1]
    return series, drifted / drifted.sum(), begin, gaps


def stats(series, btc):
    if len(series) < 2:
        return {}
    rets = series.pct_change().dropna()
    total = series.iloc[-1] / series.iloc[0] - 1
    vol = rets.std() * np.sqrt(DAYS_PER_YEAR)
    sharpe = rets.mean() / rets.std() * np.sqrt(DAYS_PER_YEAR) if rets.std() > 0 else np.nan
    dd = (series / series.cummax() - 1).min()
    b = btc.reindex(series.index).dropna()
    btc_total = b.iloc[-1] / b.iloc[0] - 1 if len(b) > 1 else np.nan
    return {
        "start": series.index[0].date(),
        "end": series.index[-1].date(),
        "days": len(series) - 1,
        "total_return": round(total, 4),
        "btc_return_same_window": round(btc_total, 4),
        "excess_vs_btc": round(total - btc_total, 4),
        "ann_volatility": round(vol, 4),
        "sharpe_rf0": round(sharpe, 2),
        "max_drawdown": round(dd, 4),
    }


def main():
    prices, caps = load_prices()
    start = pd.Timestamp(CONFIG["backfill_start"])
    live = CONFIG.get("live_start")
    live = pd.Timestamp(live) if live else None

    print("Coverage (first date with a price):")
    for a in CONFIG["assets"]:
        if a in prices:
            print(f"  {a:6} {prices[a].first_valid_index().date()}")
        else:
            print(f"  {a:6} NO DATA")

    indices, weights, rows = {}, [], []
    for key, scheme in CONFIG["schemes"].items():
        try:
            series, drifted, begin, gaps = build(scheme, prices, caps, start)
        except Exception as e:
            print(f"! {key}: skipped ({e})")
            continue
        if begin > start:
            print(f"! {key}: starts {begin.date()}, not {start.date()}, because an asset has no earlier data")
        if gaps:
            print(f"! {key}: {gaps} missing daily prices were carried forward")
        indices[key] = series
        for a, w in drifted.items():
            weights.append({"scheme": key, "asset": a, "weight": round(w, 4)})

    btc = prices["BTC"].dropna() if "BTC" in prices else pd.Series(dtype=float)
    for key, series in indices.items():
        scheme = CONFIG["schemes"][key]
        periods = {"full": series}
        if live is not None:
            periods["backtest"] = series[series.index <= live]
            periods["live"] = series[series.index >= live]
        for name, s in periods.items():
            st = stats(s, btc)
            if st:
                rows.append({"scheme": key, "label": scheme["label"], "group": scheme["group"],
                             "period": name, **st})

    pd.DataFrame(indices).round(4).to_csv(DATA / "index.csv", index_label="date")
    summary = pd.DataFrame(rows)
    summary.to_csv(DATA / "summary.csv", index=False)
    pd.DataFrame(weights).to_csv(DATA / "weights.csv", index=False)

    view = summary[summary.period == "full"][
        ["label", "total_return", "excess_vs_btc", "ann_volatility", "sharpe_rf0", "max_drawdown"]]
    print("\nFull period:")
    print(view.to_string(index=False))
    print("\nWrote data/index.csv, data/summary.csv, data/weights.csv")


if __name__ == "__main__":
    main()
