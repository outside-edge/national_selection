"""Evaluate frozen model families with matured labels and chronological splits."""

import json
import platform
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
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
from sklearn.preprocessing import StandardScaler

from national_selection.features import FEATURES


def models():
    def pipeline(model):
        return make_pipeline(
            SimpleImputer(
                strategy="median", add_indicator=True, keep_empty_features=True
            ),
            StandardScaler(),
            model,
        )

    return {
        "base_rate": (pipeline(DummyClassifier(strategy="prior")), "selected"),
        "logistic": (pipeline(LogisticRegression(C=0.1, max_iter=5000)), "selected"),
        "boosting": (
            pipeline(
                HistGradientBoostingClassifier(
                    max_iter=100,
                    max_leaf_nodes=7,
                    min_samples_leaf=20,
                    l2_regularization=10,
                    early_stopping=False,
                    random_state=2026,
                )
            ),
            "selected",
        ),
        "zero_count": (
            pipeline(DummyRegressor(strategy="constant", constant=0)),
            "n_matches",
        ),
        "mean_count": (pipeline(DummyRegressor(strategy="mean")), "n_matches"),
        "poisson": (pipeline(PoissonRegressor(alpha=10, max_iter=5000)), "n_matches"),
    }


def metrics(frame):
    y, p = frame.actual.to_numpy(), frame.prediction.to_numpy()
    result = {
        "n": len(frame),
        "players": frame.player_id.nunique(),
        "observed_mean": float(y.mean()),
        "predicted_mean": float(p.mean()),
    }
    if frame.target.iloc[0] == "selected":
        result.update(
            log_loss=log_loss(y, p, labels=[0, 1]),
            brier=brier_score_loss(y, p),
            average_precision=average_precision_score(y, p) if y.sum() else None,
            roc_auc=roc_auc_score(y, p) if len(np.unique(y)) == 2 else None,
        )
        hits, slots, positives = 0, 0, 0
        for _, block in frame.groupby("cutoff_date"):
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


def evaluate(panel, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
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
    # Validate on 2017–2019, then test the frozen families on 2022–2024.
    for year in [2017, 2018, 2019, 2022, 2023, 2024]:
        cutoff = f"{year}-01-01"
        train = panel[panel.label_end < cutoff]
        test = panel[panel.cutoff_date == cutoff]
        if train.selected.nunique() != 2 or test.empty:
            raise ValueError(f"Insufficient data for chronological fold {year}")
        phase = "validation" if year < 2020 else "test"
        folds.append(
            dict(
                year=year,
                phase=phase,
                train_rows=len(train),
                train_last_label=train.label_end.max(),
                test_rows=len(test),
                test_positive=int(test.selected.sum()),
            )
        )
        for name, (model, target) in models().items():
            model.fit(train[FEATURES], train[target])
            pred = (
                model.predict_proba(test[FEATURES])[:, 1]
                if target == "selected"
                else model.predict(test[FEATURES])
            )
            output = test[
                [
                    "player_id",
                    "player_name",
                    "cutoff_date",
                    "label_end",
                    "missing_outcome_matches",
                ]
            ].copy()
            output["model"], output["target"], output["phase"] = name, target, phase
            output["actual"], output["prediction"] = test[target].to_numpy(), pred
            predictions.append(output)
            if year == 2024:
                folder = destination / "models"
                folder.mkdir(exist_ok=True)
                joblib.dump(
                    {
                        "model": model,
                        "features": FEATURES,
                        "trained_before": cutoff,
                        "target": target,
                    },
                    folder / f"{name}.joblib",
                )
    predictions = pd.concat(predictions, ignore_index=True)
    predictions.to_csv(destination / "predictions.csv", index=False)
    pd.DataFrame(folds).to_csv(destination / "folds.csv", index=False)
    scores = []
    for (phase, name, target), block in predictions.groupby(
        ["phase", "model", "target"]
    ):
        scores.append(dict(phase=phase, model=name, target=target, **metrics(block)))
    pd.DataFrame(scores).to_csv(destination / "metrics.csv", index=False)
    annual = []
    for (date, name, target), block in predictions.groupby(
        ["cutoff_date", "model", "target"]
    ):
        annual.append(
            dict(cutoff_date=date, model=name, target=target, **metrics(block))
        )
    pd.DataFrame(annual).to_csv(destination / "metrics_by_year.csv", index=False)
    selected = min(
        (s for s in scores if s["phase"] == "validation" and s["target"] == "selected"),
        key=lambda s: s["log_loss"],
    )["model"]
    (destination / "selection.json").write_text(
        json.dumps(
            {
                "classification_model_selected_on_validation_log_loss": selected,
                "features": FEATURES,
                "test_years": [2022, 2023, 2024],
                "caveat": (
                    "Overlapping outcomes and repeated players; "
                    "rows are not independent."
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
    write_report(predictions, scores, selected, destination)
    return scores


def forecast(panel, snapshot, destination):
    """Refit on matured labels and score an unlabeled candidate snapshot."""
    destination = Path(destination)
    cutoff = snapshot.cutoff_date.unique()
    if len(cutoff) != 1:
        raise ValueError("Forecast requires one cutoff")
    train = panel[panel.label_end < cutoff[0]]
    if train.selected.nunique() != 2:
        raise ValueError("Forecast needs both training classes")
    selected = json.loads((destination / "selection.json").read_text())[
        "classification_model_selected_on_validation_log_loss"
    ]
    output = snapshot[["player_id", "player_name", "cutoff_date", "label_end"]].copy()
    folder = destination / "models"
    folder.mkdir(exist_ok=True)
    for name in [selected, "logistic", "poisson", "mean_count"]:
        model, target = models()[name]
        model.fit(train[FEATURES], train[target])
        output[name] = (
            model.predict_proba(snapshot[FEATURES])[:, 1]
            if target == "selected"
            else model.predict(snapshot[FEATURES])
        )
        joblib.dump(
            {
                "model": model,
                "features": FEATURES,
                "target": target,
                "trained_before": cutoff[0],
            },
            folder / f"forecast_{name}.joblib",
        )
    output["selected_classifier"] = selected
    output.sort_values(selected, ascending=False).to_csv(
        destination / "forecast.csv", index=False
    )
    return output


def write_report(predictions, scores, selected, destination):
    test = predictions[(predictions.phase == "test") & (predictions.model == selected)]
    lines = [
        "# Two-year international-entry pilot",
        "",
        f"Validation selected **{selected}** by log loss.",
        "",
        f"Later evaluation: {len(test)} player snapshots, "
        f"{test.player_id.nunique()} distinct players, "
        f"{int(test.actual.sum())} positive snapshots across 2022–2024 cutoffs.",
        "",
        "Labels are recorded international entry and recorded appearances. "
        "Missing archive matches and unresolved identities limit interpretation.",
        "",
        "## Classification",
        "",
        "| Model | Test log loss | Brier | Average precision | Top-10 precision |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in scores:
        if row["phase"] == "test" and row["target"] == "selected":
            lines.append(
                f"| {row['model']} | {row['log_loss']:.3f} | "
                f"{row['brier']:.3f} | {row['average_precision']:.3f} | "
                f"{row['precision_at_10']:.1%} |"
            )
    lines.extend(
        [
            "",
            "Lower log loss and Brier are better. Higher average precision "
            "and top-10 precision are better. Each year's top ten form the ranking "
            "comparison; tied base-rate ranks use arbitrary stable ID order.",
            "",
            "## Match counts",
            "",
            "| Model | Test MAE | Poisson deviance |",
            "| --- | ---: | ---: |",
        ]
    )
    for row in scores:
        if row["phase"] == "test" and row["target"] == "n_matches":
            lines.append(
                f"| {row['model']} | {row['mae']:.3f} | {row['poisson_deviance']:.3f} |"
            )
    lines.extend(
        [
            "",
            "Counts measure opportunity, not performance quality. "
            "Always-zero predictions can minimize absolute error for sparse "
            "outcomes but have infinite Poisson deviance on positive outcomes.",
            "",
            "These are rolling chronological fits with fully matured labels. "
            "Overlapping windows and repeated players are dependent. Identity "
            "corrections were made during development; this is an exploratory "
            "backtest rather than an untouched confirmation sample.",
            "",
        ]
    )
    (destination / "report.md").write_text("\n".join(lines))
