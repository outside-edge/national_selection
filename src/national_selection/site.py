"""Build publication tables from saved forecasts and verify rendered downloads."""

import argparse
import hashlib
import json
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import numpy as np
import pandas as pd

from national_selection.cli import read_inputs
from national_selection.features import build_panel


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_forecast(frame, policy, observed_through):
    if (
        frame.empty
        or frame.player_id.isna().any()
        or frame.player_id.duplicated().any()
    ):
        raise ValueError("Forecast requires unique, nonmissing player IDs")
    for column in ["cutoff_date", "label_end", "fit_date", "horizon_months"]:
        if frame[column].isna().any() or frame[column].nunique() != 1:
            raise ValueError(f"Mixed or missing forecast metadata: {column}")
    row = frame.iloc[0]
    cutoff, fit = pd.Timestamp(row.cutoff_date), pd.Timestamp(row.fit_date)
    horizon = int(row.horizon_months)
    if horizon <= 0 or horizon != policy["horizon_months"]:
        raise ValueError("Forecast horizon differs from selection policy")
    if policy["observed_through"] != observed_through:
        raise ValueError("Selection policy and inputs have different coverage")
    if cutoff > pd.Timestamp(observed_through) + pd.Timedelta(days=1):
        raise ValueError("Forecast exceeds input coverage")
    if fit != pd.Timestamp(year=cutoff.year, month=1, day=1):
        raise ValueError("Forecast must use its annual parameter fit")
    if pd.Timestamp(policy["policy_available_from"]) > fit:
        raise ValueError("Model policy was unavailable at the fit date")
    expected_end = cutoff + pd.DateOffset(months=horizon) - pd.Timedelta(days=1)
    if pd.Timestamp(row.label_end) != expected_end:
        raise ValueError("Forecast target window is inconsistent")
    selected = policy["classification_model_selected_on_validation_log_loss"]
    if not frame.selected_classifier.eq(selected).all():
        raise ValueError("Forecast selected model differs from validation policy")
    for model in {selected, "logistic"}:
        values = pd.to_numeric(frame[model], errors="raise")
        if not np.isfinite(values).all() or not values.between(0, 1).all():
            raise ValueError(f"Invalid probabilities: {model}")
    return selected


def markdown_table(frame):
    def cell(value):
        return escape(str(value)).replace("|", "&#124;").replace("\n", " ")

    lines = ["| " + " | ".join(map(cell, frame.columns)) + " |"]
    lines.append("| " + " | ".join("---" for _ in frame.columns) + " |")
    lines.extend(
        "| " + " | ".join(map(cell, row)) + " |"
        for row in frame.itertuples(index=False, name=None)
    )
    return "\n".join(lines)


def prepare_content(root):
    root = Path(root)
    data = root / "data/build"
    manifest = json.loads((data / "manifest.json").read_text())
    observed = manifest["observed_through"]
    tables = read_inputs(data)
    content = [
        "::: {.callout-warning}",
        "## Historical forecasts",
        f"Input coverage ends **{observed}**. These are saved forecasts, not live "
        "predictions as of the website build date.",
        ":::",
        "",
    ]
    runs = []
    for horizon in [12, 6, 24]:
        directory = root / f"out/monthly_{horizon}m"
        frame = pd.read_csv(directory / "forecast.csv", dtype={"player_id": str})
        policy = json.loads((directory / "selection.json").read_text())
        selected = validate_forecast(frame, policy, observed)
        cutoff, end, fit = frame.iloc[0][["cutoff_date", "label_end", "fit_date"]]
        snapshot = build_panel(
            *tables,
            cutoffs=[cutoff],
            horizon_months=horizon,
            observed_through=observed,
            labeled=False,
        )
        features = [
            "career_matches",
            "career_runs",
            "career_batting_average",
            "career_strike_rate",
        ]
        keys = ["player_id", "country", "cutoff_date"]
        if set(frame.player_id) != set(snapshot.player_id):
            raise ValueError("Saved forecast and reconstructed risk set disagree")
        joined = frame.merge(
            snapshot[keys + features],
            on=keys,
            how="outer",
            validate="one_to_one",
            indicator=True,
        )
        if not joined._merge.eq("both").all():
            raise ValueError("Forecast affiliation or cutoff differs from inputs")
        joined["selected_probability"] = joined[selected]
        joined = joined.sort_values(
            ["country", "logistic", "player_id"], ascending=[True, False, True]
        )
        download = f"out/monthly_{horizon}m/forecast_metrics.csv"
        columns = [
            "player_id",
            "player_name",
            "country",
            "cutoff_date",
            "label_end",
            "horizon_months",
            "fit_date",
            "selected_classifier",
            "selected_probability",
            "logistic",
            *features,
        ]
        joined[columns].to_csv(root / download, index=False)
        runs.append(
            dict(
                horizon_months=horizon,
                cutoff_date=cutoff,
                label_end=end,
                fit_date=fit,
                selected_model=selected,
                candidates=len(joined),
            )
        )
        content += [
            f"## Next {horizon} months",
            "",
            f"Forecast date: **{cutoff}**. Outcome window: **{cutoff}–{end}**. "
            f"Parameter fit: **{fit}**. Candidates: **{len(joined)}**.",
            "",
            f"Validation selected **`{selected}`**. Within each country, rows below "
            "are ordered by the **exploratory logistic score**, not by an endorsed "
            "selection ranking.",
            "",
            f"[Download forecasts and IPL metrics]({download}) · "
            f"[Backtest](out/monthly_{horizon}m/report.md)",
            "",
        ]
        for country, group in joined.groupby("country", sort=True):
            display = group[
                ["player_name", "selected_probability", "logistic", *features]
            ].copy()
            for column in ["selected_probability", "logistic"]:
                display[column] = display[column].map(lambda x: f"{x:.1%}")
            for column in ["career_matches", "career_runs"]:
                display[column] = display[column].map(lambda x: f"{x:,.0f}")
            for column in ["career_batting_average", "career_strike_rate"]:
                display[column] = display[column].map(
                    lambda x: "—" if pd.isna(x) else f"{x:.1f}"
                )
            display.columns = [
                "Player",
                "Selected model",
                "Logistic (exploratory)",
                "IPL matches",
                "IPL runs",
                "Batting average",
                "Strike rate",
            ]
            content += [f"### {country}", "", markdown_table(display), ""]
    generated = root / "docs/_generated"
    generated.mkdir(parents=True, exist_ok=True)
    (generated / "forecasts.md").write_text("\n".join(content) + "\n")
    cutoffs = ", ".join(sorted({run["cutoff_date"] for run in runs}))
    status = (
        "::: {.callout-important}\n## Forecast vintage\n"
        f"Data through **{observed}**; forecast date(s): **{cutoffs}**. "
        "These are historical snapshots. Rebuilding this website does not "
        "advance the data cutoff.\n:::\n"
    )
    (generated / "status.md").write_text(status)
    downloads = sorted(
        set(data.glob("*"))
        | set((root / "out").glob("**/*.csv"))
        | set((root / "out").glob("**/selection.json"))
    )
    downloads = [
        p for p in downloads if p.is_file() and "site" not in p.relative_to(root).parts
    ]
    publication = {
        "observed_through": observed,
        "forecasts": runs,
        "downloads": {str(p.relative_to(root)): checksum(p) for p in downloads},
    }
    (root / "out/publication.json").write_text(json.dumps(publication, indent=2) + "\n")
    return publication


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.targets.append(value)


def check_site(directory):
    root = Path(directory).resolve()
    pages = sorted(root.rglob("*.html"))
    if not (root / "index.html").is_file() or not pages:
        raise ValueError("Rendered site is missing")
    for page in pages:
        parser = Links()
        parser.feed(page.read_text())
        for value in parser.targets:
            url = urlsplit(value)
            if url.scheme or url.netloc or not url.path:
                continue
            path = unquote(url.path)
            target = (
                root / path.lstrip("/") if path.startswith("/") else page.parent / path
            )
            if target.is_dir():
                target /= "index.html"
            if not target.resolve().is_relative_to(root) or not target.is_file():
                raise ValueError(
                    f"Broken local link in {page.relative_to(root)}: {value}"
                )
    publication = json.loads((root / "out/publication.json").read_text())
    for name, digest in publication["downloads"].items():
        target = root / name
        if not target.resolve().is_relative_to(root) or not target.is_file():
            raise ValueError(f"Missing download: {name}")
        if checksum(target) != digest:
            raise ValueError(f"Download checksum mismatch: {name}")
    return len(pages)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "check"])
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    if args.command == "prepare":
        publication = prepare_content(args.root)
        print(f"Prepared {len(publication['forecasts'])} forecast tables")
    else:
        print(f"Verified {check_site(args.root / 'out/site')} pages and all downloads")


if __name__ == "__main__":
    main()
