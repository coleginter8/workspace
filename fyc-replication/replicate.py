"""Replicate Gürkaynak, Sack & Wright (2006) — FEDS 200628.

Because public CUSIP-level Treasury bond price data does not exist, this is a
*self-consistency simulation*:

  1. Load the CUSIP master for nominal Treasury notes/bonds from the U.S.
     Treasury Fiscal Data API (public, covers 1979-11-15 onward).
  2. For each trading day, identify the eligible bond universe per the paper's
     rules (no bills, TIPS, FRNs, callables; off-the-run; >=3 months to
     maturity; no 20-yr from 1996).
  3. Use the Fed's own published Svensson parameters for that date to compute
     the model-implied clean price of each eligible bond, optionally with
     Gaussian price noise.
  4. Fit Svensson back to those simulated prices via duration-weighted
     nonlinear least squares.
  5. Write the recovered parameters and derived yields/forwards/par-yields in
     the Fed's CSV schema, so they can be diffed against the official file by
     evaluate_replication.py.

This tests the full estimation pipeline end-to-end (bond pricing, cash-flow
schedule, NLS, Svensson math). It does *not* test the raw-data step, since
prices are simulated rather than observed.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import least_squares


CUSIP_CACHE = ".cache/cusip_master.csv"
FISCAL_API = ("https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
              "/v1/accounting/od/auctions_query")
USER_AGENT = "Mozilla/5.0 (feds200628-replication)"


# ---------------------------------------------------------------------------
# CUSIP master from Treasury Fiscal Data API
# ---------------------------------------------------------------------------

def fetch_cusip_master(cache_path: str = CUSIP_CACHE, refresh: bool = False) -> pd.DataFrame:
    """Return a deduplicated CUSIP-level master of nominal Treasury notes/bonds.

    Columns: cusip, security_type, issue_date, dated_date, maturity_date,
    int_rate, callable, original_issue_date.
    """
    if not refresh and os.path.exists(cache_path):
        df = pd.read_csv(cache_path, parse_dates=["issue_date", "dated_date",
                                                  "maturity_date", "original_issue_date"])
        return df

    os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
    fields = ("cusip,security_type,security_term,issue_date,dated_date,"
              "maturity_date,int_rate,callable,inflation_index_security,"
              "floating_rate,reopening,auction_date,original_issue_date,"
              "original_security_term")

    records: list[dict] = []
    page = 1
    while True:
        url = f"{FISCAL_API}?page[size]=1000&page[number]={page}&fields={fields}&sort=auction_date"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read())
        records.extend(d["data"])
        if len(d["data"]) < 1000:
            break
        page += 1
        if page > 50:
            raise RuntimeError("Pagination guard exceeded")

    print(f"[cusip] fetched {len(records)} auction records "
          f"(total-count={d['meta']['total-count']})")

    df = pd.DataFrame.from_records(records)
    # Keep only nominal coupon notes & bonds
    keep = (df["security_type"].isin(["Note", "Bond"])
            & (df["inflation_index_security"] != "Yes")
            & (df["floating_rate"] != "Yes"))
    df = df.loc[keep].copy()

    for c in ["issue_date", "dated_date", "maturity_date", "auction_date",
              "original_issue_date"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df["int_rate"] = pd.to_numeric(df["int_rate"], errors="coerce")

    # Each CUSIP may appear multiple times (reopenings). Collapse to one row
    # per CUSIP, keeping the earliest original_issue_date as the security's
    # "born" date and the canonical coupon/maturity.
    df = df.sort_values(["cusip", "issue_date"])
    master = df.groupby("cusip", as_index=False).agg({
        "security_type": "first",
        "security_term": "first",
        "original_security_term": "first",
        "dated_date": "first",
        "maturity_date": "first",
        "int_rate": "first",
        "callable": "first",
        "original_issue_date": "first",
        "issue_date": "min",       # earliest issuance (original)
        "auction_date": "min",
    })

    # Use original_issue_date if present, else earliest issue_date
    master["original_issue_date"] = master["original_issue_date"].fillna(master["issue_date"])
    master = master.dropna(subset=["maturity_date", "int_rate", "dated_date"])

    master.to_csv(cache_path, index=False)
    print(f"[cusip] cached {len(master)} unique CUSIPs to {cache_path}")
    return master


# ---------------------------------------------------------------------------
# Svensson model
# ---------------------------------------------------------------------------

def svensson_zero_yield(tau: np.ndarray, beta0: float, beta1: float, beta2: float,
                        beta3: float, tau1: float, tau2: float) -> np.ndarray:
    """Zero-coupon (continuously compounded) yield in percentage points.

    tau in years (>0). Inputs follow Fed convention: BETA in pct, TAU in years.
    """
    tau = np.asarray(tau, dtype=float)
    out = np.empty_like(tau)
    # Avoid division by zero at tau == 0 (limit equals beta0 + beta1)
    mask = tau > 0
    t = tau[mask]
    x1 = t / tau1
    x2 = t / tau2
    # (1 - exp(-x))/x term
    f1 = np.where(x1 > 1e-12, (1.0 - np.exp(-x1)) / x1, 1.0)
    f2 = np.where(x2 > 1e-12, (1.0 - np.exp(-x2)) / x2, 1.0)
    y = (beta0
         + beta1 * f1
         + beta2 * (f1 - np.exp(-x1))
         + beta3 * (f2 - np.exp(-x2)))
    out[mask] = y
    out[~mask] = beta0 + beta1
    return out


def svensson_forward(tau: np.ndarray, beta0: float, beta1: float, beta2: float,
                     beta3: float, tau1: float, tau2: float) -> np.ndarray:
    """Instantaneous forward rate in percentage points at horizon tau (years)."""
    tau = np.asarray(tau, dtype=float)
    x1 = tau / tau1
    x2 = tau / tau2
    return (beta0
            + beta1 * np.exp(-x1)
            + beta2 * x1 * np.exp(-x1)
            + beta3 * x2 * np.exp(-x2))


def svensson_par_yield(tau: np.ndarray, beta0, beta1, beta2, beta3, tau1, tau2,
                       freq: int = 2) -> np.ndarray:
    """Coupon-equivalent par yield for a hypothetical par bond with given maturity.

    Approximation: yields are continuously compounded; we solve c such that
    1 = sum_{i=1..n} (c/freq) * exp(-y(t_i)*t_i) + exp(-y(T)*T) with
    t_i = i / freq, n = freq * tau. Returned in pct.
    """
    tau = np.atleast_1d(np.asarray(tau, dtype=float))
    out = np.full_like(tau, np.nan)
    for k, T in enumerate(tau):
        if T <= 0:
            continue
        n = max(1, int(round(freq * T)))
        ts = np.arange(1, n + 1) / freq
        ts = ts * (T / ts[-1])  # rescale so the last cash flow lands exactly at T
        ys = svensson_zero_yield(ts, beta0, beta1, beta2, beta3, tau1, tau2) / 100.0
        df = np.exp(-ys * ts)
        annuity = df.sum() / freq
        # 1 = c * annuity + df[-1]  =>  c = (1 - df[-1]) / annuity
        out[k] = freq * (1.0 - df[-1]) / df.sum() * 100.0  # convert per-period to annual pct
    return out


# ---------------------------------------------------------------------------
# Bond cash-flow schedule & pricing
# ---------------------------------------------------------------------------

def coupon_dates(maturity: pd.Timestamp, dated: pd.Timestamp) -> list[pd.Timestamp]:
    """Semi-annual coupon dates from `maturity` back to (but excluding) the
    dated date. Schedule walks back in 6-month steps from maturity."""
    dates: list[pd.Timestamp] = []
    d = maturity
    while d > dated:
        dates.append(d)
        # Walk back exactly 6 months
        d = d - pd.DateOffset(months=6)
    return sorted(dates)


@dataclass
class Bond:
    cusip: str
    coupon: float       # annualized %, e.g. 4.5 means 4.5%
    maturity: pd.Timestamp
    dated: pd.Timestamp
    coupons: np.ndarray  # array of pd.Timestamps (sorted ascending)


def make_bond(row: pd.Series) -> Bond:
    cps = coupon_dates(row["maturity_date"], row["dated_date"])
    return Bond(
        cusip=row["cusip"],
        coupon=float(row["int_rate"]),
        maturity=row["maturity_date"],
        dated=row["dated_date"],
        coupons=np.array(cps, dtype="datetime64[D]"),
    )


def bond_clean_price(bond: Bond, settle: pd.Timestamp,
                     beta0: float, beta1: float, beta2: float, beta3: float,
                     tau1: float, tau2: float) -> tuple[float, float]:
    """Return (clean_price_per100, duration_years) for a coupon bond on `settle`.

    Uses continuously compounded zero-coupon yields from the Svensson curve to
    discount each remaining cash flow. Accrued interest follows actual/actual
    ICMA between coupon dates.
    """
    settle_dt = np.datetime64(settle, "D")
    future = bond.coupons[bond.coupons > settle_dt]
    if len(future) == 0:
        return float("nan"), float("nan")

    days_to_cf = (future - settle_dt).astype(int)
    t_years = days_to_cf / 365.25
    y = svensson_zero_yield(t_years, beta0, beta1, beta2, beta3, tau1, tau2) / 100.0
    df = np.exp(-y * t_years)

    coupon_per_period = bond.coupon / 2.0  # semi-annual
    cf = np.full(len(future), coupon_per_period, dtype=float)
    cf[-1] += 100.0  # principal at maturity

    dirty = float((cf * df).sum())

    # Accrued interest (actual/actual ICMA): find the previous coupon date
    prev_cp_arr = bond.coupons[bond.coupons <= settle_dt]
    if len(prev_cp_arr) == 0:
        prev_cp = np.datetime64(bond.dated, "D")
    else:
        prev_cp = prev_cp_arr[-1]
    next_cp = future[0]
    period_days = (next_cp - prev_cp).astype(int)
    accr_days = (settle_dt - prev_cp).astype(int)
    accrued = coupon_per_period * (accr_days / period_days) if period_days > 0 else 0.0

    clean = dirty - accrued

    # Modified duration (continuous-compounding equivalent): D = sum(t*PV)/dirty
    duration = float((t_years * cf * df).sum() / dirty) if dirty > 0 else float("nan")

    return clean, duration


# ---------------------------------------------------------------------------
# Eligibility (paper's filter rules, what's reproducible from public data)
# ---------------------------------------------------------------------------

def eligible_bonds(master: pd.DataFrame, settle: pd.Timestamp) -> pd.DataFrame:
    """Per-paper exclusions reproducible from the public CUSIP master:

      - exclude callable
      - require dated_date <= settle (security exists)
      - require maturity_date - settle >= 90 days
      - exclude 20-year bonds from 1996 onward (per paper)
      - off-the-run filter: drop the most-recent and 2nd-most-recent issue of
        each original_security_term active on `settle`.
    """
    df = master.copy()
    df = df[df["callable"] != "Yes"]
    df = df[df["dated_date"] <= settle]
    df = df[(df["maturity_date"] - settle).dt.days >= 90]

    if settle >= pd.Timestamp("1996-01-01"):
        df = df[df["original_security_term"] != "20-Year"]

    # Off-the-run: rank issues per original_security_term by original_issue_date
    # (descending). Drop ranks 1 and 2 (on-the-run and first off-the-run).
    df = df.sort_values(["original_security_term", "original_issue_date"])
    df["rank_in_term"] = (df.groupby("original_security_term")["original_issue_date"]
                           .rank(method="first", ascending=False))
    df = df[df["rank_in_term"] > 2]
    return df.drop(columns=["rank_in_term"])


# ---------------------------------------------------------------------------
# Svensson NLS fitter (duration-weighted)
# ---------------------------------------------------------------------------

def fit_svensson(bonds: list[Bond], settle: pd.Timestamp, observed_prices: np.ndarray,
                 x0: np.ndarray) -> tuple[np.ndarray, float, int]:
    """Fit Svensson params to observed clean prices using duration-weighted
    nonlinear least squares.

    Returns (params, rmse_bp, n_bonds).
    params order: (beta0, beta1, beta2, beta3, tau1, tau2).
    """
    def residuals(params):
        b0, b1, b2, b3, t1, t2 = params
        if t1 <= 0 or t2 <= 0:
            return np.full(len(bonds), 1e6)
        res = np.empty(len(bonds))
        for i, bnd in enumerate(bonds):
            mp, dur = bond_clean_price(bnd, settle, b0, b1, b2, b3, t1, t2)
            if not np.isfinite(mp) or not np.isfinite(dur) or dur <= 0:
                res[i] = 1e6
            else:
                # Convert price error to ~yield error: dY ≈ -dP / (P * D),
                # so weighting by 1/D is the paper's prescription.
                res[i] = (mp - observed_prices[i]) / dur
        return res

    bounds = ([-50, -50, -50, -50, 1e-3, 1e-3], [50, 50, 50, 50, 50, 50])
    try:
        sol = least_squares(residuals, x0, bounds=bounds, method="trf",
                            max_nfev=500, xtol=1e-10, ftol=1e-10)
        params = sol.x
        res = residuals(params)
        rmse_bp = float(np.sqrt(np.mean(res ** 2))) * 100  # res is in 1/yr-ish units of price; convert to bp-scale (rough)
        return params, rmse_bp, len(bonds)
    except Exception as e:
        print(f"  [fit] failed: {e}")
        return x0, float("nan"), len(bonds)


# ---------------------------------------------------------------------------
# Output schema (matches Fed CSV)
# ---------------------------------------------------------------------------

OUTPUT_COLS = (["BETA0", "BETA1", "BETA2", "BETA3", "TAU1", "TAU2"]
               + [f"SVENY{m:02d}" for m in range(1, 31)]
               + [f"SVENPY{m:02d}" for m in range(1, 31)]
               + [f"SVENF{m:02d}" for m in range(1, 31)])


def derived_row(params: np.ndarray) -> dict:
    b0, b1, b2, b3, t1, t2 = params
    mats = np.arange(1, 31, dtype=float)
    sveny = svensson_zero_yield(mats, b0, b1, b2, b3, t1, t2)
    svenf = svensson_forward(mats, b0, b1, b2, b3, t1, t2)
    svenpy = svensson_par_yield(mats, b0, b1, b2, b3, t1, t2)
    row = {"BETA0": b0, "BETA1": b1, "BETA2": b2, "BETA3": b3,
           "TAU1": t1, "TAU2": t2}
    for i, m in enumerate(mats):
        row[f"SVENY{int(m):02d}"] = sveny[i]
        row[f"SVENF{int(m):02d}"] = svenf[i]
        row[f"SVENPY{int(m):02d}"] = svenpy[i]
    return row


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run(start: str, end: str, out_path: str,
        fed_cache: str = ".cache/feds200628.csv",
        noise_bp: float = 0.0, seed: int = 42,
        verbose_every: int = 50) -> None:
    """Run the replication over [start, end]; write CSV to out_path."""
    # Lazy import to reuse evaluate_replication's Fed fetcher.
    sys.path.insert(0, ".")
    from evaluate_replication import fetch_fed_data, FED_URL

    fed = fetch_fed_data(FED_URL, fed_cache, refresh=False)
    fed = fed.loc[start:end]
    print(f"[run] target dates: {len(fed)} ({fed.index.min().date()} .. {fed.index.max().date()})")

    master = fetch_cusip_master()
    print(f"[run] cusip master: {len(master)} unique bonds")

    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    prev_params: np.ndarray | None = None

    for n_done, (date, fed_row) in enumerate(fed.iterrows(), start=1):
        try:
            elig = eligible_bonds(master, date)
            if len(elig) < 7:  # need >= number of params to fit
                continue

            true = np.array([fed_row["BETA0"], fed_row["BETA1"], fed_row["BETA2"],
                              fed_row["BETA3"], fed_row["TAU1"], fed_row["TAU2"]],
                            dtype=float)
            if not np.all(np.isfinite(true)):
                continue

            bonds = [make_bond(r) for _, r in elig.iterrows()]
            # Generate simulated clean prices from the Fed's "true" params
            prices = np.empty(len(bonds))
            durations = np.empty(len(bonds))
            for i, bnd in enumerate(bonds):
                p, d = bond_clean_price(bnd, date, *true)
                prices[i] = p
                durations[i] = d

            # Optional Gaussian noise on prices (in price units = $ per $100)
            if noise_bp > 0:
                # Convert ~bp of yield noise to price noise via duration
                price_sigma = noise_bp / 100.0 * durations  # approx
                prices = prices + rng.normal(0.0, price_sigma)

            valid = np.isfinite(prices) & np.isfinite(durations) & (durations > 0)
            if valid.sum() < 7:
                continue
            bonds = [b for b, v in zip(bonds, valid) if v]
            prices = prices[valid]

            # Initial guess: previous day's fitted params if available, else true
            x0 = prev_params.copy() if prev_params is not None else true.copy()
            params, _rmse, _n = fit_svensson(bonds, date, prices, x0)
            prev_params = params

            row = {"Date": date, "n_bonds": len(bonds)}
            row.update(derived_row(params))
            rows.append(row)

            if n_done % verbose_every == 0:
                diff_bp = np.abs(svensson_zero_yield(np.array([10.0]), *params) -
                                 svensson_zero_yield(np.array([10.0]), *true))[0] * 100
                print(f"  [{n_done}/{len(fed)}] {date.date()}  n_bonds={len(bonds):3d}  "
                      f"10y diff vs Fed: {diff_bp:.3f} bp")
        except Exception as e:
            print(f"  [{date.date()}] error: {type(e).__name__}: {e}")
            continue

    df = pd.DataFrame(rows)
    if "Date" in df.columns:
        df = df.set_index("Date")
    # Column order to match Fed schema (omit n_bonds from output)
    cols = [c for c in OUTPUT_COLS if c in df.columns]
    df = df[cols]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    df.reset_index().to_csv(out_path, index=False)
    print(f"[run] wrote {len(df)} rows to {out_path}")


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", required=True, help="Start date, YYYY-MM-DD.")
    p.add_argument("--end", required=True, help="End date, YYYY-MM-DD.")
    p.add_argument("--out", required=True, help="Output CSV path (Fed schema).")
    p.add_argument("--noise-bp", type=float, default=0.0,
                   help="Gaussian price-noise stddev in basis points of yield (default 0).")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--verbose-every", type=int, default=50)
    args = p.parse_args(argv)

    run(args.start, args.end, args.out,
        noise_bp=args.noise_bp, seed=args.seed,
        verbose_every=args.verbose_every)
    return 0


if __name__ == "__main__":
    sys.exit(main())
