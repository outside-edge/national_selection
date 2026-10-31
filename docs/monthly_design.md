# Monthly prediction and backtest design

Specified on 2026-10-30 before fitting the monthly models. The earlier annual
results and their data problems have already been inspected. This extension is
exploratory; the later calendar periods are held out from model selection, not
untouched by all project development.

## Question and timing

At the start of each month t, for an active player with no known senior
international appearance before t, estimate the probability of first recorded
international participation during [t, t + H calendar months). Primary H=12;
comparisons H=6 and H=24. Appearance counts over the same interval are secondary.
Predicting a return or continued selection for previously capped players is a
separate task and is not pooled into this risk set.

The prediction cadence, outcome horizon, and model-refit cadence are independent:
monthly predictions, configurable month horizons, and annual January refits.
The panel builder also accepts arbitrary cutoff dates. A prediction after a
match uses the following day because only dates, not reliable publication times,
are available. Multi-day matches enter X only after their end date. All forecasts
remain conditional on information at t; actual future performances or national
match schedules are never supplied as X.

Monthly landmarks keep players without recent matches under consideration until
the existing 24-month activity rule expires. Post-match-only sampling would weight
frequent players more heavily and omit some idle candidate-months. Daily sampling
would create many near-identical rows. Monthly rows are dependent, not new people.

The 24 performance predictors retain the existing career and trailing-24-month
windows so that changing forecast timing does not silently replace the feature
set. Context models add country and calendar month as categorical predictors.
A context-only logistic baseline tests whether performance adds value beyond
country and season. No age, role, WAR, future schedule, region or caste is added.

Affiliation evidence retains its conservative January-after-season effective
date. Exact match dates do not magically date nationality evidence. This still
excludes some first-season prospects. Partial international coverage remains a
separate problem from administrative right censoring.

## Evaluation protocol

Build fully followed-up monthly rows from January 2010 through the last mature
cutoff for each horizon, using observations through 2025-12-31. Do not retain
recent observed positives while dropping recent unobserved negatives; use the
same mature-window criterion for both classes in this classification backtest.

Refit every January. For every forecast during year y, training uses only rows
with label_end strictly before January 1 of y. Update X at each forecast month,
but hold the fitted model fixed until the following January. Report that actual
fit date in every prediction row and assert training label maturity against it.

Validation: monthly forecasts in 2017–2019. Select the classifier separately for
each horizon using pooled validation log loss. Test: monthly forecasts in
2022–2024 with complete follow-up. For H=24, only January 2024 is mature within
that last year. Also report the common January 2022–January 2024 forecast period
for all horizons so differences in test-date coverage are visible. Do not use
2025 cutoffs to lengthen the shorter-horizon test silently.

Retain a January-only training/evaluation benchmark at each horizon. Compare
its predictions with monthly-trained models on the same January test dates and
identical candidate IDs, for each model family as well as each policy's chosen
classifier. This separates common-date accuracy from the additional coverage
provided by monthly forecasts. It cannot establish that more rows alone caused
an improvement.

Compare pooled base rate, context-only logistic, performance-only logistic and
boosting, and performance-plus-context logistic and boosting. Keep existing fixed
hyperparameters. Count models: always zero, pooled mean, performance-only Poisson,
and performance-plus-context Poisson. No tuning on the test period.

## How performance will be reported

Report log loss, Brier score, average precision, ROC AUC, calibration bins and
probability means; report top-10 precision/recall within country and cutoff.
Show baseline-relative changes, sample sizes, unique players and unique entrants.
The number of positive player-months is not the number of distinct debuts.
Always-zero classification accuracy is uninformative for this rare outcome.
Count evaluation uses MAE and Poisson deviance against zero/mean baselines.

Provide pooled, per-year, per-country and common-period results. Compare the
validation-chosen policy, rather than relabeling the best test model as chosen.
Show January-only matched-date comparisons separately. Report equal-player
weighted log loss and Brier (each player gets total weight one within the reported
slice) as sensitivity checks to the primary player-month
weighting. Do not report row-independent uncertainty intervals; repeated players
and common country/calendar shocks would require appropriate resampling.

Independent horizon models can violate monotonicity (a 6-month probability may
exceed a 12-month probability). Export the frequency of violations on shared
player/cutoff rows rather than silently forcing coherence. A landmark survival
model could later provide a coherent distribution over entry times. A one-month
hazard model cannot be multiplied forward using actual future performance Xs;
those are unknown at prediction time.

This follows the repeated-landmark prediction idea described by
[van Houwelingen (2007)](https://doi.org/10.1111/j.1467-9469.2006.00529.x), implemented
here as direct horizon classifiers. Chronological evaluation follows the
[time-series validation principle](https://scikit-learn.org/1.8/modules/cross_validation.html#time-series-split),
with a label-maturity restriction stricter than simply ordering feature dates.

## Required checks

Test month-end and leap-year horizons; matches ending on the cutoff; independence
from future performance; removal immediately after earlier caps; verified cap
records; unsupported and conflicting affiliations; immature-window exclusion;
training labels ending before each annual fit; no future category fitting;
matched January evaluation rows; and exact preserved forecast probabilities.
Keep the existing accounting and identity regression tests.

The independent design review required horizon-specific baseline comparisons,
explicit per-cadence selection, within-slice player weights, separate fitting and
forecast dates, and unique-entrant counts. These are implemented. Verified cap
evidence now contributes a known event to a target window if missing from the
archive, in addition to excluding earlier caps; this avoids a known event being
labeled zero when more frequent cutoffs make such windows possible.

For other requested month horizons, validation windows must also finish before
January 2022, when test-policy selection occurs. Evaluation years without a
mature cutoff are skipped; runs without both validation and test data fail.
Cross-horizon summaries use the actual intersection of test forecast dates.

The scoring API rejects a forecast whose annual fit precedes the availability
of its validation-selected policy, or whose cutoff is later than documented
input coverage plus one day. Training, snapshot and policy horizons must match.
Arbitrary-date scoring is supported, but accuracy is evaluated at month starts.
