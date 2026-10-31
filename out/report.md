# Monthly international-entry backtests

Predictions update monthly; model parameters refit each January using fully matured training labels. Primary horizon: 12 months. Evaluated horizons: 6, 12, 24 months. Model choice uses mature 2017–2019 validation outcomes.

## Same-date comparison across horizons

All rows below use shared forecast dates from 2022-01-01 through 2024-01-01. Each horizon has a different outcome frequency: compare improvement over its own baseline, not raw scores between horizons.

| Horizon | Chosen model | Log loss | Base-rate log loss | Improvement | Brier | Average precision | Players | Unique entrants |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 months | context_only | 0.270 | 0.270 | -0.1% | 0.069 | 0.112 | 90 | 20 |
| 12 months | base_rate | 0.437 | 0.437 | 0.0% | 0.128 | 0.147 | 90 | 25 |
| 24 months | base_rate | 0.556 | 0.556 | 0.0% | 0.179 | 0.206 | 90 | 25 |

Positive improvement means lower log loss. These are descriptive differences; repeated players and overlapping windows are not independent observations.

## All 12-month classifiers

Every family was specified before the monthly backtest. The lowest test loss does not override validation model selection.

| Model | Validation log loss | Test log loss | Test Brier | Test average precision | Test ROC AUC | Test top-10 precision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| base_rate | 0.287 | 0.384 | 0.110 | 0.111 | 0.437 | 18.4% |
| boosting | 0.360 | 0.339 | 0.097 | 0.366 | 0.756 | 33.1% |
| boosting_context | 0.369 | 0.334 | 0.096 | 0.386 | 0.771 | 32.2% |
| context_only | 0.287 | 0.384 | 0.110 | 0.121 | 0.472 | 18.4% |
| logistic | 0.348 | 0.345 | 0.093 | 0.417 | 0.735 | 34.4% |
| logistic_context | 0.345 | 0.342 | 0.093 | 0.415 | 0.743 | 32.8% |

## Full 12-month test

The chosen base_rate model has log loss 0.384, Brier 0.110, average precision 0.111, ROC AUC 0.437, and top-10 precision 18.4%.
Mean predicted probability: 8.3%; observed entry frequency: 12.3%. Sample: 1987 snapshots, 93 distinct players, 26 distinct observed entrants.

Top-ten rankings use country/month pools. Calibration bins, all model families, count forecasts, annual breakdowns, country breakdowns and equal-player metrics are in each run folder.

## January-only benchmark

Both procedures below are evaluated on the same January candidate/date rows. Each chooses its model using its own validation cadence. The CSV also compares every identical model family.

| Training snapshots | Chosen model | January test log loss | Brier | Average precision |
| --- | --- | ---: | ---: | ---: |
| monthly | base_rate | 0.435 | 0.128 | 0.137 |
| annual | context_only | 0.428 | 0.126 | 0.216 |

This compares forecasting procedures, not a causal effect of more observations. Fixed regularization also behaves differently as training rows increase.

## Horizon consistency and limitations

Independent horizon models violate increasing probability with longer horizons in 1/1358 shared forecasts. Raw probabilities are retained; they are not a coherent survival curve.

The sample still covers IPL pathways. Country affiliation is conservatively dated, international history is incomplete, and overseas cohorts are small. Outcomes describe recorded entry; this does not establish comprehensive cross-country accuracy or discrimination.

For definitions, censoring, leakage safeguards and design choices see [monthly design](../docs/monthly_design.md).
