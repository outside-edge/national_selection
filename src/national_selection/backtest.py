"""Compare horizons and prediction cadences on explicitly matched observations."""

import json
from pathlib import Path

import pandas as pd

from national_selection.models import metrics, score_groups


def selected_name(folder):
    return json.loads((folder / "selection.json").read_text())[
        "classification_model_selected_on_validation_log_loss"
    ]


def january_comparison(monthly, annual):
    monthly = monthly[
        (monthly.phase == "test") & monthly.cutoff_date.str.endswith("-01-01")
    ]
    annual = annual[annual.phase == "test"]
    rows = []
    for model, block in monthly.groupby("model"):
        other = annual[annual.model == model]
        keys = ["player_id", "cutoff_date"]
        matched = block.merge(
            other,
            on=keys,
            how="outer",
            suffixes=("_m", "_a"),
            indicator=True,
            validate="one_to_one",
        )
        if (
            not matched._merge.eq("both").all()
            or not matched.actual_m.eq(matched.actual_a).all()
        ):
            raise ValueError(
                "January comparison requires identical candidate rows and outcomes"
            )
        for cadence, frame in [("monthly", block), ("annual", other)]:
            rows.append(
                dict(
                    model=model,
                    cadence=cadence,
                    target=frame.target.iloc[0],
                    **metrics(frame),
                )
            )
    return pd.DataFrame(rows)


def summarize_runs(destination, horizons):
    destination = Path(destination)
    summary, january, selected_predictions = [], [], []
    monthly_predictions = {
        h: pd.read_csv(
            destination / f"monthly_{h}m/predictions.csv", dtype={"player_id": str}
        )
        for h in horizons
    }
    common_dates = set.intersection(
        *(
            set(p.loc[p.phase == "test", "cutoff_date"])
            for p in monthly_predictions.values()
        )
    )
    if not common_dates:
        raise ValueError("No shared test dates across horizons")
    common_start, common_end = min(common_dates), max(common_dates)
    for horizon in horizons:
        folder = destination / f"monthly_{horizon}m"
        selected = selected_name(folder)
        month = monthly_predictions[horizon]
        common = score_groups(
            month[(month.phase == "test") & month.cutoff_date.isin(common_dates)],
            ["phase", "model", "target"],
        )
        common.to_csv(folder / "metrics_common_test.csv", index=False)
        for name in dict.fromkeys([selected, "base_rate", "context_only"]):
            row = (
                common[(common.model == name) & (common.target == "selected")]
                .iloc[0]
                .to_dict()
            )
            summary.append(
                dict(horizon_months=horizon, selected_classifier=selected, **row)
            )
        annual_folder = destination / f"annual_{horizon}m"
        annual = pd.read_csv(
            annual_folder / "predictions.csv", dtype={"player_id": str}
        )
        score_groups(
            annual[(annual.phase == "test") & annual.cutoff_date.isin(common_dates)],
            ["phase", "model", "target"],
        ).to_csv(annual_folder / "metrics_common_test.csv", index=False)
        comparison = january_comparison(month, annual)
        comparison["horizon_months"] = horizon
        comparison["chosen_by_own_validation"] = [
            name == (selected if cadence == "monthly" else selected_name(annual_folder))
            for name, cadence in zip(comparison.model, comparison.cadence, strict=True)
        ]
        january.append(comparison)
        pred = month[(month.phase == "test") & (month.model == selected)]
        selected_predictions.append(
            pred[["player_id", "cutoff_date", "prediction"]].rename(
                columns={"prediction": f"p_{horizon}m"}
            )
        )
    scores = pd.DataFrame(summary)
    scores.to_csv(destination / "horizon_comparison.csv", index=False)
    pd.concat(january, ignore_index=True).to_csv(
        destination / "january_comparison.csv", index=False
    )
    consistency = selected_predictions[0]
    for frame in selected_predictions[1:]:
        consistency = consistency.merge(
            frame, on=["player_id", "cutoff_date"], validate="one_to_one"
        )
    consistency["nonmonotone"] = False
    for shorter, longer in zip(
        sorted(horizons)[:-1], sorted(horizons)[1:], strict=True
    ):
        consistency["nonmonotone"] |= (
            consistency[f"p_{shorter}m"] > consistency[f"p_{longer}m"] + 1e-12
        )
    consistency.to_csv(destination / "horizon_consistency.csv", index=False)
    primary = 12 if 12 in horizons else horizons[0]
    lines = [
        "# Monthly international-entry backtests",
        "",
        "Predictions update monthly; model parameters refit each January "
        "using fully matured training labels. "
        f"Primary horizon: {primary} months. Evaluated horizons: "
        f"{', '.join(map(str, horizons))} months. "
        "Model choice uses mature 2017–2019 validation outcomes.",
        "",
        "## Same-date comparison across horizons",
        "",
        f"All rows below use shared forecast dates from {common_start} "
        f"through {common_end}. "
        "Each horizon has a different outcome frequency: compare "
        "improvement over its own baseline, not raw scores between "
        "horizons.",
        "",
        "| Horizon | Chosen model | Log loss | Base-rate log loss | "
        "Improvement | Brier | Average precision | Players | Unique "
        "entrants |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for horizon in horizons:
        block = scores[scores.horizon_months == horizon]
        chosen = block[block.model == block.selected_classifier].iloc[0]
        base = block[block.model == "base_rate"].iloc[0]
        lines.append(
            f"| {horizon} months | {chosen.model} | {chosen.log_loss:.3f} | "
            f"{base.log_loss:.3f} | "
            f"{1 - chosen.log_loss / base.log_loss:.1%} | "
            f"{chosen.brier:.3f} | {chosen.average_precision:.3f} | "
            f"{int(chosen.players)} | {int(chosen.unique_entrants)} |"
        )
    lines += [
        "",
        "Positive improvement means lower log loss. These are descriptive "
        "differences; repeated players and overlapping windows are not "
        "independent observations.",
        "",
    ]
    primary = 12 if 12 in horizons else horizons[0]
    primary_folder = destination / f"monthly_{primary}m"
    primary_name = selected_name(primary_folder)
    primary_metrics = pd.read_csv(primary_folder / "metrics.csv")
    row = primary_metrics[
        (primary_metrics.phase == "test") & (primary_metrics.model == primary_name)
    ].iloc[0]
    lines += [
        f"## All {primary}-month classifiers",
        "",
        "Every family was specified before the monthly backtest. The "
        "lowest test loss does not override validation model selection.",
        "",
        "| Model | Validation log loss | Test log loss | Test Brier | Test "
        "average precision | Test ROC AUC | Test top-10 precision |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in primary_metrics[
        (primary_metrics.phase == "test") & (primary_metrics.target == "selected")
    ].itertuples():
        validation = primary_metrics[
            (primary_metrics.phase == "validation") & (primary_metrics.model == r.model)
        ].iloc[0]
        lines.append(
            f"| {r.model} | {validation.log_loss:.3f} | {r.log_loss:.3f} | "
            f"{r.brier:.3f} | {r.average_precision:.3f} | {r.roc_auc:.3f} | "
            f"{r.precision_at_10:.1%} |"
        )
    lines += [""]
    lines += [
        f"## Full {primary}-month test",
        "",
        f"The chosen {primary_name} model has log loss {row.log_loss:.3f}, "
        f"Brier {row.brier:.3f}, average precision "
        f"{row.average_precision:.3f}, ROC AUC {row.roc_auc:.3f}, and "
        f"top-10 precision {row.precision_at_10:.1%}.",
        f"Mean predicted probability: {row.predicted_mean:.1%}; observed "
        f"entry frequency: {row.observed_mean:.1%}. Sample: {int(row.n)} "
        f"snapshots, {int(row.players)} distinct players, "
        f"{int(row.unique_entrants)} distinct observed entrants.",
        "",
        "Top-ten rankings use country/month pools. Calibration bins, all "
        "model families, count forecasts, annual breakdowns, country "
        "breakdowns and equal-player metrics are in each run folder.",
        "",
        "## January-only benchmark",
        "",
        "Both procedures below are evaluated on the same January "
        "candidate/date rows. Each chooses its model using its own "
        "validation cadence. The CSV also compares every identical model "
        "family.",
        "",
        "| Training snapshots | Chosen model | January test log loss | "
        "Brier | Average precision |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    comparison = pd.concat(january, ignore_index=True)
    for r in comparison[
        (comparison.horizon_months == primary) & comparison.chosen_by_own_validation
    ].itertuples():
        lines.append(
            f"| {r.cadence} | {r.model} | {r.log_loss:.3f} | {r.brier:.3f} "
            f"| {r.average_precision:.3f} |"
        )
    lines += [
        "",
        "This compares forecasting procedures, not a causal effect of more "
        "observations. Fixed regularization also behaves differently as "
        "training rows increase.",
        "",
        "## Horizon consistency and limitations",
        "",
        f"Independent horizon models violate increasing probability with "
        f"longer horizons in "
        f"{int(consistency.nonmonotone.sum())}/{len(consistency)} shared "
        f"forecasts. Raw probabilities are retained; they are not a "
        f"coherent survival curve.",
        "",
        "The sample still covers IPL pathways. Country affiliation is "
        "conservatively dated, international history is incomplete, and "
        "overseas cohorts are small. Outcomes describe recorded entry; "
        "this does not establish comprehensive cross-country accuracy or "
        "discrimination.",
        "",
        "For definitions, censoring, leakage safeguards and design choices "
        "see [monthly design](../docs/monthly_design.md).",
        "",
    ]
    (destination / "report.md").write_text("\n".join(lines))
    return scores
