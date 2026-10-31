"""Account for every observed IPL player before a forecast cutoff."""

import pandas as pd


def candidate_audit(performances, eligibility, appearances, prior, cutoff):
    cutoff = pd.Timestamp(cutoff)
    perf = performances.copy()
    perf["end_date"] = pd.to_datetime(perf.end_date)
    before = perf[perf.end_date < cutoff].sort_values(["end_date", "match_id"])
    audit = before.groupby("player_id", as_index=False).agg(
        player_name=("player_name", "last"), last_ipl_date=("end_date", "max")
    )
    known = eligibility[pd.to_datetime(eligibility.known_from) <= cutoff]
    countries = known.groupby("player_id").country.agg(lambda x: sorted(set(x)))

    def affiliation(values):
        if not isinstance(values, list):
            return "Unknown"
        if len(values) == 1:
            return values[0]
        return "Conflicting affiliations"

    audit["country"] = audit.player_id.map(countries).map(affiliation)
    caps = pd.concat([appearances[["player_id", "date"]], prior[["player_id", "date"]]])
    caps["date"] = pd.to_datetime(caps.date)
    caps = caps[caps.date < cutoff].groupby("player_id").date.min()
    audit["first_known_cap"] = audit.player_id.map(caps)
    supported = set(
        appearances.loc[pd.to_datetime(appearances.date) < cutoff, "country"]
    )
    audit["active"] = audit.last_ipl_date >= cutoff - pd.DateOffset(years=2)
    audit["prior_cap"] = audit.first_known_cap.notna()
    audit["supported"] = audit.country.isin(supported)
    audit["reason"] = "candidate"
    audit.loc[~audit.supported, "reason"] = "no_international_coverage"
    audit.loc[audit.prior_cap, "reason"] = "prior_international_appearance"
    audit.loc[audit.country.eq("Conflicting affiliations"), "reason"] = (
        "conflicting_affiliations"
    )
    audit.loc[audit.country.eq("Unknown"), "reason"] = "unknown_affiliation"
    audit.loc[~audit.active, "reason"] = "no_ipl_in_previous_24_months"
    audit["cutoff_date"] = cutoff.date().isoformat()
    return audit


def country_summary(audit):
    counts = audit.groupby("country").agg(
        observed_ipl_players=("player_id", "size"),
        active_ipl_players=("active", "sum"),
    )
    reasons = pd.crosstab(audit.country, audit.reason)
    return counts.join(reasons).fillna(0).astype(int).reset_index()
