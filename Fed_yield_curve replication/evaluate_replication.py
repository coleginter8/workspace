"""Evaluate a replication of FEDS-200628 (Gürkaynak, Sack & Wright 2006)
against the Federal Reserve's officially published yield-curve dataset.

The replicated CSV is expected to share the Fed schema: BETA0..BETA3, TAU1,
TAU2, SVENY01..30, SVENPY01..30, SVENF01..30 (and optional SVEN1F*). Missing
values may be encoded as -9999 (Fed convention) or left blank.

Usage:
    python evaluate_replication.py --replication path/to/repl.csv
                                  [--fed-cache .cache/feds200628.csv]
                                  [--refresh]
                                  [--start YYYY-MM-DD] [--end YYYY-MM-DD]
                                  [--report path/to/report.txt]
                                  [--yields-rmse-bp 5.0] [--yields-max-bp 25.0]
                                  [--params-rmse 0.10] [--min-corr 0.999]

Exit code: 0 if all thresholds pass, 1 otherwise.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import urllib.request
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


FED_URL = "https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv"
DEFAULT_CACHE_PATH = ".cache/feds200628.csv"
MISSING_SENTINEL = -9999

PARAM_COLS = ["BETA0", "BETA1", "BETA2", "BETA3", "TAU1", "TAU2"]
YIELD_COLS = [f"SVENY{m:02d}" for m in range(1, 31)]
PAR_COLS = [f"SVENPY{m:02d}" for m in range(1, 31)]
FWD_COLS = [f"SVENF{m:02d}" for m in range(1, 31)]

GROUPS = [
    ("SVENSSON PARAMETERS", PARAM_COLS, "params"),
    ("ZERO-COUPON YIELDS (basis points)", YIELD_COLS, "bp"),
    ("PAR YIELDS (basis points)", PAR_COLS, "bp"),
    ("INSTANTANEOUS FORWARDS (basis points)", FWD_COLS, "bp"),
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _read_fed_csv(text: str) -> pd.DataFrame:
    """Parse Fed CSV text, skipping the metadata preamble before the header row."""
    lines = text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        # The real column row starts with 'Date,' (case sensitive in the Fed file).
        if line.startswith("Date,") or line.lower().startswith("date,"):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("Could not find 'Date,' header row in Fed CSV.")

    csv_body = "\n".join(lines[header_idx:])
    df = pd.read_csv(io.StringIO(csv_body))
    return _normalize(df)


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    # Normalize the date column name.
    date_col = next((c for c in df.columns if c.lower() == "date"), None)
    if date_col is None:
        raise ValueError("Input CSV has no Date column.")
    df = df.rename(columns={date_col: "Date"})
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).set_index("Date").sort_index()

    # Replace Fed missing sentinel with NaN across all numeric columns.
    df = df.replace(MISSING_SENTINEL, np.nan)
    # Coerce non-Date columns to numeric.
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def fetch_fed_data(url: str, cache_path: str, refresh: bool) -> pd.DataFrame:
    if refresh or not os.path.exists(cache_path):
        os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
        print(f"[fetch] Downloading {url}")
        # federalreserve.gov rejects requests with no User-Agent.
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (feds200628-replication-eval)"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        with open(cache_path, "w") as f:
            f.write(text)
        print(f"[fetch] Cached to {cache_path} ({len(text):,} bytes)")
    else:
        print(f"[fetch] Using cached {cache_path}")
        with open(cache_path) as f:
            text = f.read()
    return _read_fed_csv(text)


def load_replication(path: str) -> pd.DataFrame:
    with open(path) as f:
        text = f.read()
    # Reuse the same parser to tolerate Fed-style preamble or a plain header.
    return _read_fed_csv(text)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@dataclass
class ColMetrics:
    column: str
    n: int
    rmse: float
    mae: float
    max_abs_err: float
    bias: float
    corr: float
    pct_within_1bp: float | None = None
    pct_within_5bp: float | None = None
    pct_within_10bp: float | None = None
    pct_within_25bp: float | None = None


def compute_metrics(fed_col: pd.Series, repl_col: pd.Series, scale: str) -> ColMetrics:
    """Compute per-column comparison metrics.

    scale="bp": multiply diff by 100 (Fed yields are in percentage points, so
    1.0 == 100 bp). Adds tolerance pass-rates.
    scale="params": natural units.
    """
    name = fed_col.name
    pair = pd.concat([fed_col, repl_col], axis=1, keys=["fed", "repl"]).dropna()
    n = len(pair)
    if n == 0:
        return ColMetrics(name, 0, np.nan, np.nan, np.nan, np.nan, np.nan)

    diff = (pair["repl"] - pair["fed"]).to_numpy(dtype=float)
    if scale == "bp":
        diff = diff * 100.0

    rmse = float(np.sqrt(np.mean(diff ** 2)))
    mae = float(np.mean(np.abs(diff)))
    max_abs = float(np.max(np.abs(diff)))
    bias = float(np.mean(diff))

    if pair["fed"].std() == 0 or pair["repl"].std() == 0:
        corr = float("nan")
    else:
        corr = float(np.corrcoef(pair["fed"], pair["repl"])[0, 1])

    m = ColMetrics(name, n, rmse, mae, max_abs, bias, corr)
    if scale == "bp":
        abs_diff = np.abs(diff)
        m.pct_within_1bp = 100.0 * float(np.mean(abs_diff <= 1.0))
        m.pct_within_5bp = 100.0 * float(np.mean(abs_diff <= 5.0))
        m.pct_within_10bp = 100.0 * float(np.mean(abs_diff <= 10.0))
        m.pct_within_25bp = 100.0 * float(np.mean(abs_diff <= 25.0))
    return m


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

@dataclass
class GroupReport:
    title: str
    scale: str
    rows: list[ColMetrics] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def group_rmse(self) -> float:
        vals = [r.rmse for r in self.rows if not np.isnan(r.rmse)]
        return float(np.sqrt(np.mean(np.square(vals)))) if vals else float("nan")

    @property
    def group_max(self) -> float:
        vals = [r.max_abs_err for r in self.rows if not np.isnan(r.max_abs_err)]
        return max(vals) if vals else float("nan")

    @property
    def min_corr(self) -> float:
        vals = [r.corr for r in self.rows if not np.isnan(r.corr)]
        return min(vals) if vals else float("nan")


@dataclass
class Report:
    fed_range: tuple[pd.Timestamp, pd.Timestamp]
    fed_n: int
    repl_range: tuple[pd.Timestamp, pd.Timestamp]
    repl_n: int
    overlap_range: tuple[pd.Timestamp, pd.Timestamp]
    overlap_n: int
    groups: list[GroupReport]
    worst_dates: pd.DataFrame  # date, worst_series, abs_diff_bp


def build_report(fed: pd.DataFrame, repl: pd.DataFrame,
                 fed_full: pd.DataFrame, repl_full: pd.DataFrame) -> Report:
    groups: list[GroupReport] = []
    bp_diff_frames: list[pd.DataFrame] = []

    for title, cols, scale in GROUPS:
        g = GroupReport(title=title, scale=scale)
        for c in cols:
            if c not in fed.columns or c not in repl.columns:
                g.skipped.append(c)
                continue
            g.rows.append(compute_metrics(fed[c], repl[c], scale=scale))
        groups.append(g)

        if scale == "bp" and g.rows:
            present_cols = [c for c in cols if c in fed.columns and c in repl.columns]
            d = (repl[present_cols] - fed[present_cols]) * 100.0
            bp_diff_frames.append(d)

    # Worst dates across all bp columns (yields + par + forwards).
    if bp_diff_frames:
        all_bp = pd.concat(bp_diff_frames, axis=1)
        abs_bp = all_bp.abs()
        worst_per_date = pd.DataFrame({
            "worst_series": abs_bp.idxmax(axis=1),
            "abs_diff_bp": abs_bp.max(axis=1),
        }).dropna()
        worst_dates = worst_per_date.sort_values(
            "abs_diff_bp", ascending=False
        ).head(10).reset_index().rename(columns={"index": "Date"})
    else:
        worst_dates = pd.DataFrame(columns=["Date", "worst_series", "abs_diff_bp"])

    return Report(
        fed_range=(fed_full.index.min(), fed_full.index.max()),
        fed_n=len(fed_full),
        repl_range=(repl_full.index.min(), repl_full.index.max()),
        repl_n=len(repl_full),
        overlap_range=(fed.index.min(), fed.index.max()) if len(fed) else (pd.NaT, pd.NaT),
        overlap_n=len(fed),
        groups=groups,
        worst_dates=worst_dates,
    )


def _fmt(x: float, width: int = 8, prec: int = 3) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "nan".rjust(width)
    return f"{x:>{width}.{prec}f}"


def render_report(report: Report, tolerances: dict) -> tuple[str, int]:
    """Render the report as text and return (text, exit_code)."""
    out: list[str] = []
    bar = "=" * 78
    sep = "-" * 78

    out.append(bar)
    out.append("FEDS-200628 REPLICATION EVALUATION")
    out.append(f"Fed data:     {report.fed_range[0].date()} to {report.fed_range[1].date()}  "
               f"(n={report.fed_n})")
    out.append(f"Replication:  {report.repl_range[0].date()} to {report.repl_range[1].date()}  "
               f"(n={report.repl_n})")
    if report.overlap_n:
        out.append(f"Overlap:      {report.overlap_range[0].date()} to "
                   f"{report.overlap_range[1].date()}  (n={report.overlap_n})")
    else:
        out.append("Overlap:      (none)")
    out.append(bar)

    failures: list[str] = []

    if report.overlap_n < tolerances["min_overlap_dates"]:
        failures.append(
            f"min_overlap_dates >= {tolerances['min_overlap_dates']} "
            f"FAIL (overlap n={report.overlap_n})"
        )

    for g in report.groups:
        out.append("")
        out.append(f"--- {g.title} ---")
        if not g.rows:
            out.append("  (no columns present in both files; skipped)")
            continue
        if g.scale == "bp":
            header = (f"  {'col':<10} {'n':>6} {'RMSE':>8} {'MAE':>8} "
                      f"{'MaxAbs':>8} {'Bias':>8} {'Corr':>7} "
                      f"{'%<1bp':>7} {'%<5bp':>7} {'%<10bp':>7} {'%<25bp':>7}")
        else:
            header = (f"  {'col':<10} {'n':>6} {'RMSE':>8} {'MAE':>8} "
                      f"{'MaxAbs':>8} {'Bias':>8} {'Corr':>7}")
        out.append(header)
        for r in g.rows:
            line = (f"  {r.column:<10} {r.n:>6d} {_fmt(r.rmse)} {_fmt(r.mae)} "
                    f"{_fmt(r.max_abs_err)} {_fmt(r.bias)} {_fmt(r.corr, 7, 4)}")
            if g.scale == "bp":
                line += (f" {_fmt(r.pct_within_1bp, 7, 1)} {_fmt(r.pct_within_5bp, 7, 1)} "
                         f"{_fmt(r.pct_within_10bp, 7, 1)} {_fmt(r.pct_within_25bp, 7, 1)}")
            out.append(line)
        if g.skipped:
            out.append(f"  (skipped, not in both files: {', '.join(g.skipped)})")

        if g.scale == "bp":
            group_pass = (g.group_rmse <= tolerances["yields_rmse_bp"]
                          and g.group_max <= tolerances["yields_max_error_bp"])
            status = "PASS" if group_pass else "FAIL"
            out.append(f"  GROUP RMSE: {g.group_rmse:.3f} bp   "
                       f"GROUP MAX: {g.group_max:.3f} bp   "
                       f"MIN CORR: {g.min_corr:.4f}   {status}")
            if not group_pass:
                if g.group_rmse > tolerances["yields_rmse_bp"]:
                    failures.append(f"{g.title}: group RMSE {g.group_rmse:.3f} bp "
                                    f"> {tolerances['yields_rmse_bp']} bp")
                if g.group_max > tolerances["yields_max_error_bp"]:
                    worst = max(g.rows, key=lambda r: 0 if np.isnan(r.max_abs_err) else r.max_abs_err)
                    failures.append(f"{g.title}: max abs error {g.group_max:.3f} bp "
                                    f"({worst.column}) > {tolerances['yields_max_error_bp']} bp")
            if not np.isnan(g.min_corr) and g.min_corr < tolerances["min_correlation"]:
                worst = min((r for r in g.rows if not np.isnan(r.corr)),
                            key=lambda r: r.corr)
                failures.append(f"{g.title}: min correlation {g.min_corr:.4f} "
                                f"({worst.column}) < {tolerances['min_correlation']}")
        else:
            group_pass = g.group_rmse <= tolerances["params_rmse"]
            status = "PASS" if group_pass else "FAIL"
            out.append(f"  GROUP RMSE: {g.group_rmse:.4f}   "
                       f"GROUP MAX: {g.group_max:.4f}   "
                       f"MIN CORR: {g.min_corr:.4f}   {status}")
            if not group_pass:
                failures.append(f"{g.title}: group RMSE {g.group_rmse:.4f} "
                                f"> {tolerances['params_rmse']}")

    out.append("")
    out.append(sep)
    out.append("WORST 10 DATES (largest abs difference across any yield series, bp)")
    if len(report.worst_dates):
        out.append(f"  {'date':<12} {'worst_series':<12} {'abs_diff_bp':>12}")
        for _, row in report.worst_dates.iterrows():
            out.append(f"  {pd.Timestamp(row['Date']).date()!s:<12} "
                       f"{row['worst_series']:<12} {row['abs_diff_bp']:>12.3f}")
    else:
        out.append("  (no overlap or no basis-point series present)")

    out.append("")
    out.append(sep)
    out.append("THRESHOLD CHECK")
    if not failures:
        out.append("  All thresholds passed.")
    else:
        for f in failures:
            out.append(f"  FAIL: {f}")

    out.append(bar)
    overall = "PASS" if not failures else f"FAIL ({len(failures)} violation(s))"
    out.append(f"OVERALL: {overall}")
    out.append(bar)

    return "\n".join(out), (0 if not failures else 1)


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------

def align(fed: pd.DataFrame, repl: pd.DataFrame,
          start: str | None, end: str | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    common = fed.index.intersection(repl.index)
    if start:
        common = common[common >= pd.Timestamp(start)]
    if end:
        common = common[common <= pd.Timestamp(end)]
    return fed.loc[common], repl.loc[common]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--replication", required=True, help="Path to replicated CSV.")
    p.add_argument("--fed-cache", default=DEFAULT_CACHE_PATH, help="Path to cached Fed CSV.")
    p.add_argument("--fed-url", default=FED_URL, help="Override Fed CSV URL.")
    p.add_argument("--refresh", action="store_true", help="Force re-download of Fed CSV.")
    p.add_argument("--start", default=None, help="Start date (inclusive), YYYY-MM-DD.")
    p.add_argument("--end", default=None, help="End date (inclusive), YYYY-MM-DD.")
    p.add_argument("--report", default=None, help="Write report to this path in addition to stdout.")
    p.add_argument("--yields-rmse-bp", type=float, default=5.0)
    p.add_argument("--yields-max-bp", type=float, default=25.0)
    p.add_argument("--params-rmse", type=float, default=0.10)
    p.add_argument("--min-corr", type=float, default=0.999)
    p.add_argument("--min-overlap", type=int, default=100)
    args = p.parse_args(argv)

    tolerances = {
        "yields_rmse_bp": args.yields_rmse_bp,
        "yields_max_error_bp": args.yields_max_bp,
        "params_rmse": args.params_rmse,
        "min_correlation": args.min_corr,
        "min_overlap_dates": args.min_overlap,
    }

    fed_full = fetch_fed_data(args.fed_url, args.fed_cache, args.refresh)
    repl_full = load_replication(args.replication)
    fed_aligned, repl_aligned = align(fed_full, repl_full, args.start, args.end)

    report = build_report(fed_aligned, repl_aligned, fed_full, repl_full)
    text, exit_code = render_report(report, tolerances)

    print(text)
    if args.report:
        os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
        with open(args.report, "w") as f:
            f.write(text + "\n")
        print(f"\n[report] Written to {args.report}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
