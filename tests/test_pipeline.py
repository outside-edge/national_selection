import copy
from pathlib import Path

import pandas as pd
import pytest

from national_selection.data import (
    clean_appearances,
    match_stats,
    normalize,
    resolve_name,
)
from national_selection.features import FEATURES, TOTALS, build_panel
from national_selection.models import MODEL_INPUTS, evaluate, metrics, models


def inputs():
    rows = []
    for player in ["a", "b"]:
        row = dict(
            match_id="old",
            player_id=player,
            player_name=player,
            end_date="2015-12-01",
            **dict.fromkeys(TOTALS, 0),
        )
        row.update(matches=1, runs=50, balls_faced=30, dismissals=1)
        rows.append(row)
    return [
        pd.DataFrame(rows),
        pd.DataFrame(
            {
                "player_id": ["a", "b"],
                "known_from": ["2015-01-01"] * 2,
                "country": ["India", "Australia"],
            }
        ),
        pd.DataFrame(
            {
                "match_id": ["i", "past_i", "past_a"],
                "player_id": ["a", "other_i", "other_a"],
                "date": ["2017-12-31", "2010-01-01", "2010-01-01"],
                "country": ["India", "India", "Australia"],
            }
        ),
        pd.DataFrame(
            {"match_id": ["i"], "start_date": ["2017-12-31"], "country": ["India"]}
        ),
    ]


def test_future_matches_cannot_change_features():
    tables = inputs()
    before = build_panel(*tables, first_year=2016, last_year=2016)
    future = tables[0].iloc[[0]].copy()
    future["end_date"], future["match_id"], future["runs"] = "2016-01-01", "future", 999
    tables[0] = pd.concat([tables[0], future])
    after = build_panel(*tables, first_year=2016, last_year=2016)
    pd.testing.assert_frame_equal(before[FEATURES], after[FEATURES])


def test_two_year_boundary_and_censoring():
    tables = inputs()
    panel = build_panel(*tables, first_year=2016, last_year=2016)
    assert panel.set_index("player_id").selected.to_dict() == {"a": 1, "b": 0}
    tables[2].loc[0, "date"] = "2018-01-01"
    assert build_panel(*tables, first_year=2016, last_year=2016).selected.sum() == 0
    with pytest.raises(ValueError, match="Incomplete"):
        build_panel(
            *tables, first_year=2016, last_year=2016, observed_through="2017-12-30"
        )


def test_prior_international_and_future_eligibility_excluded():
    tables = inputs()
    tables[2].loc[0, "date"] = "2015-12-20"
    panel = build_panel(*tables, first_year=2016, last_year=2016)
    assert panel.player_id.tolist() == ["b"]
    tables[1].loc[tables[1].player_id == "b", "known_from"] = "2016-01-02"
    with pytest.raises(ValueError, match="Empty risk"):
        build_panel(*tables, first_year=2016, last_year=2016)


def test_duplicate_and_negative_stats_rejected():
    tables = inputs()
    tables[0] = pd.concat([tables[0], tables[0].iloc[[0]]])
    with pytest.raises(ValueError, match="Duplicate"):
        build_panel(*tables, first_year=2016, last_year=2016)
    tables = inputs()
    tables[0].loc[0, "wickets"] = -1
    with pytest.raises(ValueError, match="Invalid totals"):
        build_panel(*tables, first_year=2016, last_year=2016)


def test_delivery_accounting_and_dnb():
    info = dict(
        players={"x": ["A", "C"], "y": ["B"]},
        registry={"people": {"A": "a", "B": "b", "C": "c"}},
        dates=["2020-01-01"],
    )
    ball = dict(
        batter="A", bowler="B", runs={"batter": 0, "total": 2}, extras={"wides": 2}
    )
    runout = dict(
        batter="A",
        bowler="B",
        runs={"batter": 0, "total": 1},
        extras={"legbyes": 1},
        wickets=[{"player_out": "A", "kind": "run out"}],
    )
    data = {"info": info, "innings": [{"overs": [{"deliveries": [ball, runout]}]}]}
    result = {r["player_id"]: r for r in match_stats(data, "m")}
    assert result["a"]["balls_faced"] == 1
    assert result["a"]["dismissals"] == 1
    assert result["b"]["balls_bowled"] == 1
    assert result["b"]["runs_conceded"] == 2
    assert result["b"]["wickets"] == 0
    assert result["c"]["matches"] == 1 and result["c"]["dismissals"] == 0
    extra = copy.deepcopy(data["innings"][0])
    extra["super_over"] = True
    data["innings"].append(extra)
    assert match_stats(data, "m") == list(result.values())


def test_evaluation_matures_labels_and_preserves_predictions(tmp_path):
    rows = []
    for year in range(2010, 2025):
        for number in range(12):
            rows.append(
                dict(
                    player_id=str(number),
                    player_name=str(number),
                    country="India" if number < 8 else "Australia",
                    cutoff_date=f"{year}-01-01",
                    label_end=f"{year + 1}-12-31",
                    selected=number % 3 == 0,
                    n_matches=3 * (number % 3 == 0),
                    missing_affiliation_matches=0,
                    **{f: number + year % 3 for f in FEATURES},
                )
            )
    evaluate(pd.DataFrame(rows), tmp_path)
    folds = pd.read_csv(tmp_path / "folds.csv")
    assert all(folds.train_last_label < folds.year.astype(str) + "-01-01")
    predictions = pd.read_csv(tmp_path / "predictions.csv")
    assert predictions[predictions.target == "selected"].prediction.between(0, 1).all()
    assert len(predictions) == 6 * 12 * len(models())


def test_identity_override_prevents_initials_collision():
    direct = {"ravibishnoi": {"ravi"}, "rbishnoi": {"rajesh"}}
    aliases = {"ravibishnoi": {"ravi", "rajesh"}}
    ids, method = resolve_name("Ravi Bishnoi", direct, aliases, {})
    assert ids == {"ravi"} and method == "exact_scorecard_name"
    ids, method = resolve_name(
        "Ravi Bishnoi", direct, aliases, {"ravibishnoi": "ravibishnoi"}
    )
    assert ids == {"ravi"} and method == "reviewed_name_link"


def test_unlabeled_forecast_has_no_fake_outcome():
    panel = build_panel(
        *inputs(),
        first_year=2016,
        last_year=2016,
        observed_through="2015-12-31",
        labeled=False,
    )
    assert panel.selected.isna().all() and panel.n_matches.isna().all()


def test_country_switch_is_not_a_new_debut_and_gaps_are_country_specific():
    tables = inputs()
    tables[2].loc[0, "country"] = "South Africa"
    tables[2].loc[0, "date"] = "2015-12-20"
    panel = build_panel(*tables, first_year=2016, last_year=2016)
    assert panel.player_id.tolist() == ["b"]
    assert panel.missing_affiliation_matches.tolist() == [0]
    tables[2].loc[0, "date"] = "2017-01-01"
    panel = build_panel(*tables, first_year=2016, last_year=2016).set_index("player_id")
    assert panel.loc["a", "selected"] == 1
    assert panel.loc["a", "country"] == "India"
    assert panel.loc["a", "missing_affiliation_matches"] == 1
    assert panel.loc["b", "missing_affiliation_matches"] == 0


def test_future_conflicting_affiliation_cannot_change_earlier_risk_set():
    tables = inputs()
    before = build_panel(*tables, first_year=2016, last_year=2016)
    conflict = pd.DataFrame(
        [dict(player_id="a", country="England", known_from="2017-01-01")]
    )
    tables[1] = pd.concat([tables[1], conflict], ignore_index=True)
    after = build_panel(*tables, first_year=2016, last_year=2016)
    pd.testing.assert_frame_equal(before, after)
    tables[0]["end_date"] = "2016-12-01"
    assert build_panel(*tables, first_year=2017, last_year=2017).player_id.tolist() == [
        "b"
    ]


def test_unseen_country_and_performance_ablation():
    x = pd.DataFrame(
        [
            {**dict.fromkeys(FEATURES, n), "country": "India" if n < 6 else "Australia"}
            for n in range(12)
        ]
    )
    y = pd.Series([0, 1] * 6)
    model, _ = models()["country_only"]
    model.fit(x[MODEL_INPUTS], y)
    future = x.iloc[[0]].copy()
    future["country"] = "New Zealand"
    original = model.predict_proba(future)
    future[FEATURES] = 10000
    assert (model.predict_proba(future) == original).all()
    for name in ["logistic_country", "boosting_country", "poisson_country"]:
        estimator, _ = models()[name]
        estimator.fit(x, y)
        assert pd.notna(estimator.predict(future)).all()


def test_rankings_use_separate_national_pools():
    rows = [
        dict(
            player_id=str(i),
            cutoff_date="2022-01-01",
            country="India" if i < 10 else "Australia",
            target="selected",
            actual=int(i >= 10),
            prediction=0.9 if i < 10 else 0.1,
        )
        for i in range(20)
    ]
    result = metrics(pd.DataFrame(rows))
    assert result["precision_at_10"] == 0.5
    assert result["recall_at_10"] == 1


def test_finn_and_fabian_are_not_the_same_person():
    direct = {"faallen": {"fabian"}}
    aliases = {"finnallen": {"fabian"}}
    ids, _ = resolve_name("Finn Allen", direct, aliases, {"finnallen": "finnallen"})
    assert ids == set()


def test_no_appearance_coverage_does_not_create_negative_labels():
    tables = inputs()
    tables[1].loc[1, "country"] = "Afghanistan"
    panel = build_panel(*tables, first_year=2016, last_year=2016)
    assert panel.player_id.tolist() == ["a"]
    future_coverage = pd.DataFrame(
        [
            dict(
                match_id="f",
                player_id="other",
                country="Afghanistan",
                date="2016-12-01",
            )
        ]
    )
    tables[2] = pd.concat([tables[2], future_coverage], ignore_index=True)
    assert build_panel(*tables, first_year=2016, last_year=2016).player_id.tolist() == [
        "a"
    ]


@pytest.mark.parametrize(
    "auction_name,scorecard_name,expected",
    [
        ("Aryaman Birla", "UA Birla", set()),
        ("Ansh Patel", "AR Patel", set()),
        ("Kuldip Yadav", "K Yadav", {"distinct"}),
    ],
)
def test_packaged_identity_links_block_known_false_merges(
    auction_name, scorecard_name, expected
):
    reference = pd.read_csv(
        Path(__file__).parents[1] / "src/national_selection/reference/name_links.csv"
    )
    overrides = {
        normalize(r.auction_name): normalize(r.scorecard_name)
        for r in reference.itertuples()
    }
    direct = {normalize(scorecard_name): {"distinct"}}
    aliases = {normalize(auction_name): {"wrong"}}
    ids, _ = resolve_name(auction_name, direct, aliases, overrides)
    assert ids == expected


def test_independent_prior_cap_excludes_false_uncapped_candidate():
    prior = pd.DataFrame([dict(player_id="b", date="2015-12-30")])
    panel = build_panel(
        *inputs(), prior_appearances=prior, first_year=2016, last_year=2016
    )
    assert panel.player_id.tolist() == ["a"]
    prior["date"] = "2016-01-02"
    assert build_panel(
        *inputs(), prior_appearances=prior, first_year=2016, last_year=2016
    ).player_id.tolist() == ["a", "b"]


def test_inconsistent_registry_quarantines_both_entire_teams():
    rows = pd.DataFrame(
        [
            dict(match_id="bad", player_id="a", country="X"),
            dict(match_id="bad", player_id="a", country="Y"),
            dict(match_id="bad", player_id="b", country="Y"),
            dict(match_id="good", player_id="a", country="X"),
        ]
    )
    clean, audit = clean_appearances(rows)
    assert clean.match_id.tolist() == ["good"]
    assert audit.country.tolist() == ["X", "Y"]
