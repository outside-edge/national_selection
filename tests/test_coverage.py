import pandas as pd

from national_selection.coverage import candidate_audit, country_summary


def test_country_counts_keep_capped_inactive_and_unresolved_players():
    names = ["capped", "candidate", "inactive", "unknown", "unsupported", "conflict"]
    perf = pd.DataFrame(
        {
            "player_id": names,
            "player_name": names,
            "match_id": ["m"] * 6,
            "end_date": [
                "2025-05-01",
                "2025-05-01",
                "2023-12-31",
                "2025-05-01",
                "2025-05-01",
                "2025-05-01",
            ],
        }
    )
    eligible = pd.DataFrame(
        {
            "player_id": [
                "capped",
                "candidate",
                "inactive",
                "unsupported",
                "conflict",
                "conflict",
                "unknown",
            ],
            "country": [
                "Australia",
                "India",
                "Australia",
                "Afghanistan",
                "India",
                "England",
                "India",
            ],
            "known_from": ["2024-01-01"] * 6 + ["2027-01-01"],
        }
    )
    apps = pd.DataFrame(
        {
            "player_id": ["capped", "other", "candidate"],
            "country": ["Australia", "India", "India"],
            "date": ["2024-01-01", "2020-01-01", "2026-02-01"],
        }
    )
    prior = pd.DataFrame(columns=["player_id", "date"])
    audit = candidate_audit(perf, eligible, apps, prior, "2026-01-01")
    assert audit.set_index("player_id").reason.to_dict() == {
        "capped": "prior_international_appearance",
        "candidate": "candidate",
        "inactive": "no_ipl_in_previous_24_months",
        "unknown": "unknown_affiliation",
        "unsupported": "no_international_coverage",
        "conflict": "conflicting_affiliations",
    }
    summary = country_summary(audit).set_index("country")
    assert summary.loc["Australia", "observed_ipl_players"] == 2
    assert summary.loc["Australia", "active_ipl_players"] == 1
    assert summary.loc["Australia", "candidate"] == 0
    assert summary.candidate.sum() == 1
    assert summary.observed_ipl_players.sum() == len(perf)


def test_caps_from_another_country_and_verified_caps_exclude():
    perf = pd.DataFrame(
        {
            "player_id": ["a", "b"],
            "player_name": ["A", "B"],
            "match_id": ["m", "m"],
            "end_date": ["2025-01-01"] * 2,
        }
    )
    eligible = pd.DataFrame(
        {
            "player_id": ["a", "b"],
            "country": ["Australia"] * 2,
            "known_from": ["2020-01-01"] * 2,
        }
    )
    apps = pd.DataFrame(
        {
            "player_id": ["a", "other"],
            "country": ["Singapore", "Australia"],
            "date": ["2019-01-01"] * 2,
        }
    )
    prior = pd.DataFrame({"player_id": ["b"], "date": ["2018-01-01"]})
    audit = candidate_audit(perf, eligible, apps, prior, "2026-01-01")
    assert audit.reason.eq("prior_international_appearance").all()
