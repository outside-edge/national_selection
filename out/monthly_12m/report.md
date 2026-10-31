# 12-month international-entry backtest (monthly)

Validation selected **base_rate** by log loss. Parameters refit each January; inputs update at each forecast cutoff.

Test cutoffs: 2022-01-01 through 2024-12-01; 36 forecast dates.
1987 player snapshots; 93 players; 245 positive snapshots; 26 distinct observed entrants.

Labels are recorded entry and appearances. Neither a mature horizon nor more snapshots repairs archive gaps.

| Model | Log loss | Brier | Average precision | ROC AUC | Top-10 precision | Mean probability |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| base_rate | 0.384 | 0.110 | 0.111 | 0.437 | 18.4% | 8.3% |
| boosting | 0.339 | 0.097 | 0.366 | 0.756 | 33.1% | 8.0% |
| boosting_context | 0.334 | 0.096 | 0.386 | 0.771 | 32.2% | 8.1% |
| context_only | 0.384 | 0.110 | 0.121 | 0.472 | 18.4% | 8.2% |
| logistic | 0.345 | 0.093 | 0.417 | 0.735 | 34.4% | 8.7% |
| logistic_context | 0.342 | 0.093 | 0.415 | 0.743 | 32.8% | 8.6% |

Observed entry frequency: 12.3%. Lower log loss/Brier are better; higher ranking measures are better. Top ten are selected separately within each country/date; small pools can make recall mechanically perfect. Baseline ties use arbitrary UUID order.

| Count model | MAE | Poisson deviance |
| --- | ---: | ---: |
| mean_count | 1.250 | 4.407 |
| poisson | 1.225 | 4.088 |
| poisson_context | 1.225 | 4.089 |
| zero_count | 0.856 | inf |

Counts measure opportunity and persistence. A zero forecast can win MAE but has infinite deviance on positive outcomes.

| Country | Snapshots | Players | Positive snapshots | Unique entrants | Max missing affiliation fixtures |
| --- | ---: | ---: | ---: | ---: | ---: |
| England | 1 | 1 | 1 | 1 | 1 |
| India | 1978 | 91 | 236 | 24 | 6 |
| South Africa | 8 | 1 | 8 | 1 | 2 |

Country is dated auction nationality, a proxy for affiliation. Outcomes and prior-cap exclusions span all national teams. The missing-fixture flag covers only the cutoff affiliation. Zero-coverage countries are excluded; partial coverage still limits labels.

Overlapping horizons, repeated players and country/calendar shocks make rows dependent. Improvements are descriptive backtest differences, not precise independent-row estimates. See equal-player metrics, year/country metrics, common-period scores and calibration CSVs. Overseas samples remain too small for broad validation.
