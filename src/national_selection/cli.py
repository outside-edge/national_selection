"""Reproduce dated international-entry forecasts and chronological backtests."""

import argparse
import json
from pathlib import Path

import pandas as pd

from national_selection.backtest import summarize_runs
from national_selection.data import import_local
from national_selection.features import build_panel
from national_selection.models import evaluate, forecast


def read_inputs(folder):
    return [
        pd.read_csv(folder / name, dtype={"player_id": str, "match_id": str})
        for name in [
            "performances.csv",
            "eligibility.csv",
            "international_appearances.csv",
            "calendar.csv",
            "prior_appearances.csv",
        ]
    ]


def mature_cutoffs(horizon, observed_through):
    last = (
        pd.Timestamp(observed_through)
        + pd.Timedelta(days=1)
        - pd.DateOffset(months=horizon)
    )
    return pd.date_range("2010-01-01", last, freq="MS")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=["import", "prepare", "evaluate", "forecast", "all"]
    )
    parser.add_argument("--workspace", type=Path, default=Path(".."))
    parser.add_argument("--data", type=Path, default=Path("data/build"))
    parser.add_argument("--out", type=Path, default=Path("out"))
    parser.add_argument("--horizons", type=int, nargs="+", default=[6, 12, 24])
    parser.add_argument("--observed-through", default="2025-12-31")
    parser.add_argument("--cutoff", default="2026-01-01")
    args = parser.parse_args()
    if len(set(args.horizons)) != len(args.horizons) or any(
        h <= 0 for h in args.horizons
    ):
        parser.error("Horizons must be distinct positive calendar-month counts")
    if args.command in ["import", "all"]:
        report = import_local(args.workspace, args.data)
        print(
            json.dumps(
                {
                    k: v
                    for k, v in report.items()
                    if k not in {"source_files", "missing_internationals"}
                },
                indent=2,
            )
        )
    if args.command != "import":
        manifest = json.loads((args.data / "manifest.json").read_text())
        if args.observed_through > manifest["observed_through"]:
            parser.error("Requested observation end exceeds imported data coverage")
    if args.command in ["prepare", "all"]:
        tables = read_inputs(args.data)
        for horizon in args.horizons:
            panel = build_panel(
                *tables,
                cutoffs=mature_cutoffs(horizon, args.observed_through),
                horizon_months=horizon,
                observed_through=args.observed_through,
            )
            panel.to_csv(args.data / f"panel_{horizon}m.csv", index=False)
            panel.groupby(["country", "cutoff_date"]).agg(
                players=("player_id", "size"), positives=("selected", "sum")
            ).reset_index().to_csv(
                args.data / f"risk_set_by_country_{horizon}m.csv", index=False
            )
            print(
                f"{horizon}m: {len(panel)} snapshots, "
                f"{panel.player_id.nunique()} players",
                flush=True,
            )
    if args.command in ["evaluate", "all"]:
        for horizon in args.horizons:
            panel = pd.read_csv(
                args.data / f"panel_{horizon}m.csv", dtype={"player_id": str}
            )
            for cadence in ["monthly", "annual"]:
                evaluate(
                    panel,
                    args.out / f"{cadence}_{horizon}m",
                    cadence=cadence,
                    observed_through=args.observed_through,
                )
        print(summarize_runs(args.out, args.horizons).to_string(index=False))
    if args.command in ["forecast", "all"]:
        tables = read_inputs(args.data)
        for horizon in args.horizons:
            snapshot = build_panel(
                *tables,
                cutoffs=[args.cutoff],
                horizon_months=horizon,
                labeled=False,
                observed_through=args.observed_through,
            )
            panel = pd.read_csv(
                args.data / f"panel_{horizon}m.csv", dtype={"player_id": str}
            )
            forecast(
                panel,
                snapshot,
                args.out / f"monthly_{horizon}m",
                observed_through=args.observed_through,
            )


if __name__ == "__main__":
    main()
