"""Import existing archives with explicit identity and coverage audits."""

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

NON_BOWLER_WICKETS = {"run out", "retired hurt", "obstructing the field", "retired out"}


COUNTRY_NAMES = {
    "UAE": "United Arab Emirates",
    "U.A.E.": "United Arab Emirates",
    "U.S.A.": "United States of America",
    "P.N.G.": "Papua New Guinea",
    "Cayman": "Cayman Islands",
    "Czech Rep.": "Czech Republic",
    "Turks and C.": "Turks and Caicos Island",
    "World-XI": "ICC World XI",
}


def country_name(name):
    return COUNTRY_NAMES.get(name, name)


def normalize(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def resolve_name(name, direct_ids, alias_ids, overrides):
    key = normalize(name)
    if key in overrides:
        return direct_ids.get(overrides[key], set()), "reviewed_name_link"
    if len(direct_ids.get(key, set())) == 1:
        return direct_ids[key], "exact_scorecard_name"
    return alias_ids.get(key, set()), "sibling_alias"


def match_stats(data, match_id):
    info = data["info"]
    registry = info["registry"]["people"]
    rows = {}
    for team, names in info["players"].items():
        for name in names:
            player_id = registry[name]
            if player_id in rows:
                raise ValueError("Player appears in both teams")
            rows[player_id] = dict(
                match_id=str(match_id),
                player_id=player_id,
                player_name=name,
                team=team,
                end_date=max(info["dates"]),
                matches=1,
                runs=0,
                balls_faced=0,
                dismissals=0,
                wickets=0,
                balls_bowled=0,
                runs_conceded=0,
            )
    for innings in data["innings"]:
        if innings.get("super_over", False):
            continue
        for over in innings["overs"]:
            for ball in over["deliveries"]:
                batter = rows[registry[ball["batter"]]]
                bowler = rows[registry[ball["bowler"]]]
                extras = ball.get("extras", {})
                batter["runs"] += ball["runs"]["batter"]
                batter["balls_faced"] += int(not extras.get("wides", 0))
                bowler["balls_bowled"] += int(
                    not extras.get("wides", 0) and not extras.get("noballs", 0)
                )
                bowler["runs_conceded"] += (
                    ball["runs"]["total"]
                    - extras.get("byes", 0)
                    - extras.get("legbyes", 0)
                    - extras.get("penalty", 0)
                )
                for wicket in ball.get("wickets", []):
                    if wicket["kind"] != "retired hurt":
                        rows[registry[wicket["player_out"]]]["dismissals"] += 1
                    if wicket["kind"] not in NON_BOWLER_WICKETS:
                        bowler["wickets"] += 1
    return list(rows.values())


def clean_appearances(appearances):
    """Quarantine entire matches with duplicate player IDs, preserving evidence."""
    inconsistent = appearances[
        appearances.duplicated(["match_id", "player_id"], keep=False)
    ].copy()
    clean = appearances[~appearances.match_id.isin(inconsistent.match_id)].copy()
    return clean, inconsistent


def import_local(workspace, destination, *, observed_through="2025-12-31"):
    observed_through = pd.Timestamp(observed_through).date().isoformat()
    workspace, destination = Path(workspace), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    receipts = []

    def record(path):
        receipts.append(
            {
                "path": str(path.relative_to(workspace)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    source = (
        workspace / "ipl_auction/data/perf/sources/kaggle/ipl-dataset/json/ipl_match"
    )
    rows, name_ids = [], defaultdict(set)
    for path in sorted(source.glob("*.json")):
        data = json.loads(path.read_text())
        info = data["info"]
        if max(info["dates"]) > observed_through:
            continue
        if info["gender"] != "male" or info["match_type"] != "T20":
            raise ValueError(f"Unexpected competition: {path}")
        record(path)
        for team in info["players"].values():
            for name in team:
                name_ids[normalize(name)].add(info["registry"]["people"][name])
        rows.extend(match_stats(data, path.stem))
    stats = pd.DataFrame(rows)
    if stats.empty or stats.duplicated(["match_id", "player_id"]).any():
        raise ValueError("Empty or duplicated IPL appearances")

    registry_path = workspace / "ipl_auction/data/acquisitions/player_registry.csv"
    aliases_path = workspace / "ipl_auction/data/acquisitions/name_aliases.csv"
    nationality_path = (
        workspace / "ipl_auction/data/acquisitions/sources/clod/ipl_2008_2026.csv"
    )
    for path in [registry_path, aliases_path, nationality_path]:
        record(path)
    direct_ids = {name: ids.copy() for name, ids in name_ids.items()}
    reference = Path(__file__).parent / "reference/name_links.csv"
    receipts.append(
        {
            "path": "src/national_selection/reference/name_links.csv",
            "sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
        }
    )
    prior_reference = Path(__file__).parent / "reference/prior_appearances.csv"
    receipts.append(
        {
            "path": "src/national_selection/reference/prior_appearances.csv",
            "sha256": hashlib.sha256(prior_reference.read_bytes()).hexdigest(),
        }
    )
    prior = pd.read_csv(prior_reference, dtype={"player_id": str})
    if (
        prior.player_id.duplicated().any()
        or not prior.player_id.isin(stats.player_id).all()
    ):
        raise ValueError("Invalid prior-appearance reference IDs")
    prior.to_csv(destination / "prior_appearances.csv", index=False)
    overrides = {
        normalize(r.auction_name): normalize(r.scorecard_name)
        for r in pd.read_csv(reference).itertuples()
    }
    groups = []
    for row in pd.read_csv(registry_path).itertuples():
        groups.append(
            {normalize(row.canonical_name)}
            | {normalize(n) for n in str(row.aliases).split("|")}
        )
    for row in pd.read_csv(aliases_path).itertuples():
        groups.append({normalize(row.auction_name), normalize(row.performance_name)})
    # Alias connectivity is identity metadata, never a predictive feature.
    changed = True
    while changed:
        changed = False
        for group in groups:
            ids = set().union(*(name_ids[n] for n in group))
            for name in group:
                if not ids.issubset(name_ids[name]):
                    name_ids[name].update(ids)
                    changed = True

    crosswalk = []
    for row in pd.read_csv(registry_path).itertuples():
        ids, method = resolve_name(row.canonical_name, direct_ids, name_ids, overrides)
        crosswalk.append(
            dict(
                auction_player_id=row.player_id,
                auction_name=row.canonical_name,
                player_id=next(iter(ids)) if len(ids) == 1 else None,
                method=method,
                candidates=len(ids),
            )
        )
    pd.DataFrame(crosswalk).to_csv(destination / "player_crosswalk.csv", index=False)
    nationality = pd.read_csv(nationality_path)
    nationality = nationality[nationality.year <= int(observed_through[:4])]
    linked, unresolved = [], []
    for row in nationality.itertuples():
        ids, method = resolve_name(row.player, direct_ids, name_ids, overrides)
        if len(ids) != 1:
            unresolved.append(
                {
                    "year": row.year,
                    "name": row.player,
                    "nationality": row.nationality,
                    "candidates": len(ids),
                }
            )
            continue
        linked.append(
            {
                "player_id": next(iter(ids)),
                "source_name": row.player,
                "link_method": method,
                "nationality": country_name(row.nationality),
                "known_from": f"{row.year + 1}-01-01",
            }
        )
    links = pd.DataFrame(linked)
    links.to_csv(destination / "nationality_links.csv", index=False)
    conflicts = links.groupby("player_id").nationality.nunique()
    conflicted = links[links.player_id.isin(conflicts[conflicts > 1].index)]
    conflicted.to_csv(destination / "nationality_conflicts.csv", index=False)
    eligibility = (
        links.rename(columns={"nationality": "country"})
        .groupby(["player_id", "country"], as_index=False)
        .known_from.min()
    )
    eligibility.to_csv(destination / "eligibility.csv", index=False)
    pd.DataFrame(unresolved).to_csv(
        destination / "unresolved_nationality.csv", index=False
    )

    calendar_path = workspace / "side_order/data/build/matches.csv"
    record(calendar_path)
    calendar = pd.read_csv(calendar_path, dtype={"match_id": str})
    calendar = calendar[(calendar["format"].isin(["Test", "ODI", "T20I"]))]
    calendar = calendar[
        (calendar.start_date >= "2008-01-01")
        & (calendar.start_date <= observed_through)
    ]
    calendar = calendar.melt(
        id_vars=["match_id", "format", "start_date", "end_date"],
        value_vars=["team1", "team2"],
        value_name="country",
    ).drop(columns="variable")
    calendar["country"] = calendar.country.map(country_name)
    calendar = calendar.drop_duplicates(["match_id", "country"])
    appearance_rows = []
    for folder in ["tests", "odis", "t20is"]:
        for path in sorted(
            (workspace / f"war/data/raw/cricsheet/{folder}").glob("*.json")
        ):
            if not path.stem.isdigit():
                continue
            info = json.loads(path.read_text())["info"]
            if (
                info["gender"] != "male"
                or info.get("team_type") != "international"
                or min(info["dates"]) > observed_through
            ):
                continue
            record(path)
            for team, names in info["players"].items():
                for name in names:
                    appearance_rows.append(
                        dict(
                            match_id=path.stem,
                            player_id=info["registry"]["people"][name],
                            player_name=name,
                            country=country_name(team),
                            date=min(info["dates"]),
                            format=info["match_type"],
                        )
                    )
    appearances = pd.DataFrame(appearance_rows)
    appearances, inconsistent = clean_appearances(appearances)
    inconsistent.to_csv(destination / "inconsistent_appearances.csv", index=False)
    first = (
        appearances.groupby("player_id", as_index=False)
        .date.min()
        .rename(columns={"date": "first_recorded_date"})
    )
    first.to_csv(destination / "first_recorded_appearances.csv", index=False)
    appearances.to_csv(destination / "international_appearances.csv", index=False)
    observed = appearances[["match_id", "country"]].drop_duplicates()
    coverage_calendar = calendar.merge(
        observed,
        on=["match_id", "country"],
        how="left",
        indicator=True,
        validate="one_to_one",
    )
    coverage_calendar["missing"] = coverage_calendar._merge == "left_only"
    coverage_calendar["year"] = coverage_calendar.start_date.str[:4]
    coverage_calendar.groupby(["country", "format", "year"]).agg(
        calendar_matches=("match_id", "size"), missing_matches=("missing", "sum")
    ).reset_index().to_csv(
        destination / "international_coverage_by_country.csv", index=False
    )
    unsupported = eligibility[~eligibility.country.isin(appearances.country)]
    unsupported = (
        unsupported.groupby("country")
        .agg(players=("player_id", "nunique"))
        .reset_index()
    )
    unsupported["reason"] = (
        "No international appearance coverage; omitted from risk sets"
    )
    unsupported.to_csv(destination / "unsupported_affiliations.csv", index=False)
    missing = coverage_calendar[coverage_calendar._merge == "left_only"].drop(
        columns=["_merge", "missing", "year"]
    )
    missing.to_csv(destination / "missing_internationals.csv", index=False)
    calendar.to_csv(destination / "calendar.csv", index=False)
    stats.to_csv(destination / "performances.csv", index=False)
    master = (
        stats.sort_values(["end_date", "match_id"])
        .groupby("player_id")
        .agg(
            player_name=("player_name", "last"),
            first_ipl_date=("end_date", "min"),
            last_ipl_date=("end_date", "max"),
            ipl_matches=("match_id", "nunique"),
        )
        .reset_index()
    )
    affiliations = eligibility.groupby("player_id", as_index=False).agg(
        countries=("country", lambda x: "|".join(sorted(x))),
        known_from=("known_from", "min"),
    )
    master = master.merge(
        affiliations, on="player_id", how="left", validate="one_to_one"
    )
    master = master.merge(first, on="player_id", how="left", validate="one_to_one")
    master.to_csv(destination / "players.csv", index=False)
    coverage = stats[["player_id", "end_date"]].copy()
    coverage["year"] = coverage.end_date.str[:4].astype(int)
    coverage = coverage.drop_duplicates(["year", "player_id"])
    linked_ids = set(links.player_id)
    coverage["nationality_resolved"] = coverage.player_id.isin(linked_ids)
    first_known = eligibility.groupby("player_id").known_from.min()
    coverage["affiliation_known_next_january"] = (
        coverage.player_id.map(first_known)
        <= (coverage.year + 1).astype(str) + "-01-01"
    )
    coverage.groupby("year").agg(
        players=("player_id", "size"),
        nationality_resolved=("nationality_resolved", "sum"),
        affiliation_known_next_january=("affiliation_known_next_january", "sum"),
    ).to_csv(destination / "linkage_by_year.csv")
    unmatched = master[~master.player_id.isin(linked_ids)]
    unmatched.to_csv(destination / "unlinked_players.csv", index=False)

    report = {
        "source_files": receipts,
        "observed_through": observed_through,
        "ipl_matches": int(stats.match_id.nunique()),
        "ipl_players": int(stats.player_id.nunique()),
        "nationality_linked_players": int(links.player_id.nunique()),
        "players_by_affiliation": eligibility.groupby("country")
        .player_id.nunique()
        .to_dict(),
        "unresolved_nationality_rows": len(unresolved),
        "international_calendar_matches": int(calendar.match_id.nunique()),
        "missing_internationals": missing[
            ["match_id", "country", "format", "start_date"]
        ].to_dict("records"),
        "label_caveat": (
            "First recorded appearance, not certified debut. "
            "Match counts are observed lower bounds; gaps are exported."
        ),
        "nationality_timing": (
            "Auction nationality is a proxy for affiliation, not verified eligibility. "
            "Affiliation begins January 1 after the recorded season; "
            "no future nationality cohort filter."
        ),
    }
    (destination / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
