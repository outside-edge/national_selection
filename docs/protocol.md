# International-entry prediction protocol

## Question, unit and targets

For a player active in the IPL, with no known prior senior international
appearance at a January cutoff, predict any recorded Test, ODI or T20I appearance
in the next two calendar years. The unit is player × cutoff. The principal
quantity is a probability of recorded entry; the secondary quantity is the
expected recorded match count, including zeros. There is no causal estimand.

The panel spans January 2010–2024 cutoffs, with outcomes through December 2025.
The forecast snapshot is January 2026, covering 2026–2027. Every player must have
an IPL appearance in the previous two years and a nationality record from a
season before the cutoff. Each player is removed after an earlier international
appearance for **any** national side. Changing countries does not create a new
debut. Future outcomes also include any national side; country attribution in
evaluation remains the affiliation known at the cutoff.

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
| `prior_appearances.csv` | Independently sourced earlier cap evidence, used only for risk-set exclusion; not a complete debut register or match-count supplement. |
| `calendar.csv` | Unique match ID × country, including both sides of each fixture. |
| `panel.csv` | Unique player UUID × cutoff; country, target window, observed labels, gap diagnostic and 24 numeric performance features. |

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
caps are absent from this archive. It does not add fictional complete lineups
or match counts. These targeted corrections do not certify remaining debuts.

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
using `OneHotEncoder(handle_unknown="ignore")`; unseen countries have zero country
indicators, rather than being mapped to an existing country. See the official
[encoder documentation](https://scikit-learn.org/1.8/modules/generated/sklearn.preprocessing.OneHotEncoder.html).

DNB players retain their match with zero runs and dismissals. Wides do not count
as balls faced; wides and no-balls do not count as legal bowling deliveries.
Byes/leg-byes/penalty extras are excluded from bowler runs conceded. Run-outs,
retirement and obstructing the field do not produce bowler wickets. Super-over
deliveries are excluded. Listed replacement/impact players can count as
participants; this is not a claim about the original XI.

## Models and evaluation

Compare a pooled historical base rate; country-only logistic regression;
performance-only logistic regression and boosted trees; and the same two models
with country indicators added. All logistic models use C=0.1 and max_iter=5000.
Boosting uses 100 iterations, 7 leaves, minimum 20 examples per leaf, L2=10,
seed 2026 and no random early-stopping split. Count comparisons are zero, pooled
mean, performance-only Poisson regression and Poisson with country indicators,
using alpha=10. The full three-way country/performance ablation applies to
classification; there is no country-only count model. Settings are initial fixed
choices, not a tuned optimum.

Validation cutoffs are January 2017, 2018 and 2019; test cutoffs are January 2022,
2023 and 2024. Each fit uses only snapshots whose label end is strictly before
the forecast cutoff. January 2022 can train on January 2020, whose outcomes ended
in December 2021, but not January 2021. Later fits may use newly matured outcomes.
Classifier selection minimizes pooled validation log loss, without using later
scores to pick the winner. This objective weights player snapshots equally and
therefore largely reflects India. Repeated players and overlapping windows make
rows dependent; no independent-row confidence intervals are reported.

Export pooled, annual and country-specific log loss, Brier, average precision,
ROC AUC and calibration. Equal-country mean log loss/Brier and count MAE are
also exported; these give every represented country equal weight and can be
unstable for very small pools. Country-specific ROC AUC is undefined for a
single-class sample; average precision is undefined without positives.

Top-10 rankings use separate country × cutoff pools, taking all available players
if fewer than ten. Consequently, recall can be mechanically perfect in a small
country pool. These are descriptive diagnostics, not evidence of strong overseas
performance. Tied predictions use arbitrary stable UUID order. Pooled base-rate
AUC can differ from 0.5 because the rate changes by year; annual metrics separate
within-year ranking from changes in average entry probability.

Counts measure opportunity and persistence, not skill. Use MAE and Poisson
deviance. Always-zero predictions can win MAE for sparse outcomes but have infinite
Poisson deviance when any positive outcome occurs. Predicted counts are expected
values and need not be integers. Future performance quality would require separate
role- and exposure-aware targets; estimating quality only among selected players
would answer a different, selected-sample question.

The January 2026 forecast trains on labels completed through December 2025 and
exports the validation-selected classifier plus comparison models. Fitted models
are ignored local joblib files in `out/models/`. Only load trusted artifacts.

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
