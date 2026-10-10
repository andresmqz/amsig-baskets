"""
Amsig Basket risk analytics.

Runs after compute_index.py and reads data/prices.csv, data/index.csv and
data/weights.csv. Writes:

    data/risk.csv               per scheme and period: beta, alpha, correlation and
                                R-squared vs BTC, tracking error, information ratio
    data/correlations.json      correlation matrix of daily returns for all assets,
                                for the full history and the last 90 days, with
                                assets ordered so similar coins sit together
    data/risk_contributions.csv each asset's share of the official baskets' risk,
                                using current weights
    data/rolling.csv            90-day rolling volatility, beta and correlation vs BTC
                                for the official baskets and benchmarks

Usage:
    python compute_risk.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
CONFIG = json.loads((ROOT / "config.json").read_text())
DATA = ROOT / "data"
DAYS = 365
WINDOW = 90           # days for the "recent" correlation matrix and rolling stats
MIN_OBS = 20          # fewer daily returns than this and a regression isn't meaningful


def daily_returns(df):
    return df.pct_change(fill_method=None).dropna(how="all")


def regression(y, x):
    """Beta, annualized alpha, correlation, R-squared, tracking error, information ratio of y vs x."""
    both = pd.concat([y, x], axis=1, join="inner").dropna()
    if len(both) < MIN_OBS:
        return None
    y, x = both.iloc[:, 0], both.iloc[:, 1]
    var_x = x.var()
    beta = y.cov(x) / var_x if var_x > 0 else np.nan
    alpha_daily = y.mean() - beta * x.mean()
    corr = y.corr(x)
    excess = y - x
    te = excess.std() * np.sqrt(DAYS)
    ir = excess.mean() / excess.std() * np.sqrt(DAYS) if excess.std() > 0 else np.nan
    return {
        "observations": len(both),
        "beta_btc": round(beta, 3),
        "alpha_ann": round(alpha_daily * DAYS, 4),
        "correlation_btc": round(corr, 3),
        "r_squared": round(corr ** 2, 3),
        "tracking_error": round(te, 4),
        "information_ratio": round(ir, 2),
    }


def cluster_order(corr: pd.DataFrame):
    """Order assets so that highly correlated ones sit next to each other (greedy nearest neighbour)."""
    names = list(corr.index)
    if len(names) <= 2:
        return names
    avg = corr.where(~np.eye(len(names), dtype=bool)).mean()
    order = [avg.idxmax()]  # start from the most "central" asset
    left = set(names) - set(order)
    while left:
        last = order[-1]
        nxt = max(left, key=lambda a: corr.loc[last, a])
        order.append(nxt)
        left.remove(nxt)
    return order


def matrix_block(rets: pd.DataFrame, label):
    rets = rets.dropna(axis=1, thresh=MIN_OBS)
    corr = rets.corr()
    order = cluster_order(corr)
    corr = corr.loc[order, order]
    n = len(order)
    off = corr.values[~np.eye(n, dtype=bool)]
    eig = np.clip(np.linalg.eigvalsh(corr.values), 0, None)
    effective_bets = (eig.sum() ** 2) / (eig ** 2).sum()
    first_factor = eig.max() / eig.sum()
    return {
        "label": label,
        "start": rets.index[0].date().isoformat(),
        "end": rets.index[-1].date().isoformat(),
        "observations": int(len(rets)),
        "assets": order,
        "matrix": [[round(float(v), 3) for v in row] for row in corr.values],
        "avg_pairwise": round(float(off.mean()), 3),
        "min_pair": pair(corr, np.argmin),
        "max_pair": pair(corr, np.argmax),
        "effective_bets": round(float(effective_bets), 2),
        "first_factor_share": round(float(first_factor), 3),
        "corr_to_btc": ({a: round(float(corr.loc[a, "BTC"]), 3) for a in order if a != "BTC"}
                        if "BTC" in order else {}),
    }


def pair(corr, pick):
    vals = corr.values.copy()
    np.fill_diagonal(vals, np.nan if pick is np.argmax else np.inf)
    if pick is np.argmax:
        vals = np.where(np.isnan(vals), -np.inf, vals)
    i, j = np.unravel_index(pick(vals), vals.shape)
    return {"a": corr.index[i], "b": corr.columns[j], "value": round(float(corr.iloc[i, j]), 3)}


def risk_contributions(weights: pd.Series, rets: pd.DataFrame):
    """Share of portfolio variance from each asset: w_i (Cov w)_i / (w' Cov w)."""
    assets = [a for a in weights.index if a in rets.columns]
    w = weights[assets] / weights[assets].sum()
    cov = rets[assets].dropna().cov() * DAYS
    port_var = float(w @ cov @ w)
    marginal = cov @ w
    share = w * marginal / port_var
    return share, np.sqrt(port_var)


def main():
    prices = (pd.read_csv(DATA / "prices.csv", parse_dates=["date"])
              .pivot(index="date", columns="asset", values="price_usd").sort_index())
    index = pd.read_csv(DATA / "index.csv", parse_dates=["date"], index_col="date")
    weights = pd.read_csv(DATA / "weights.csv")
    live = CONFIG.get("live_start")
    live = pd.Timestamp(live) if live else None

    asset_rets = daily_returns(prices)
    btc = asset_rets["BTC"]
    scheme_rets = daily_returns(index)

    # 1. Regression stats vs BTC, per scheme and period
    rows = []
    for key in index.columns:
        scheme = CONFIG["schemes"].get(key, {})
        r = scheme_rets[key].dropna()
        periods = {"full": r}
        if live is not None:
            periods["backtest"] = r[r.index <= live]
            periods["live"] = r[r.index > live]
        for name, rr in periods.items():
            reg = regression(rr, btc)
            if reg:
                rows.append({"scheme": key, "group": scheme.get("group", ""), "period": name, **reg})
    pd.DataFrame(rows).to_csv(DATA / "risk.csv", index=False)

    # 2. Correlation matrices
    recent = asset_rets.iloc[-WINDOW:]
    out = {
        "window_days": WINDOW,
        "full": matrix_block(asset_rets, "Since Jan 1"),
        "recent": matrix_block(recent, f"Last {WINDOW} days"),
    }
    (DATA / "correlations.json").write_text(json.dumps(out, indent=1))

    # 3. Risk contributions for the official baskets, using today's weights
    rc_rows = []
    for key, scheme in CONFIG["schemes"].items():
        if scheme.get("group") != "official":
            continue
        w = weights[weights.scheme == key].set_index("asset")["weight"]
        if w.empty:
            continue
        for window, rets in (("full", asset_rets), ("recent", recent)):
            share, vol = risk_contributions(w, rets)
            for a in share.index:
                rc_rows.append({"scheme": key, "window": window, "asset": a,
                                "weight": round(float(w[a]), 4),
                                "risk_share": round(float(share[a]), 4),
                                "portfolio_vol": round(float(vol), 4)})
    pd.DataFrame(rc_rows).to_csv(DATA / "risk_contributions.csv", index=False)

    # 4. Rolling stats
    roll_rows = []
    keys = [k for k, s in CONFIG["schemes"].items()
            if s.get("group") in ("official", "benchmark") and k in scheme_rets]
    for key in keys:
        r = scheme_rets[key]
        vol = r.rolling(WINDOW).std() * np.sqrt(DAYS)
        cov = r.rolling(WINDOW).cov(btc)
        beta = cov / btc.rolling(WINDOW).var()
        corr = r.rolling(WINDOW).corr(btc)
        df = pd.DataFrame({"vol": vol, "beta_btc": beta, "corr_btc": corr}).dropna()
        for d, v in df.iterrows():
            roll_rows.append({"date": d.date().isoformat(), "scheme": key,
                              "vol": round(v.vol, 4), "beta_btc": round(v.beta_btc, 3),
                              "corr_btc": round(v.corr_btc, 3)})
    pd.DataFrame(roll_rows).to_csv(DATA / "rolling.csv", index=False)

    f = out["full"]
    print(f"Correlation since Jan 1: average pair {f['avg_pairwise']}, "
          f"effective independent bets {f['effective_bets']} of {len(f['assets'])}, "
          f"first factor explains {f['first_factor_share']:.0%} of variance")
    print(pd.DataFrame(rows)[lambda d: d.period == "full"][
        ["scheme", "beta_btc", "alpha_ann", "correlation_btc", "information_ratio"]].to_string(index=False))
    print("\nWrote data/risk.csv, data/correlations.json, data/risk_contributions.csv, data/rolling.csv")


if __name__ == "__main__":
    main()
