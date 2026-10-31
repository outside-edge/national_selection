# Two-year international-entry pilot

Validation selected **base_rate** by log loss.

Later evaluation: 173 player snapshots, 90 distinct players, 38 positive snapshots across 2022–2024 cutoffs.

Labels are recorded international entry and recorded appearances. Missing archive matches and unresolved identities limit interpretation.

## Classification

| Model | Test log loss | Brier | Average precision | Top-10 precision |
| --- | ---: | ---: | ---: | ---: |
| base_rate | 0.553 | 0.178 | 0.188 | 34.4% |
| boosting | 0.538 | 0.166 | 0.405 | 46.9% |
| boosting_country | 0.536 | 0.165 | 0.417 | 46.9% |
| country_only | 0.552 | 0.178 | 0.238 | 34.4% |
| logistic | 0.529 | 0.164 | 0.411 | 46.9% |
| logistic_country | 0.526 | 0.164 | 0.413 | 46.9% |

Lower log loss and Brier are better. Higher average precision and top-10 precision are better. Up to ten players per country and year form the ranking comparison; tied base-rate ranks use arbitrary stable ID order.

## Match counts

| Model | Test MAE | Poisson deviance |
| --- | ---: | ---: |
| mean_count | 3.538 | 10.286 |
| poisson | 3.364 | 9.348 |
| poisson_country | 3.363 | 9.348 |
| zero_count | 2.520 | inf |

Counts measure opportunity, not performance quality. Always-zero predictions can minimize absolute error for sparse outcomes but have infinite Poisson deviance on positive outcomes.

These are rolling chronological fits with fully matured labels. Overlapping windows and repeated players are dependent. Identity corrections were made during development; this is an exploratory backtest rather than an untouched confirmation sample.

## Coverage by country

Country is the auction nationality recorded before each cutoff, a proxy for affiliation.
Outcomes count appearances for any national side; earlier appearances for any side exclude a player.

| Country | Test snapshots | Distinct players | Positive snapshots | Missing-calendar fixtures in label windows (max) |
| --- | ---: | ---: | ---: | ---: |
| England | 1 | 1 | 1 | 2 |
| India | 171 | 88 | 36 | 6 |
| South Africa | 1 | 1 | 1 | 5 |

Per-country metrics and equal-country averages are exported separately. Small country samples cannot establish country-specific predictive accuracy. The pooled model is dominated by the largest cohort. IPL participation is a selective pathway, especially for overseas players who often already have caps. These results do not cover every country's domestic player pool.
