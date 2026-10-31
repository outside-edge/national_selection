import copy

import pandas as pd
import pytest

from national_selection.data import match_stats, resolve_name
from national_selection.features import FEATURES, TOTALS, build_panel
from national_selection.models import evaluate


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
        pd.DataFrame({"player_id": ["a", "b"], "known_from": ["2015-01-01"] * 2}),
        pd.DataFrame({"match_id": ["i"], "player_id": ["a"], "date": ["2017-12-31"]}),
        pd.DataFrame({"match_id": ["i"], "start_date": ["2017-12-31"]}),
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
    tables[2]["date"] = "2018-01-01"
    assert build_panel(*tables, first_year=2016, last_year=2016).selected.sum() == 0
    with pytest.raises(ValueError, match="Incomplete"):
        build_panel(
            *tables, first_year=2016, last_year=2016, observed_through="2017-12-30"
        )


def test_prior_international_and_future_eligibility_excluded():
    tables = inputs()
    tables[2]["date"] = "2015-12-20"
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
                    cutoff_date=f"{year}-01-01",
                    label_end=f"{year + 1}-12-31",
                    selected=number % 3 == 0,
                    n_matches=3 * (number % 3 == 0),
                    missing_outcome_matches=0,
                    **{f: number + year % 3 for f in FEATURES},
                )
            )
    evaluate(pd.DataFrame(rows), tmp_path)
    folds = pd.read_csv(tmp_path / "folds.csv")
    assert all(folds.train_last_label < folds.year.astype(str) + "-01-01")
    predictions = pd.read_csv(tmp_path / "predictions.csv")
    assert predictions[predictions.target == "selected"].prediction.between(0, 1).all()
    assert len(predictions) == 6 * 12 * 6


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
