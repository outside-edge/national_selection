"""Command-line entry points for the local pilot."""

import argparse
import json
from pathlib import Path

import pandas as pd

from national_selection.data import import_local
from national_selection.features import build_panel
from national_selection.models import evaluate, forecast


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=["import", "prepare", "evaluate", "forecast", "all"]
    )
    parser.add_argument("--workspace", type=Path, default=Path(".."))
    parser.add_argument("--data", type=Path, default=Path("data/build"))
    parser.add_argument("--out", type=Path, default=Path("out"))
    args = parser.parse_args()
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
    if args.command in ["prepare", "all"]:
        tables = [
            pd.read_csv(args.data / name, dtype={"player_id": str, "match_id": str})
            for name in [
                "performances.csv",
                "eligibility.csv",
                "international_appearances.csv",
                "calendar.csv",
                "prior_appearances.csv",
            ]
        ]
        panel = build_panel(*tables)
        panel.to_csv(args.data / "panel.csv", index=False)
        panel.groupby(["country", "cutoff_date"]).agg(
            players=("player_id", "size"), positives=("selected", "sum")
        ).reset_index().to_csv(args.data / "risk_set_by_country.csv", index=False)
        print(
            panel.groupby("cutoff_date")
            .agg(players=("player_id", "size"), positives=("selected", "sum"))
            .to_string()
        )
    if args.command in ["evaluate", "all"]:
        panel = pd.read_csv(args.data / "panel.csv", dtype={"player_id": str})
        scores = evaluate(panel, args.out)
        print(pd.DataFrame(scores).to_string(index=False))
    if args.command in ["forecast", "all"]:
        tables = [
            pd.read_csv(args.data / name, dtype={"player_id": str, "match_id": str})
            for name in [
                "performances.csv",
                "eligibility.csv",
                "international_appearances.csv",
                "calendar.csv",
                "prior_appearances.csv",
            ]
        ]
        snapshot = build_panel(*tables, first_year=2026, last_year=2026, labeled=False)
        panel = pd.read_csv(args.data / "panel.csv", dtype={"player_id": str})
        forecast(panel, snapshot, args.out)


if __name__ == "__main__":
    main()
