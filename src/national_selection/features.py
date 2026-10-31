"""Build annual two-year forecasts using only completed pre-cutoff matches."""

import numpy as np
import pandas as pd

TOTALS = [
    "matches",
    "runs",
    "balls_faced",
    "dismissals",
    "wickets",
    "balls_bowled",
    "runs_conceded",
]
FEATURES = [
    f"{window}_{stat}"
    for window in ["career", "recent"]
    for stat in TOTALS
    + ["batting_average", "strike_rate", "bowling_average", "economy"]
] + ["days_since_last_match", "career_days"]


def summarize(frame, prefix):
    totals = frame[TOTALS].sum().to_dict()
    for name, numerator, denominator, multiplier in [
        ("batting_average", "runs", "dismissals", 1),
        ("strike_rate", "runs", "balls_faced", 100),
        ("bowling_average", "runs_conceded", "wickets", 1),
        ("economy", "runs_conceded", "balls_bowled", 6),
    ]:
        totals[name] = (
            multiplier * totals[numerator] / totals[denominator]
            if totals[denominator]
            else np.nan
        )
    return {f"{prefix}_{key}": value for key, value in totals.items()}


def build_panel(
    performances,
    eligibility,
    appearances,
    calendar,
    first_year=2010,
    last_year=2024,
    observed_through="2025-12-31",
    labeled=True,
):
    perf, eligible, apps = performances.copy(), eligibility.copy(), appearances.copy()
    for frame, field in [(perf, "end_date"), (eligible, "known_from"), (apps, "date")]:
        frame[field] = pd.to_datetime(frame[field])
    if perf.duplicated(["match_id", "player_id"]).any():
        raise ValueError("Duplicate performance row")
    if eligible.player_id.duplicated().any():
        raise ValueError("Duplicate eligibility row")
    if apps.duplicated(["match_id", "player_id"]).any():
        raise ValueError("Duplicate appearance row")
    for column in TOTALS:
        if perf[column].isna().any() or (perf[column] < 0).any():
            raise ValueError(f"Invalid totals: {column}")
    first = apps.groupby("player_id").date.min()
    known = eligible.set_index("player_id").known_from
    cal = calendar.copy()
    cal["start_date"] = pd.to_datetime(cal.start_date)
    missing = cal[~cal.match_id.astype(str).isin(apps.match_id.astype(str))]
    groups = {
        player: group.sort_values(["end_date", "match_id"])
        for player, group in perf.groupby("player_id")
    }
    rows = []
    for year in range(first_year, last_year + 1):
        cutoff = pd.Timestamp(year, 1, 1)
        horizon = cutoff + pd.DateOffset(years=2)
        if labeled and horizon - pd.Timedelta(days=1) > pd.Timestamp(observed_through):
            raise ValueError("Incomplete two-year label window")
        for player, history in groups.items():
            if (
                player not in known
                or known[player] > cutoff
                or (player in first and first[player] < cutoff)
            ):
                continue
            before = history[history.end_date < cutoff]
            recent = before[before.end_date >= cutoff - pd.DateOffset(years=2)]
            if recent.empty:
                continue
            future = apps[
                (apps.player_id == player)
                & (apps.date >= cutoff)
                & (apps.date < horizon)
            ]
            row = dict(
                player_id=player,
                player_name=before.iloc[-1].player_name,
                cutoff_date=cutoff.date().isoformat(),
                label_end=(horizon - pd.Timedelta(days=1)).date().isoformat(),
                selected=int(len(future) > 0) if labeled else np.nan,
                n_matches=len(future) if labeled else np.nan,
                missing_outcome_matches=int(
                    (
                        (missing.start_date >= cutoff) & (missing.start_date < horizon)
                    ).sum()
                ),
                days_since_last_match=(cutoff - before.end_date.max()).days,
                career_days=(cutoff - before.end_date.min()).days,
            )
            row.update(summarize(before, "career"))
            row.update(summarize(recent, "recent"))
            rows.append(row)
    result = pd.DataFrame(rows)
    if result.empty:
        raise ValueError("Empty risk set")
    return result
