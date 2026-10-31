# International-entry prediction protocol

## Question, unit and targets

At each monthly cutoff, for a player active in the IPL with no known earlier
senior international appearance, predict recorded Test, ODI or T20I participation
during the next H calendar months. H=12 is primary; H=6 and H=24 are comparisons.
The unit is player × cutoff. Outcomes are any recorded entry and expected
recorded match count, including zeros. There is no causal estimand. The
[monthly design](monthly_design.md) records the timing and evaluation choices.

The panel begins in January 2010 and ends at the latest fully observed window
for each horizon, using data through December 2025. The default unscored forecast
is January 2026. Candidates need an IPL appearance in the preceding 24 months
and country affiliation known at cutoff. Earlier international participation
for any side removes a player; changing countries does not create a new debut.
Future outcomes also span any side, while evaluation attributes the player to
the affiliation known at cutoff.

Season nationality becomes available on January 1 of the following year because
auction dates are not consistently available. It is a proxy for affiliation,
not verified legal or ICC eligibility. It is never inferred from a player's
name, franchise location or later national selection. Multiple conflicting
country assignments exclude the player from the cutoff when the conflict is
known onward; a later conflict cannot remove an earlier valid snapshot. Countries
with no international appearance in the local archive before the cutoff are
unsupported and excluded. At present this excludes Afghanistan. At least one
prior match is only a support gate, not a completeness guarantee.

## Data and identity contract

The importer reads IPL JSON in `ipl_auction`, raw international Cricsheet JSON in
`war`, the `side_order` calendar and auction nationality/alias tables. Only men's
international records and IPL performance are used, through December 2025. It
uses the raw international history rather than a prepared recent-only T20I file.
No additional domestic competition has been added in this extension.

| File | Grain and purpose |
| --- | --- |
| `performances.csv` | Unique player UUID × IPL match; completed-match date and count statistics. |
| `eligibility.csv` | Unique player UUID × country, with earliest `known_from`; despite its filename this contains affiliation evidence, not certified eligibility. |
| `international_appearances.csv` | Unique player UUID × match, with country, start date and format. |
| `prior_appearances.csv` | Independently sourced cap evidence; excludes earlier caps and contributes a known event within a target window without duplicating an archived same-date appearance. |
| `calendar.csv` | Unique match ID × country, including both sides of each fixture. |
| `panel_Hm.csv` | Unique player UUID × cutoff; country, target window, observed labels, gap diagnostic and 24 numeric performance features. |

Cricsheet UUID is the primary key. Names and auction IDs never enter the model.
The auction crosswalk can have several auction IDs for one UUID because its
source registry contains duplicate entries. Exact scorecard names and explicit
reference links take precedence over sibling aliases. Reviewed links remain
retrospective identity interpretations; they have not all been independently
certified. Collision corrections and supporting evidence are recorded in
[identity notes](identity_notes.md). Conflicting affiliations, unresolved names,
unlinked players, linkage coverage and source hashes are exported.

A scorecard listing the same UUID twice is quarantined in full. Its conflicting
rows are exported and it remains missing in the calendar comparison. A partial
or ambiguous lineup must not certify a complete match. Alias differences in
country names are normalized before calendar joins.

## Coverage and interpretation of Y

`first_recorded_appearances.csv` gives archive dates, not verified debut dates.
Pre-2008 records help exclude previously capped players, but are not exhaustive.
Independently confirmed earlier appearances can also exclude players: the
current reference covers Alfonso Thomas and Matheesha Pathirana, whose earlier
caps are absent from this archive. Each verified record can also supply one observed appearance if it falls within
a target window and has no same-date archived appearance. It never certifies a
complete lineup or complete match-count history. These targeted corrections do
not certify remaining debuts.

Missing fixtures are compared on country and string match ID. Some missing
calendar fixtures were abandoned without play, so the number of missing fixtures
is not necessarily the number of missing official appearances. Coverage exports
show counts by country, format and year. `missing_affiliation_matches` counts
missing fixtures during the target window for the **cutoff affiliation only**.
Zero does not certify complete any-team outcomes, or complete pre-cutoff history.
A player switching to a different team can have outcome gaps outside this flag.

The implementation therefore estimates recorded entry and observed match counts.
Missed earlier caps can place already-capped players in the risk set; missed
future games can create false zeros or lower counts. A matured two-year window
means calendar follow-up has ended, not that every match is observed. Countries
with no records are excluded, but partially observed countries still require
caution. Country-only prediction can reflect recording differences as well as
real selection opportunities.

IPL participation is itself selective. Most overseas IPL players already have
international caps, leaving very small overseas entry cohorts. All countries in
the nationality table need not appear in the risk panel. Country results must
show denominators and cannot be read as comprehensive domestic selection models.
The India cohort dominates pooled results. Historical discrimination questions
remain outside this dataset's coverage.

## Predictors

Compute seven totals and four rates for each of two windows: all observed IPL
matches before cutoff, and matches during the preceding two years.

| Totals | Rates |
| --- | --- |
| Matches, runs, balls faced, dismissals, wickets, legal balls bowled, runs conceded | Runs/dismissals; 100 × runs/balls faced; runs conceded/wickets; 6 × runs conceded/balls bowled |

Add days since last IPL appearance and days since first observed IPL appearance,
for 24 numeric features. No age, role, first-class statistics, WAR, region or caste
is currently included. Career always means observed IPL career. Missing rate
denominators stay missing; medians, missing indicators and scaling are learned
only from the training fold. Country indicators are learned from training data
alongside calendar month using `OneHotEncoder(handle_unknown="ignore")`; unseen countries have zero country
indicators, rather than being mapped to an existing country. See the official
[encoder documentation](https://scikit-learn.org/1.8/modules/generated/sklearn.preprocessing.OneHotEncoder.html).

DNB players retain their match with zero runs and dismissals. Wides do not count
as balls faced; wides and no-balls do not count as legal bowling deliveries.
Byes/leg-byes/penalty extras are excluded from bowler runs conceded. Run-outs,
retirement and obstructing the field do not produce bowler wickets. Super-over
deliveries are excluded. Listed replacement/impact players can count as
participants; this is not a claim about the original XI.

## Models and evaluation

Compare pooled historical entry rate; country/calendar-only logistic regression;
performance-only logistic and boosted trees; and the same models with country and
calendar-month indicators. All logistic models use C=0.1 and max_iter=5000.
Boosting uses 100 iterations, 7 leaves, minimum 20 examples per leaf, L2=10,
seed 2026 and no random early-stopping split. Count comparisons are zero, pooled
mean, performance-only Poisson and Poisson with context, using alpha=10.
Settings are initial fixed choices, not a tuned optimum. The same C with more
monthly training rows changes regularization relative to accumulated loss; a
cadence comparison does not isolate the effect of additional observations.

Parameters refit every January. Every training label must end before that fit
date, even for forecasts made later in the year. Features update at each monthly
cutoff. Models and all preprocessing remain fixed during that year. Prediction
outputs distinguish `fit_date` from `cutoff_date`. Arbitrary-date forecasts use
the same latest-January fitting rule.

Validation covers 2017–2019 and test covers mature cutoffs in 2022–2024. Each
horizon/cadence selects its own classifier by pooled validation log loss. Monthly
procedures validate on months; annual benchmarks validate on January snapshots.
The common January 2022–January 2024 period makes horizon comparisons transparent.
January comparisons require identical candidate/date/outcome rows. Selection
never chooses the best test model retrospectively.

See the monthly design for metrics and dependence. Pooled probability losses
weight player snapshots equally. Within each reported slice, equal-player scores
give each player total weight one, divided equally over that player's snapshots.
Country-specific and equal-country metrics are also exported. Small country
samples cannot establish broad predictive validity. Unique entrants are counted
separately from repeated positive rows.

Top-ten rankings use country × cutoff pools. When fewer than ten candidates are
available, all are taken and recall can become mechanically perfect. Tied scores
use arbitrary UUID order. Calibration compares bin-level predicted and observed
frequencies. A pooled baseline can have nontrivial ROC AUC because its fitted
rate changes between years.

Count forecasts measure opportunity and persistence, not skill. Compare MAE and
Poisson deviance. Zero counts can win MAE for rare outcomes but have infinite
deviance for positive outcomes. Forecast counts are expected values and need not
be integers. Future batting/bowling quality requires separate role- and
exposure-aware targets.

Independent horizon classifiers can violate increasing probability with horizon.
Export those violations; do not claim these probabilities are a survival curve.
A later landmark survival model could impose coherent timing probabilities.

Fitted forecasting models are ignored local joblib files in each run's `models/`
folder. Only load trusted artifacts. Their metadata records horizon, fitting
date, target and input columns. Default forecasts use January 2026 inputs and
have no observed 2026-onward evaluation labels.

## Validation and remaining work

Tests cover future-feature invariance, horizon boundaries, immature follow-up,
prior caps for any team, independent prior-cap evidence, future affiliation and
coverage evidence, dated affiliation conflicts, duplicate/negative inputs,
delivery accounting, identity collisions, unseen countries, within-country
rankings and label maturity in rolling fits. Runtime versions accompany outputs.

Identity and coverage corrections were made during development and after
inspecting outputs. This is an exploratory temporal backtest, not a preregistered
or untouched confirmation sample. Next steps are broader domestic histories,
verified debut registers and format-specific outcomes. Country coverage must be
adequate before interpreting country differences; prediction residuals alone
would not establish region or caste discrimination.
