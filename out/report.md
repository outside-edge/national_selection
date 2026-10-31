# Two-year international-entry pilot

Validation selected **boosting** by log loss.

Later evaluation: 169 player snapshots, 87 distinct players, 36 positive snapshots across 2022–2024 cutoffs.

Labels are recorded international entry and recorded appearances. Missing archive matches and unresolved identities limit interpretation.

## Classification

| Model | Test log loss | Brier | Average precision | Top-10 precision |
| --- | ---: | ---: | ---: | ---: |
| base_rate | 0.543 | 0.174 | 0.184 | 30.0% |
| boosting | 0.519 | 0.157 | 0.450 | 46.7% |
| logistic | 0.506 | 0.158 | 0.431 | 43.3% |

Lower log loss and Brier are better. Higher average precision and top-10 precision are better. Each year's top ten form the ranking comparison; tied base-rate ranks use arbitrary stable ID order.

## Match counts

| Model | Test MAE | Poisson deviance |
| --- | ---: | ---: |
| mean_count | 3.491 | 10.730 |
| poisson | 3.292 | 9.495 |
| zero_count | 2.562 | inf |

Counts measure opportunity, not performance quality. Always-zero predictions can minimize absolute error for sparse outcomes but have infinite Poisson deviance on positive outcomes.

These are rolling chronological fits with fully matured labels. Overlapping windows and repeated players are dependent. Identity corrections were made during development; this is an exploratory backtest rather than an untouched confirmation sample.
