# 24-month international-entry backtest (monthly)

Validation selected **base_rate** by log loss. Parameters refit each January; inputs update at each forecast cutoff.

Test cutoffs: 2022-01-01 through 2024-01-01; 25 forecast dates.
1358 player snapshots; 90 players; 295 positive snapshots; 25 distinct observed entrants.

Labels are recorded entry and appearances. Neither a mature horizon nor more snapshots repairs archive gaps.

| Model | Log loss | Brier | Average precision | ROC AUC | Top-10 precision | Mean probability |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| base_rate | 0.556 | 0.179 | 0.206 | 0.464 | 34.7% | 12.8% |
| boosting | 0.570 | 0.174 | 0.339 | 0.673 | 39.4% | 14.6% |
| boosting_context | 0.560 | 0.172 | 0.350 | 0.689 | 41.3% | 14.4% |
| context_only | 0.558 | 0.179 | 0.203 | 0.459 | 34.7% | 12.6% |
| logistic | 0.496 | 0.151 | 0.494 | 0.708 | 52.9% | 13.9% |
| logistic_context | 0.489 | 0.151 | 0.492 | 0.725 | 50.6% | 13.8% |

Observed entry frequency: 21.7%. Lower log loss/Brier are better; higher ranking measures are better. Top ten are selected separately within each country/date; small pools can make recall mechanically perfect. Baseline ties use arbitrary UUID order.

| Count model | MAE | Poisson deviance |
| --- | ---: | ---: |
| mean_count | 3.167 | 9.755 |
| poisson | 3.016 | 8.634 |
| poisson_context | 3.016 | 8.634 |
| zero_count | 2.370 | inf |

Counts measure opportunity and persistence. A zero forecast can win MAE but has infinite deviance on positive outcomes.

| Country | Snapshots | Players | Positive snapshots | Unique entrants | Max missing affiliation fixtures |
| --- | ---: | ---: | ---: | ---: | ---: |
| England | 1 | 1 | 1 | 1 | 2 |
| India | 1349 | 88 | 286 | 23 | 7 |
| South Africa | 8 | 1 | 8 | 1 | 6 |

Country is dated auction nationality, a proxy for affiliation. Outcomes and prior-cap exclusions span all national teams. The missing-fixture flag covers only the cutoff affiliation. Zero-coverage countries are excluded; partial coverage still limits labels.

Overlapping horizons, repeated players and country/calendar shocks make rows dependent. Improvements are descriptive backtest differences, not precise independent-row estimates. See equal-player metrics, year/country metrics, common-period scores and calibration CSVs. Overseas samples remain too small for broad validation.
