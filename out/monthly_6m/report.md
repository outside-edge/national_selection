# 6-month international-entry backtest (monthly)

Validation selected **context_only** by log loss. Parameters refit each January; inputs update at each forecast cutoff.

Test cutoffs: 2022-01-01 through 2024-12-01; 36 forecast dates.
1987 player snapshots; 93 players; 139 positive snapshots; 26 distinct observed entrants.

Labels are recorded entry and appearances. Neither a mature horizon nor more snapshots repairs archive gaps.

| Model | Log loss | Brier | Average precision | ROC AUC | Top-10 precision | Mean probability |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| base_rate | 0.258 | 0.066 | 0.067 | 0.481 | 9.8% | 4.8% |
| boosting | 0.236 | 0.061 | 0.204 | 0.748 | 21.7% | 4.6% |
| boosting_context | 0.239 | 0.061 | 0.206 | 0.741 | 22.2% | 4.5% |
| context_only | 0.258 | 0.065 | 0.102 | 0.538 | 9.8% | 4.7% |
| logistic | 0.229 | 0.058 | 0.297 | 0.735 | 20.9% | 5.2% |
| logistic_context | 0.231 | 0.058 | 0.289 | 0.731 | 20.9% | 5.1% |

Observed entry frequency: 7.0%. Lower log loss/Brier are better; higher ranking measures are better. Top ten are selected separately within each country/date; small pools can make recall mechanically perfect. Baseline ties use arbitrary UUID order.

| Count model | MAE | Poisson deviance |
| --- | ---: | ---: |
| mean_count | 0.525 | 2.187 |
| poisson | 0.522 | 2.092 |
| poisson_context | 0.522 | 2.092 |
| zero_count | 0.353 | inf |

Counts measure opportunity and persistence. A zero forecast can win MAE but has infinite deviance on positive outcomes.

| Country | Snapshots | Players | Positive snapshots | Unique entrants | Max missing affiliation fixtures |
| --- | ---: | ---: | ---: | ---: | ---: |
| England | 1 | 1 | 1 | 1 | 0 |
| India | 1978 | 91 | 132 | 24 | 5 |
| South Africa | 8 | 1 | 6 | 1 | 1 |

Country is dated auction nationality, a proxy for affiliation. Outcomes and prior-cap exclusions span all national teams. The missing-fixture flag covers only the cutoff affiliation. Zero-coverage countries are excluded; partial coverage still limits labels.

Overlapping horizons, repeated players and country/calendar shocks make rows dependent. Improvements are descriptive backtest differences, not precise independent-row estimates. See equal-player metrics, year/country metrics, common-period scores and calibration CSVs. Overseas samples remain too small for broad validation.
