"""Evaluate frozen model families with matured labels and chronological splits."""

import json
import platform
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, PoissonRegressor
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    mean_absolute_error,
    mean_poisson_deviance,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from national_selection.features import FEATURES

MODEL_INPUTS = FEATURES + ["country", "calendar_month"]


def models():
    def pipeline(model, performance=True, context=False):
        transformers = []
        if performance:
            transformers.append(
                (
                    "performance",
                    make_pipeline(
                        SimpleImputer(
                            strategy="median",
                            add_indicator=True,
                            keep_empty_features=True,
                        ),
                        StandardScaler(),
                    ),
                    FEATURES,
                )
            )
        if context:
            transformers.append(
                (
                    "context",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                    ["country", "calendar_month"],
                )
            )
        return make_pipeline(ColumnTransformer(transformers), model)

    def boosting():
        return HistGradientBoostingClassifier(
            max_iter=100,
            max_leaf_nodes=7,
            min_samples_leaf=20,
            l2_regularization=10,
            early_stopping=False,
            random_state=2026,
        )

    result = {
        "base_rate": (pipeline(DummyClassifier(strategy="prior")), "selected"),
        "context_only": (
            pipeline(
                LogisticRegression(C=0.1, max_iter=5000),
                performance=False,
                context=True,
            ),
            "selected",
        ),
        "logistic": (pipeline(LogisticRegression(C=0.1, max_iter=5000)), "selected"),
        "boosting": (pipeline(boosting()), "selected"),
        "zero_count": (
            pipeline(DummyRegressor(strategy="constant", constant=0)),
            "n_matches",
        ),
        "mean_count": (pipeline(DummyRegressor(strategy="mean")), "n_matches"),
        "poisson": (pipeline(PoissonRegressor(alpha=10, max_iter=5000)), "n_matches"),
    }
    result.update(
        {
            "logistic_context": (
                pipeline(LogisticRegression(C=0.1, max_iter=5000), context=True),
                "selected",
            ),
            "boosting_context": (pipeline(boosting(), context=True), "selected"),
            "poisson_context": (
                pipeline(PoissonRegressor(alpha=10, max_iter=5000), context=True),
                "n_matches",
            ),
        }
    )
    return result


def metrics(frame):
    y, p = frame.actual.to_numpy(), frame.prediction.to_numpy()
    result = {
        "n": len(frame),
        "players": frame.player_id.nunique(),
        "positive_rows": int((y > 0).sum()),
        "unique_entrants": frame.loc[frame.actual > 0, "player_id"].nunique(),
        "observed_mean": float(y.mean()),
        "predicted_mean": float(p.mean()),
    }
    weights = 1 / frame.groupby("player_id").player_id.transform("size")
    if frame.target.iloc[0] == "selected":
        result.update(
            log_loss=log_loss(y, p, labels=[0, 1]),
            equal_player_log_loss=log_loss(y, p, labels=[0, 1], sample_weight=weights),
            equal_player_brier=brier_score_loss(y, p, sample_weight=weights),
            brier=brier_score_loss(y, p),
            average_precision=average_precision_score(y, p) if y.sum() else None,
            roc_auc=roc_auc_score(y, p) if len(np.unique(y)) == 2 else None,
        )
        hits, slots, positives = 0, 0, 0
        for _, block in frame.groupby(["cutoff_date", "country"]):
            top = block.sort_values(
                ["prediction", "player_id"], ascending=[False, True]
            ).head(10)
            hits += top.actual.sum()
            slots += len(top)
            positives += block.actual.sum()
        result.update(
            precision_at_10=hits / slots,
            recall_at_10=hits / positives if positives else None,
        )
    else:
        result.update(
            mae=mean_absolute_error(y, p),
            poisson_deviance=(
                float("inf")
                if ((p == 0) & (y > 0)).any()
                else mean_poisson_deviance(y, np.maximum(p, 1e-9))
            ),
        )
    return result


def predict(model, target, frame):
    if target == "selected":
        return model.predict_proba(frame[MODEL_INPUTS])[:, 1]
    return model.predict(frame[MODEL_INPUTS])


def score_groups(predictions, keys):
    rows = []
    for values, block in predictions.groupby(keys):
        if not isinstance(values, tuple):
            values = (values,)
        rows.append(dict(zip(keys, values, strict=True)) | metrics(block))
    return pd.DataFrame(rows)


def evaluate(panel, destination, cadence="monthly", observed_through=None):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    observed_through = observed_through or panel.label_end.max()
    if panel.label_end.max() > observed_through:
        raise ValueError("Evaluation contains immature outcome windows")
    horizons = panel.horizon_months.unique()
    if len(horizons) != 1:
        raise ValueError("Evaluate one horizon at a time")
    if cadence not in {"monthly", "annual"}:
        raise ValueError("Unknown cadence")
    if cadence == "annual":
        panel = panel[panel.cutoff_date.str.endswith("-01-01")].copy()
    if panel[["selected", "n_matches"]].isna().any().any():
        raise ValueError("Cannot evaluate unlabeled rows")
    environment = {
        "python": platform.python_version(),
        "packages": {
            name: version(name)
            for name in ["numpy", "pandas", "scikit-learn", "scipy", "joblib"]
        },
    }
    (destination / "environment.json").write_text(
        json.dumps(environment, indent=2) + "\n"
    )
    predictions, folds = [], []
    for year in [2017, 2018, 2019, 2022, 2023, 2024]:
        fit_date = f"{year}-01-01"
        train = panel[panel.label_end < fit_date]
        test = panel[panel.cutoff_date.str.startswith(str(year))]
        phase = "validation" if year < 2020 else "test"
        if phase == "validation":
            test = test[test.label_end < "2022-01-01"]
        if test.empty:
            continue
        if train.selected.nunique() != 2:
            raise ValueError(f"Insufficient training classes for fold {year}")
        folds.append(
            dict(
                year=year,
                phase=phase,
                fit_date=fit_date,
                train_rows=len(train),
                train_last_label=train.label_end.max(),
                test_rows=len(test),
                test_positive=int(test.selected.sum()),
                test_cutoffs=test.cutoff_date.nunique(),
            )
        )
        print(
            f"{cadence} {horizons[0]}m: fit {year}, {len(train)} training "
            f"rows, {len(test)} forecasts",
            flush=True,
        )
        for name, (model, target) in models().items():
            model.fit(train[MODEL_INPUTS], train[target])
            output = test[
                [
                    "player_id",
                    "player_name",
                    "country",
                    "cutoff_date",
                    "label_end",
                    "event_date",
                    "horizon_months",
                    "missing_affiliation_matches",
                ]
            ].copy()
            output["fit_date"] = fit_date
            output["model"], output["target"], output["phase"] = name, target, phase
            output["actual"] = test[target].to_numpy()
            output["prediction"] = predict(model, target, test)
            predictions.append(output)
    if not predictions:
        raise ValueError("No mature validation or test forecasts")
    predictions = pd.concat(predictions, ignore_index=True)
    if set(predictions.phase) != {"validation", "test"}:
        raise ValueError("Need mature validation and test periods")
    if (
        predictions.loc[predictions.phase == "validation", "label_end"].max()
        >= predictions.loc[predictions.phase == "test", "fit_date"].min()
    ):
        raise ValueError(
            "Validation labels were not available before test policy selection"
        )
    predictions.to_csv(destination / "predictions.csv", index=False)
    pd.DataFrame(folds).to_csv(destination / "folds.csv", index=False)
    keys = ["phase", "model", "target"]
    scores = score_groups(predictions, keys)
    scores.to_csv(destination / "metrics.csv", index=False)
    predictions["year"] = predictions.cutoff_date.str[:4]
    for dimension in ["year", "cutoff_date", "country"]:
        score_groups(predictions, keys + [dimension]).to_csv(
            destination / f"metrics_by_{dimension}.csv", index=False
        )
    country_scores = score_groups(predictions, keys + ["country"])
    country_scores.groupby(keys)[
        ["log_loss", "brier", "mae"]
    ].mean().reset_index().to_csv(
        destination / "metrics_country_macro.csv", index=False
    )
    choices = scores[(scores.phase == "validation") & (scores.target == "selected")]
    selected = choices.sort_values(["log_loss", "model"]).iloc[0].model
    (destination / "selection.json").write_text(
        json.dumps(
            {
                "classification_model_selected_on_validation_log_loss": selected,
                "horizon_months": int(horizons[0]),
                "training_cadence": cadence,
                "observed_through": observed_through,
                "policy_available_from": (
                    pd.Timestamp(
                        predictions.loc[
                            predictions.phase == "validation", "label_end"
                        ].max()
                    )
                    + pd.Timedelta(days=1)
                )
                .date()
                .isoformat(),
                "refit_cadence": "annual",
                "input_columns": MODEL_INPUTS,
                "validation_years": [2017, 2018, 2019],
                "test_years": [2022, 2023, 2024],
                "caveat": (
                    "Exploratory backtest; repeated players and overlapping "
                    "windows are dependent."
                ),
            },
            indent=2,
        )
        + "\n"
    )
    calibration = predictions[predictions.target == "selected"].copy()
    calibration["bin"] = pd.cut(
        calibration.prediction,
        bins=[0, 0.05, 0.1, 0.2, 0.4, 0.6, 0.8, 1],
        include_lowest=True,
    )
    calibration.groupby(["phase", "model", "bin"], observed=True).agg(
        n=("actual", "size"),
        observed=("actual", "mean"),
        predicted=("prediction", "mean"),
    ).reset_index().to_csv(destination / "calibration.csv", index=False)
    write_report(predictions, scores, selected, destination, cadence, int(horizons[0]))
    return scores.to_dict("records")


def forecast(panel, snapshot, destination, observed_through=None):
    """Forecast with parameters fitted at the most recent January cutoff."""
    destination = Path(destination)
    cutoffs = snapshot.cutoff_date.unique()
    if len(cutoffs) != 1 or snapshot.horizon_months.nunique() != 1:
        raise ValueError("Forecast requires one cutoff and one horizon")
    metadata = json.loads((destination / "selection.json").read_text())
    if snapshot.horizon_months.iloc[0] != metadata["horizon_months"]:
        raise ValueError("Forecast horizon differs from fitted policy")
    if set(panel.horizon_months) != {metadata["horizon_months"]}:
        raise ValueError("Training panel horizon differs from fitted policy")
    coverage = min(
        observed_through or metadata["observed_through"], metadata["observed_through"]
    )
    if pd.Timestamp(cutoffs[0]) > pd.Timestamp(coverage) + pd.Timedelta(days=1):
        raise ValueError("Forecast cutoff exceeds documented input coverage")
    if metadata["training_cadence"] == "annual":
        panel = panel[panel.cutoff_date.str.endswith("-01-01")]
    fit_date = f"{cutoffs[0][:4]}-01-01"
    if fit_date < metadata["policy_available_from"]:
        raise ValueError(
            "Model-selection policy was unavailable at the annual fit date"
        )
    train = panel[panel.label_end < fit_date]
    if train.selected.nunique() != 2:
        raise ValueError("Forecast needs both training classes")
    selected = metadata["classification_model_selected_on_validation_log_loss"]
    output = snapshot[
        [
            "player_id",
            "player_name",
            "country",
            "cutoff_date",
            "label_end",
            "horizon_months",
        ]
    ].copy()
    output["fit_date"] = fit_date
    folder = destination / "models"
    folder.mkdir(exist_ok=True)
    for name in dict.fromkeys(
        [
            selected,
            "context_only",
            "logistic",
            "logistic_context",
            "poisson",
            "poisson_context",
            "mean_count",
        ]
    ):
        model, target = models()[name]
        model.fit(train[MODEL_INPUTS], train[target])
        output[name] = predict(model, target, snapshot)
        joblib.dump(
            {
                "model": model,
                "input_columns": MODEL_INPUTS,
                "target": target,
                "fit_date": fit_date,
                "horizon_months": metadata["horizon_months"],
            },
            folder / f"forecast_{name}.joblib",
        )
    output["selected_classifier"] = selected
    output.sort_values(selected, ascending=False).to_csv(
        destination / "forecast.csv", index=False
    )
    return output


def write_report(predictions, scores, selected, destination, cadence, horizon):
    test = predictions[(predictions.phase == "test") & (predictions.model == selected)]
    lines = [
        f"# {horizon}-month international-entry backtest ({cadence})",
        "",
        f"Validation selected **{selected}** by log loss. Parameters refit "
        f"each January; inputs update at each forecast cutoff.",
        "",
        f"Test cutoffs: {test.cutoff_date.min()} through "
        f"{test.cutoff_date.max()}; {test.cutoff_date.nunique()} forecast "
        f"dates.",
        f"{len(test)} player snapshots; {test.player_id.nunique()} players; "
        f"{int(test.actual.sum())} positive snapshots; "
        f"{test.loc[test.actual > 0, 'player_id'].nunique()} distinct "
        f"observed entrants.",
        "",
        "Labels are recorded entry and appearances. Neither a mature "
        "horizon nor more snapshots repairs archive gaps.",
        "",
        "| Model | Log loss | Brier | Average precision | ROC AUC | Top-10 "
        "precision | Mean probability |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in scores[
        (scores.phase == "test") & (scores.target == "selected")
    ].itertuples():
        lines.append(
            f"| {row.model} | {row.log_loss:.3f} | {row.brier:.3f} | "
            f"{row.average_precision:.3f} | {row.roc_auc:.3f} | "
            f"{row.precision_at_10:.1%} | {row.predicted_mean:.1%} |"
        )
    lines += [
        "",
        f"Observed entry frequency: {test.actual.mean():.1%}. Lower log "
        f"loss/Brier are better; higher ranking measures are better. Top "
        f"ten are selected separately within each country/date; small pools "
        f"can make recall mechanically perfect. Baseline ties use arbitrary "
        f"UUID order.",
        "",
        "| Count model | MAE | Poisson deviance |",
        "| --- | ---: | ---: |",
    ]
    for row in scores[
        (scores.phase == "test") & (scores.target == "n_matches")
    ].itertuples():
        lines.append(f"| {row.model} | {row.mae:.3f} | {row.poisson_deviance:.3f} |")
    lines += [
        "",
        "Counts measure opportunity and persistence. A zero forecast can "
        "win MAE but has infinite deviance on positive outcomes.",
        "",
        "| Country | Snapshots | Players | Positive snapshots | Unique "
        "entrants | Max missing affiliation fixtures |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for country, block in test.groupby("country"):
        lines.append(
            f"| {country} | {len(block)} | {block.player_id.nunique()} | "
            f"{int(block.actual.sum())} | "
            f"{block.loc[block.actual > 0, 'player_id'].nunique()} | "
            f"{int(block.missing_affiliation_matches.max())} |"
        )
    lines += [
        "",
        "Country is dated auction nationality, a proxy for affiliation. "
        "Outcomes and prior-cap exclusions span all national teams. The "
        "missing-fixture flag covers only the cutoff affiliation. "
        "Zero-coverage countries are excluded; partial coverage still "
        "limits labels.",
        "",
        "Overlapping horizons, repeated players and country/calendar "
        "shocks make rows dependent. Improvements are descriptive backtest "
        "differences, not precise independent-row estimates. See "
        "equal-player metrics, year/country metrics, common-period scores "
        "and calibration CSVs. Overseas samples remain too small for broad "
        "validation.",
        "",
    ]
    (destination / "report.md").write_text("\n".join(lines))
