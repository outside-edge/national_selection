# 6-month international-entry backtest (annual)

Validation selected **boosting** by log loss. Parameters refit each January; inputs update at each forecast cutoff.

Test cutoffs: 2022-01-01 through 2024-01-01; 3 forecast dates.
173 player snapshots; 90 players; 10 positive snapshots; 10 distinct observed entrants.

Labels are recorded entry and appearances. Neither a mature horizon nor more snapshots repairs archive gaps.

| Model | Log loss | Brier | Average precision | ROC AUC | Top-10 precision | Mean probability |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| base_rate | 0.223 | 0.055 | 0.050 | 0.413 | 6.2% | 4.8% |
| boosting | 0.244 | 0.057 | 0.174 | 0.591 | 9.4% | 5.4% |
| boosting_context | 0.242 | 0.056 | 0.123 | 0.606 | 9.4% | 4.9% |
| context_only | 0.221 | 0.054 | 0.101 | 0.501 | 6.2% | 4.7% |
| logistic | 0.196 | 0.051 | 0.260 | 0.747 | 12.5% | 4.7% |
| logistic_context | 0.194 | 0.051 | 0.269 | 0.764 | 12.5% | 4.6% |

Observed entry frequency: 5.8%. Lower log loss/Brier are better; higher ranking measures are better. Top ten are selected separately within each country/date; small pools can make recall mechanically perfect. Baseline ties use arbitrary UUID order.

| Count model | MAE | Poisson deviance |
| --- | ---: | ---: |
| mean_count | 0.447 | 1.544 |
| poisson | 0.445 | 1.512 |
| poisson_context | 0.445 | 1.511 |
| zero_count | 0.254 | inf |

Counts measure opportunity and persistence. A zero forecast can win MAE but has infinite deviance on positive outcomes.

| Country | Snapshots | Players | Positive snapshots | Unique entrants | Max missing affiliation fixtures |
| --- | ---: | ---: | ---: | ---: | ---: |
| England | 1 | 1 | 1 | 1 | 0 |
| India | 171 | 88 | 9 | 9 | 4 |
| South Africa | 1 | 1 | 0 | 0 | 0 |

Country is dated auction nationality, a proxy for affiliation. Outcomes and prior-cap exclusions span all national teams. The missing-fixture flag covers only the cutoff affiliation. Zero-coverage countries are excluded; partial coverage still limits labels.

Overlapping horizons, repeated players and country/calendar shocks make rows dependent. Improvements are descriptive backtest differences, not precise independent-row estimates. See equal-player metrics, year/country metrics, common-period scores and calibration CSVs. Overseas samples remain too small for broad validation.
