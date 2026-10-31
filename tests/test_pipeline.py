import copy
from pathlib import Path

import pandas as pd
import pytest

from national_selection.backtest import january_comparison
from national_selection.cli import mature_cutoffs
from national_selection.data import (
    clean_appearances,
    match_stats,
    normalize,
    resolve_name,
)
from national_selection.features import FEATURES, TOTALS, build_panel
from national_selection.models import MODEL_INPUTS, evaluate, metrics, models


def annual_panel(*args, first_year=2010, last_year=2024, **kwargs):
    return build_panel(
        *args,
        cutoffs=[f"{y}-01-01" for y in range(first_year, last_year + 1)],
        horizon_months=24,
        **kwargs,
    )


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
    before = annual_panel(*tables, first_year=2016, last_year=2016)
    future = tables[0].iloc[[0]].copy()
    future["end_date"], future["match_id"], future["runs"] = "2016-01-01", "future", 999
    tables[0] = pd.concat([tables[0], future])
    after = annual_panel(*tables, first_year=2016, last_year=2016)
    pd.testing.assert_frame_equal(before[FEATURES], after[FEATURES])


def test_two_year_boundary_and_censoring():
    tables = inputs()
    panel = annual_panel(*tables, first_year=2016, last_year=2016)
    assert panel.set_index("player_id").selected.to_dict() == {"a": 1, "b": 0}
    tables[2].loc[0, "date"] = "2018-01-01"
    assert annual_panel(*tables, first_year=2016, last_year=2016).selected.sum() == 0
    with pytest.raises(ValueError, match="Incomplete"):
        annual_panel(
            *tables, first_year=2016, last_year=2016, observed_through="2017-12-30"
        )


def test_prior_international_and_future_eligibility_excluded():
    tables = inputs()
    tables[2].loc[0, "date"] = "2015-12-20"
    panel = annual_panel(*tables, first_year=2016, last_year=2016)
    assert panel.player_id.tolist() == ["b"]
    tables[1].loc[tables[1].player_id == "b", "known_from"] = "2016-01-02"
    with pytest.raises(ValueError, match="Empty risk"):
        annual_panel(*tables, first_year=2016, last_year=2016)


def test_duplicate_and_negative_stats_rejected():
    tables = inputs()
    tables[0] = pd.concat([tables[0], tables[0].iloc[[0]]])
    with pytest.raises(ValueError, match="Duplicate"):
        annual_panel(*tables, first_year=2016, last_year=2016)
    tables = inputs()
    tables[0].loc[0, "wickets"] = -1
    with pytest.raises(ValueError, match="Invalid totals"):
        annual_panel(*tables, first_year=2016, last_year=2016)


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
                    calendar_month=1,
                    horizon_months=24,
                    event_date=None,
                    cutoff_date=f"{year}-01-01",
                    label_end=f"{year + 1}-12-31",
                    selected=number % 3 == 0,
                    n_matches=3 * (number % 3 == 0),
                    missing_affiliation_matches=0,
                    **{f: number + year % 3 for f in FEATURES},
                )
            )
    annual_rows = pd.DataFrame(rows)
    summer = annual_rows.copy()
    summer["cutoff_date"] = summer.cutoff_date.str.replace("-01-01", "-06-01")
    summer["label_end"] = (
        pd.to_datetime(summer.cutoff_date)
        + pd.DateOffset(months=24)
        - pd.Timedelta(days=1)
    ).dt.strftime("%Y-%m-%d")
    summer["calendar_month"] = 6
    panel = pd.concat([annual_rows, summer], ignore_index=True)
    evaluate(panel, tmp_path)
    folds = pd.read_csv(tmp_path / "folds.csv")
    assert all(folds.train_last_label < folds.fit_date)
    predictions = pd.read_csv(tmp_path / "predictions.csv")
    assert (predictions.fit_date == predictions.cutoff_date.str[:4] + "-01-01").all()
    assert predictions[predictions.target == "selected"].prediction.between(0, 1).all()
    assert len(predictions) == 6 * 12 * 2 * len(models())
    baseline = predictions[
        (predictions.model == "base_rate")
        & predictions.cutoff_date.str.startswith("2022")
    ]
    expected = panel.loc[panel.label_end < "2022-01-01", "selected"].mean()
    assert baseline.prediction.tolist() == pytest.approx([expected] * len(baseline))
    annual_dir = tmp_path / "annual"
    evaluate(panel, annual_dir, cadence="annual")
    annual_predictions = pd.read_csv(annual_dir / "predictions.csv")
    comparison = january_comparison(predictions, annual_predictions)
    assert len(comparison) == 2 * len(models())
    with pytest.raises(ValueError, match="identical candidate"):
        january_comparison(
            predictions,
            annual_predictions.drop(
                annual_predictions[annual_predictions.phase == "test"].index[0]
            ),
        )


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
    panel = annual_panel(
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
    panel = annual_panel(*tables, first_year=2016, last_year=2016)
    assert panel.player_id.tolist() == ["b"]
    assert panel.missing_affiliation_matches.tolist() == [0]
    tables[2].loc[0, "date"] = "2017-01-01"
    panel = annual_panel(*tables, first_year=2016, last_year=2016).set_index(
        "player_id"
    )
    assert panel.loc["a", "selected"] == 1
    assert panel.loc["a", "country"] == "India"
    assert panel.loc["a", "missing_affiliation_matches"] == 1
    assert panel.loc["b", "missing_affiliation_matches"] == 0


def test_future_conflicting_affiliation_cannot_change_earlier_risk_set():
    tables = inputs()
    before = annual_panel(*tables, first_year=2016, last_year=2016)
    conflict = pd.DataFrame(
        [dict(player_id="a", country="England", known_from="2017-01-01")]
    )
    tables[1] = pd.concat([tables[1], conflict], ignore_index=True)
    after = annual_panel(*tables, first_year=2016, last_year=2016)
    pd.testing.assert_frame_equal(before, after)
    tables[0]["end_date"] = "2016-12-01"
    assert annual_panel(
        *tables, first_year=2017, last_year=2017
    ).player_id.tolist() == ["b"]


def test_unseen_country_and_performance_ablation():
    x = pd.DataFrame(
        [
            {
                **dict.fromkeys(FEATURES, n),
                "country": "India" if n < 6 else "Australia",
                "calendar_month": 1,
            }
            for n in range(12)
        ]
    )
    y = pd.Series([0, 1] * 6)
    model, _ = models()["context_only"]
    model.fit(x[MODEL_INPUTS], y)
    future = x.iloc[[0]].copy()
    future["country"] = "New Zealand"
    original = model.predict_proba(future)
    future[FEATURES] = 10000
    assert (model.predict_proba(future) == original).all()
    for name in ["logistic_context", "boosting_context", "poisson_context"]:
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
    panel = annual_panel(*tables, first_year=2016, last_year=2016)
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
    assert annual_panel(
        *tables, first_year=2016, last_year=2016
    ).player_id.tolist() == ["a"]


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
    panel = annual_panel(
        *inputs(), prior_appearances=prior, first_year=2016, last_year=2016
    )
    assert panel.player_id.tolist() == ["a"]
    prior["date"] = "2016-01-02"
    assert annual_panel(
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


@pytest.mark.parametrize("horizon", [6, 12, 24])
def test_monthly_horizon_boundary_and_mature_cutoffs(horizon):
    tables = inputs()
    cutoff = pd.Timestamp("2016-02-01")
    end = cutoff + pd.DateOffset(months=horizon)
    tables[2].loc[0, "date"] = (end - pd.Timedelta(days=1)).date().isoformat()
    panel = build_panel(*tables, cutoffs=[cutoff], horizon_months=horizon)
    assert panel.set_index("player_id").loc["a", "selected"] == 1
    assert panel.label_end.unique().tolist() == [
        (end - pd.Timedelta(days=1)).date().isoformat()
    ]
    tables[2].loc[0, "date"] = end.date().isoformat()
    assert (
        build_panel(*tables, cutoffs=[cutoff], horizon_months=horizon).selected.sum()
        == 0
    )
    dates = mature_cutoffs(horizon, "2025-12-31")
    assert (dates[-1] + pd.DateOffset(months=horizon)) == pd.Timestamp("2026-01-01")
    with pytest.raises(ValueError, match="Incomplete"):
        build_panel(
            *tables,
            cutoffs=[cutoff],
            horizon_months=horizon,
            observed_through=(end - pd.Timedelta(days=2)).date().isoformat(),
        )


def test_month_end_leap_year_and_completed_match_cutoffs():
    tables = inputs()
    tables[2].loc[0, "date"] = "2016-02-28"
    new = tables[0].iloc[[0]].copy()
    new["match_id"], new["end_date"], new["runs"] = "new", "2016-01-31", 1000
    tables[0] = pd.concat([tables[0], new], ignore_index=True)
    panel = build_panel(*tables, cutoffs=["2016-01-31", "2016-02-01"], horizon_months=1)
    player = panel[panel.player_id == "a"].set_index("cutoff_date")
    assert player.loc["2016-01-31", "label_end"] == "2016-02-28"
    assert player.loc["2016-01-31", "career_runs"] == 50
    assert player.loc["2016-02-01", "career_runs"] == 1050
    assert player.selected.tolist() == [1, 1]


def test_verified_appearance_is_a_positive_label_and_not_double_counted():
    tables = inputs()
    prior = pd.DataFrame([dict(player_id="b", date="2016-06-01")])
    panel = build_panel(
        *tables, prior_appearances=prior, cutoffs=["2016-01-01"], horizon_months=12
    )
    assert panel.set_index("player_id").loc["b", "n_matches"] == 1
    tables[2] = pd.concat(
        [
            tables[2],
            pd.DataFrame(
                [
                    dict(
                        player_id="b",
                        date="2016-06-01",
                        country="Australia",
                        match_id="v",
                    )
                ]
            ),
        ],
        ignore_index=True,
    )
    after = build_panel(
        *tables,
        prior_appearances=prior,
        cutoffs=["2016-01-01", "2016-07-01"],
        horizon_months=12,
    )
    assert after[
        (after.player_id == "b") & (after.cutoff_date == "2016-01-01")
    ].n_matches.tolist() == [1]
    assert "b" not in set(after.loc[after.cutoff_date == "2016-07-01", "player_id"])


def test_equal_player_weights_are_computed_within_the_evaluation_slice():
    frame = pd.DataFrame(
        [
            dict(
                player_id="a",
                country="India",
                cutoff_date=f"2022-{m:02d}-01",
                target="selected",
                actual=0,
                prediction=0.1,
            )
            for m in [1, 2, 3]
        ]
        + [
            dict(
                player_id="b",
                country="India",
                cutoff_date="2022-01-01",
                target="selected",
                actual=1,
                prediction=0.1,
            )
        ]
    )
    score = metrics(frame)
    assert score["brier"] == pytest.approx((3 * 0.01 + 0.81) / 4)
    assert score["equal_player_brier"] == pytest.approx((0.01 + 0.81) / 2)
    assert score["unique_entrants"] == 1


def test_arbitrary_date_forecast_obeys_fit_policy_coverage_and_horizon(tmp_path):
    import json

    import joblib

    from national_selection.models import forecast

    rows = []
    for date in ["2015-01-01", "2016-01-01", "2016-06-01"]:
        for n in range(4):
            rows.append(
                dict(
                    player_id=str(n),
                    player_name=str(n),
                    country="India",
                    cutoff_date=date,
                    calendar_month=int(date[5:7]),
                    horizon_months=12,
                    label_end=(
                        pd.Timestamp(date)
                        + pd.DateOffset(months=12)
                        - pd.Timedelta(days=1)
                    )
                    .date()
                    .isoformat(),
                    selected=int(n == 0 or date == "2016-06-01"),
                    n_matches=int(n == 0 or date == "2016-06-01"),
                    **dict.fromkeys(FEATURES, n + 1),
                )
            )
    panel = pd.DataFrame(rows)
    snapshot = panel.iloc[[0]].copy()
    snapshot["cutoff_date"], snapshot["calendar_month"] = "2017-06-01", 6
    snapshot["label_end"] = "2018-05-31"
    (tmp_path / "selection.json").write_text(
        json.dumps(
            dict(
                classification_model_selected_on_validation_log_loss="base_rate",
                horizon_months=12,
                training_cadence="monthly",
                policy_available_from="2017-01-01",
                observed_through="2017-05-31",
            )
        )
    )
    result = forecast(panel, snapshot, tmp_path)
    assert result.fit_date.tolist() == ["2017-01-01"]
    assert result.base_rate.tolist() == [0.25]
    artifact = joblib.load(tmp_path / "models/forecast_logistic.joblib")
    assert (
        artifact["model"].predict_proba(snapshot[MODEL_INPUTS])[:, 1].tolist()
        == result.logistic.tolist()
    )
    stored = pd.read_csv(tmp_path / "forecast.csv")
    assert stored.logistic.tolist() == pytest.approx(result.logistic.tolist())
    with pytest.raises(ValueError, match="Training panel horizon"):
        forecast(panel.assign(horizon_months=24), snapshot, tmp_path)
    with pytest.raises(ValueError, match="unavailable"):
        forecast(panel, snapshot.assign(cutoff_date="2016-12-01"), tmp_path)
    with pytest.raises(ValueError, match="input coverage"):
        forecast(panel, snapshot.assign(cutoff_date="2017-06-02"), tmp_path)


def test_long_horizon_validation_must_mature_before_policy_selection(
    tmp_path, monkeypatch
):
    import national_selection.models as modeling

    families = models()
    monkeypatch.setattr(
        modeling,
        "models",
        lambda: {n: families[n] for n in ["base_rate", "zero_count"]},
    )
    rows = []
    for date in pd.date_range("2010-01-01", "2022-12-01", freq="MS"):
        for n in range(4):
            rows.append(
                dict(
                    player_id=str(n),
                    player_name=str(n),
                    country="India",
                    cutoff_date=date.date().isoformat(),
                    calendar_month=date.month,
                    horizon_months=36,
                    event_date=None,
                    label_end=(date + pd.DateOffset(months=36) - pd.Timedelta(days=1))
                    .date()
                    .isoformat(),
                    selected=n % 2,
                    n_matches=n % 2,
                    missing_affiliation_matches=0,
                    **dict.fromkeys(FEATURES, n + 1),
                )
            )
    evaluate(pd.DataFrame(rows), tmp_path, observed_through="2025-12-31")
    predictions = pd.read_csv(tmp_path / "predictions.csv")
    validation = predictions[predictions.phase == "validation"]
    assert validation.label_end.max() == "2021-12-31"
    assert validation[
        validation.cutoff_date.str.startswith("2019")
    ].cutoff_date.unique().tolist() == ["2019-01-01"]
    assert predictions.loc[
        predictions.phase == "test", "fit_date"
    ].unique().tolist() == ["2022-01-01"]


@pytest.mark.parametrize("horizon", [0, -1, True, 1.5])
def test_invalid_horizon_and_stale_forecasts_are_rejected(horizon):
    with pytest.raises(ValueError, match="positive integer"):
        build_panel(*inputs(), cutoffs=["2016-01-01"], horizon_months=horizon)
    with pytest.raises(ValueError, match="input coverage"):
        build_panel(
            *inputs(),
            cutoffs=["2016-01-02"],
            observed_through="2015-12-31",
            labeled=False,
        )
