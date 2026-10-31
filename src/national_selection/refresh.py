"""Refresh sibling inputs and publish forecasts without replacing the benchmark."""

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd

from national_selection.cli import mature_cutoffs, read_inputs
from national_selection.data import import_local
from national_selection.features import build_panel
from national_selection.models import forecast

ARCHIVES = {
    "ipl": "ipl_auction/data/perf/sources/kaggle/ipl-dataset/json/ipl_match",
    "tests": "war/data/raw/cricsheet/tests",
    "odis": "war/data/raw/cricsheet/odis",
    "t20s": "war/data/raw/cricsheet/t20is",
}
SIBLINGS = {
    "side_order": ("main", ["data/build/matches.csv", "data/build/manifest.json"]),
    "ipl_auction": (
        "master",
        [
            "data/acquisitions/player_registry.csv",
            "data/acquisitions/name_aliases.csv",
        ],
    ),
}


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n")


def download(url, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".download")
    subprocess.run(
        [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--location",
            "--retry",
            "3",
            "--max-time",
            "300",
            "--output",
            str(temporary),
            url,
        ],
        check=True,
    )
    temporary.replace(destination)


def extract_archive(archive, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    names = set()
    with zipfile.ZipFile(archive) as source:
        for entry in source.infolist():
            name = entry.filename
            if not name.endswith(".json"):
                continue
            if not name.removesuffix(".json").isdecimal() or name in names:
                raise ValueError(f"Unexpected or duplicate archive member: {name}")
            names.add(name)
            with source.open(entry) as incoming, (destination / name).open("wb") as out:
                shutil.copyfileobj(incoming, out)
    if not names:
        raise ValueError("Archive contains no match records")
    return len(names)


def acquire(workspace):
    workspace = Path(workspace)
    receipts = {
        "retrieved_at": datetime.now(UTC).isoformat(),
        "siblings": {},
        "archives": {},
    }
    for repository, (branch, files) in SIBLINGS.items():
        commit = subprocess.check_output(
            [
                "gh",
                "api",
                f"repos/outside-edge/{repository}/commits/{branch}",
                "--jq",
                ".sha",
            ],
            text=True,
        ).strip()
        if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
            raise ValueError("Invalid upstream commit")
        receipts["siblings"][repository] = {"commit": commit, "files": {}}
        for name in files:
            target = workspace / repository / name
            download(
                f"https://raw.githubusercontent.com/outside-edge/{repository}/{commit}/{name}",
                target,
            )
            receipts["siblings"][repository]["files"][name] = sha256(target)
    for archive, folder in ARCHIVES.items():
        url = f"https://cricsheet.org/downloads/{archive}_json.zip"
        target = workspace / f"{archive}.zip"
        print(f"Downloading {archive}", flush=True)
        download(url, target)
        count = extract_archive(target, workspace / folder)
        receipts["archives"][archive] = {
            "url": url,
            "sha256": sha256(target),
            "match_files": count,
        }
    affiliations = Path(__file__).parent / "reference/auction_affiliations.csv"
    target = workspace / "ipl_auction/data/acquisitions/sources/clod/ipl_2008_2026.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(affiliations, target)
    receipts["affiliations_sha256"] = sha256(affiliations)
    write_json(workspace / "sources.json", receipts)
    return receipts


def observation_end(manifest, today):
    cutoff = date.fromisoformat(manifest["as_of"])
    if cutoff >= today or (today - cutoff).days > 10:
        raise ValueError(
            "Sibling calendar must cover a completed day within the last 10 days"
        )
    return cutoff


def verify_retained_matches(previous, current):
    for filename in [
        "performances.csv",
        "international_appearances.csv",
        "calendar.csv",
    ]:
        before, after = Path(previous) / filename, Path(current) / filename
        if before.exists():
            old = set(pd.read_csv(before, usecols=["match_id"], dtype=str).match_id)
            new = set(pd.read_csv(after, usecols=["match_id"], dtype=str).match_id)
            if old - new:
                raise ValueError(
                    f"Previously recorded matches disappeared from {filename}; "
                    "review before publication"
                )


def build_current(root, workspace, destination, *, today=None):
    root, workspace, destination = Path(root), Path(workspace), Path(destination)
    today = today or datetime.now(UTC).date()
    receipts = json.loads((workspace / "sources.json").read_text())
    if set(receipts["archives"]) != set(ARCHIVES) or set(receipts["siblings"]) != set(
        SIBLINGS
    ):
        raise ValueError("Acquisition receipts do not cover all required sources")
    retrieved = datetime.fromisoformat(receipts["retrieved_at"]).date()
    if retrieved > today or (today - retrieved).days > 2:
        raise ValueError("Acquisition receipts are stale or future-dated")
    for repository, details in receipts["siblings"].items():
        for name, digest in details["files"].items():
            if sha256(workspace / repository / name) != digest:
                raise ValueError("Upstream source checksum mismatch")
    for name, details in receipts["archives"].items():
        if sha256(workspace / f"{name}.zip") != details["sha256"]:
            raise ValueError("Archive checksum mismatch")
    affiliations = (
        workspace / "ipl_auction/data/acquisitions/sources/clod/ipl_2008_2026.csv"
    )
    if sha256(affiliations) != receipts["affiliations_sha256"]:
        raise ValueError("Affiliation reference checksum mismatch")
    calendar_root = workspace / "side_order/data/build"
    calendar_manifest = json.loads((calendar_root / "manifest.json").read_text())
    if sha256(calendar_root / "matches.csv") != calendar_manifest["matches_sha256"]:
        raise ValueError("Calendar and its publication manifest disagree")
    observed = observation_end(calendar_manifest, today)
    cutoff = (observed + timedelta(days=1)).isoformat()
    previous = root / "data/current"
    if previous.exists():
        old_end = json.loads((previous / "manifest.json").read_text())[
            "observed_through"
        ]
        if observed.isoformat() < old_end:
            raise ValueError(
                "Refusing to move the published observation cutoff backward"
            )
    data = destination / "data/current"
    report = import_local(workspace, data, observed_through=observed.isoformat())
    verify_retained_matches(
        previous if previous.exists() else root / "data/build", data
    )
    tables = read_inputs(data)
    for horizon in [6, 12, 24]:
        directory = destination / f"out/current/monthly_{horizon}m"
        directory.mkdir(parents=True, exist_ok=True)
        policy_path = root / f"out/monthly_{horizon}m/selection.json"
        policy = json.loads(policy_path.read_text())
        policy["frozen_policy_sha256"] = sha256(policy_path)
        policy["benchmark_observed_through"] = policy["observed_through"]
        policy["observed_through"] = observed.isoformat()
        write_json(directory / "selection.json", policy)
        panel = build_panel(
            *tables,
            cutoffs=mature_cutoffs(horizon, observed.isoformat()),
            horizon_months=horizon,
            observed_through=observed.isoformat(),
        )
        snapshot = build_panel(
            *tables,
            cutoffs=[cutoff],
            horizon_months=horizon,
            observed_through=observed.isoformat(),
            labeled=False,
        )
        forecast(panel, snapshot, directory, observed_through=observed.isoformat())
    metadata = {
        "created_at": datetime.now(UTC).isoformat(),
        "observed_through": observed.isoformat(),
        "cutoff_date": cutoff,
        "source_receipts": receipts,
        "ipl_matches": report["ipl_matches"],
        "last_ipl_match": tables[0].end_date.max(),
        "code_sha256": {p.name: sha256(p) for p in Path(__file__).parent.glob("*.py")},
        "input_sha256": {
            p.name: sha256(p) for p in sorted(data.iterdir()) if p.is_file()
        },
        "forecast_sha256": {
            str(p.relative_to(destination / "out/current")): sha256(p)
            for p in (destination / "out/current").glob("monthly_*m/*.csv")
        },
    }
    write_json(destination / "out/current/refresh.json", metadata)
    return metadata


def refresh(root, workspace=None):
    root = Path(root).resolve()
    with tempfile.TemporaryDirectory(prefix="national-selection-refresh-") as temporary:
        stage = Path(temporary)
        if workspace is None:
            workspace = stage / "sources"
            acquire(workspace)
        output = stage / "publication"
        metadata = build_current(root, workspace, output)
        for directory in ["data/current", "out/current"]:
            shutil.copytree(output / directory, root / directory, dirs_exist_ok=True)
        stamp = datetime.fromisoformat(metadata["created_at"]).strftime(
            "%Y%m%dT%H%M%S%fZ"
        )
        history = root / "out/history" / metadata["cutoff_date"] / stamp
        history.mkdir(parents=True, exist_ok=False)
        for horizon in [6, 12, 24]:
            shutil.copyfile(
                output / f"out/current/monthly_{horizon}m/forecast.csv",
                history / f"forecast_{horizon}m.csv",
            )
        write_json(history / "refresh.json", metadata)
        print(
            json.dumps(
                {
                    k: metadata[k]
                    for k in [
                        "observed_through",
                        "cutoff_date",
                        "ipl_matches",
                        "last_ipl_match",
                    ]
                },
                indent=2,
            )
        )
    return metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--workspace", type=Path, help="Reuse a verified acquisition with sources.json"
    )
    args = parser.parse_args()
    refresh(args.root, args.workspace)


if __name__ == "__main__":
    main()
