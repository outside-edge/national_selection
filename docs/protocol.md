# Pilot protocol

## Target and risk set

On January 1 of each year from 2010 through 2024, take players with an IPL
appearance in the preceding two calendar years, a linked Indian nationality
record from an earlier season, and no earlier recorded senior India appearance.
The positive label is any recorded Test, ODI or T20I appearance during the
following two calendar years. The count target is appearances during the same
window, including zero for non-entrants. Count measures opportunity and persistence,
not cricketing quality. Players can recur in successive risk sets until entry.

Season nationality is conservatively available from January 1 of the following
year, since auction timestamps are not consistently available. This can exclude
first-season candidates. Unknown nationality and ambiguous identity are excluded
and reported. The contemporary candidates are not chosen using eventual India
membership. Institutional nationality records are used; nationality is not inferred
from names. Retrospective identity crosswalks are allowed but are never predictors.

The data adapter reads raw IPL JSON in `ipl_auction`, raw international Cricsheet
JSON in `war`, the `side_order` international calendar, and `ipl_auction` nationality
and alias tables. It does not depend on an incomplete recent-only prepared T20I
extract. Modern match calendars are compared by string match ID. The missing
matches export includes no-result fixtures and absent Afghanistan fixtures; a
listed match is not automatically a missing official appearance. Until resolved,
counts are recorded counts and entry dates are first observed dates. Pre-2008
international records provide a burn-in exclusion, but their completeness is not
certified. A prior appearance missed in all sources could leave a capped player
in the nominally uncapped pool. Do not make a census-level debut claim.

## Features and identities

For available IPL career history and the preceding two years, calculate matches,
runs, balls faced, dismissals, wickets, legal balls bowled, runs conceded, batting
average, strike rate, bowling average and economy. Add days since the last IPL
match and days since the first observed IPL match. Career means observed IPL
career, not full domestic career. There is no age, first-class performance,
association, caste, nationality, name or player-ID feature.

Keep DNB players in appearances with zero runs and zero dismissals. Wides do not
count as balls faced; wides and no-balls do not count as legal bowling balls.
Byes and leg-byes do not count against bowlers. Run-outs, retirement and obstructing
the field do not produce bowling wickets. Super-over deliveries are excluded.
Some modern Cricsheet participant lists include replacement/impact players;
`matches` here means listed participation, not a claim about the original XI.
Undefined rates stay missing, with medians and missing indicators fitted only on
training data. The primary identifier is the provider's Cricsheet UUID; canonical
names are displays. `player_crosswalk.csv` preserves sibling auction IDs separately.
Multiple auction IDs can point to one person because that registry has duplicate
name entries; unresolved rows remain null rather than forcing a false merge.

Exact scorecard names and explicit links in the packaged reference file take
precedence over sibling aliases. This matters because a sibling alias maps Ravi
Bishnoi to R Bishnoi and Navdeep Saini to N Saini, names belonging to different
player IDs in the IPL archive. The reference links are manually curated identity
interpretations and still warrant independent verification before inferential
research. `nationality_links.csv` records method, original name and effective date.
A conflicting Indian/non-Indian nationality assignment stops import; conflicts
solely between overseas labels are recorded and do not enter the Indian cohort.

## Forecast evaluation

Validation cutoffs are January 2017, 2018 and 2019; test cutoffs are January 2022,
2023 and 2024. Each fit uses all earlier snapshots with label end strictly before
the cutoff. Thus a January 2022 fit can use the 2020 snapshot, whose outcomes end
in December 2021, but cannot use 2021 outcomes extending through 2022. This is a
rolling evaluation, so later fits can use outcomes that have since matured.

All model families use the same rows and feature columns. Logistic regression
uses C=0.1. Boosting uses 100 iterations, at most 7 leaves, minimum 20 examples per
leaf, L2 regularization 10, seed 2026 and no random early-stopping split. Poisson
regression uses alpha=10. These initial settings are not a tuned optimum.

Compare classification log loss, Brier score, average precision, ROC AUC,
calibration and top-10 precision/recall within each snapshot. A base-rate model
can have pooled AUC different from 0.5 because its prediction changes by year;
use annual scores to distinguish across-year and within-year ranking. Ties are
broken by player ID, which is deterministic but arbitrary. Top-10 base-rate
performance is therefore a tie-breaking reference, not a learned ranking.

Compare count MAE and Poisson deviance. The always-zero forecast can win MAE in
sparse outcomes and must be shown alongside the mean forecast. Its true Poisson
deviance is infinite when any positive count occurs; report infinity rather than
claiming that an epsilon floor is the exact zero-model deviance. Predictions are
expected counts and need not be integers.

Overlapping two-year windows and repeated players make rows dependent. The output
is descriptive predictive evaluation without independent-row confidence intervals.
Do not interpret 169 player-snapshot rows as 169 independent people or 36 positive
snapshots as 36 distinct debutants. No discrimination estimates are made.

The January 2026 forecast refits on all labels completed through 2025. It exports
the validation-selected classifier, logistic comparison, Poisson expected count
and historical mean count. It has no observed 2026–2027 outcome labels. Model
artifacts are local joblib files under ignored `out/models/`; load only artifacts
from trusted runs. The forecast output is a research result, not validated scouting
advice. Reconcile identity and appearance gaps and add first-class histories before
claiming comprehensive national-selection forecasting.

## Validation and extensions

Tests cover future-feature invariance, two-year boundary dates, censoring,
pre-existing caps, future nationality evidence, duplicate/invalid records, delivery
accounting, DNB/super-over handling, and label maturity in rolling fits. Existing
input hashes are recorded, and package/runtime versions accompany results.

Next extensions can use the same performance/eligibility/appearance schema for
Ranji histories, age/role attributes with dated sources, verified debut registers,
and separate format targets. Batting and bowling international success need
exposure-aware outcomes and role-specific evaluation; they should not be silently
replaced by a generic career average among only the players who were selected.
