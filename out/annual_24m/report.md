# 24-month international-entry backtest (annual)

Validation selected **base_rate** by log loss. Parameters refit each January; inputs update at each forecast cutoff.

Test cutoffs: 2022-01-01 through 2024-01-01; 3 forecast dates.
173 player snapshots; 90 players; 38 positive snapshots; 25 distinct observed entrants.

Labels are recorded entry and appearances. Neither a mature horizon nor more snapshots repairs archive gaps.

| Model | Log loss | Brier | Average precision | ROC AUC | Top-10 precision | Mean probability |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| base_rate | 0.553 | 0.178 | 0.188 | 0.385 | 34.4% | 14.4% |
| boosting | 0.538 | 0.166 | 0.405 | 0.665 | 46.9% | 14.3% |
| boosting_context | 0.536 | 0.165 | 0.417 | 0.673 | 46.9% | 13.9% |
| context_only | 0.552 | 0.178 | 0.238 | 0.425 | 34.4% | 14.2% |
| logistic | 0.529 | 0.164 | 0.411 | 0.646 | 46.9% | 13.8% |
| logistic_context | 0.526 | 0.164 | 0.413 | 0.655 | 46.9% | 13.6% |

Observed entry frequency: 22.0%. Lower log loss/Brier are better; higher ranking measures are better. Top ten are selected separately within each country/date; small pools can make recall mechanically perfect. Baseline ties use arbitrary UUID order.

| Count model | MAE | Poisson deviance |
| --- | ---: | ---: |
| mean_count | 3.538 | 10.286 |
| poisson | 3.364 | 9.348 |
| poisson_context | 3.363 | 9.348 |
| zero_count | 2.520 | inf |

Counts measure opportunity and persistence. A zero forecast can win MAE but has infinite deviance on positive outcomes.

| Country | Snapshots | Players | Positive snapshots | Unique entrants | Max missing affiliation fixtures |
| --- | ---: | ---: | ---: | ---: | ---: |
| England | 1 | 1 | 1 | 1 | 2 |
| India | 171 | 88 | 36 | 23 | 6 |
| South Africa | 1 | 1 | 1 | 1 | 5 |

Country is dated auction nationality, a proxy for affiliation. Outcomes and prior-cap exclusions span all national teams. The missing-fixture flag covers only the cutoff affiliation. Zero-coverage countries are excluded; partial coverage still limits labels.

Overlapping horizons, repeated players and country/calendar shocks make rows dependent. Improvements are descriptive backtest differences, not precise independent-row estimates. See equal-player metrics, year/country metrics, common-period scores and calibration CSVs. Overseas samples remain too small for broad validation.
