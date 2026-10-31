# 12-month international-entry backtest (annual)

Validation selected **context_only** by log loss. Parameters refit each January; inputs update at each forecast cutoff.

Test cutoffs: 2022-01-01 through 2024-01-01; 3 forecast dates.
173 player snapshots; 90 players; 25 positive snapshots; 25 distinct observed entrants.

Labels are recorded entry and appearances. Neither a mature horizon nor more snapshots repairs archive gaps.

| Model | Log loss | Brier | Average precision | ROC AUC | Top-10 precision | Mean probability |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| base_rate | 0.430 | 0.127 | 0.137 | 0.471 | 18.8% | 9.0% |
| boosting | 0.388 | 0.118 | 0.317 | 0.754 | 34.4% | 9.6% |
| boosting_context | 0.380 | 0.116 | 0.343 | 0.769 | 37.5% | 9.4% |
| context_only | 0.428 | 0.126 | 0.216 | 0.530 | 18.8% | 8.9% |
| logistic | 0.414 | 0.118 | 0.317 | 0.706 | 34.4% | 8.8% |
| logistic_context | 0.412 | 0.118 | 0.323 | 0.715 | 34.4% | 8.7% |

Observed entry frequency: 14.5%. Lower log loss/Brier are better; higher ranking measures are better. Top ten are selected separately within each country/date; small pools can make recall mechanically perfect. Baseline ties use arbitrary UUID order.

| Count model | MAE | Poisson deviance |
| --- | ---: | ---: |
| mean_count | 1.610 | 6.049 |
| poisson | 1.585 | 5.762 |
| poisson_context | 1.584 | 5.762 |
| zero_count | 1.197 | inf |

Counts measure opportunity and persistence. A zero forecast can win MAE but has infinite deviance on positive outcomes.

| Country | Snapshots | Players | Positive snapshots | Unique entrants | Max missing affiliation fixtures |
| --- | ---: | ---: | ---: | ---: | ---: |
| England | 1 | 1 | 1 | 1 | 1 |
| India | 171 | 88 | 23 | 23 | 4 |
| South Africa | 1 | 1 | 1 | 1 | 1 |

Country is dated auction nationality, a proxy for affiliation. Outcomes and prior-cap exclusions span all national teams. The missing-fixture flag covers only the cutoff affiliation. Zero-coverage countries are excluded; partial coverage still limits labels.

Overlapping horizons, repeated players and country/calendar shocks make rows dependent. Improvements are descriptive backtest differences, not precise independent-row estimates. See equal-player metrics, year/country metrics, common-period scores and calibration CSVs. Overseas samples remain too small for broad validation.
