# National selection

[Forecasts and documentation](https://outside-edge.github.io/national_selection/) ·
[Player tables](https://outside-edge.github.io/national_selection/forecasts.html)

Forecast whether an uncapped IPL player will make a recorded senior international
appearance in the next **H months**, across countries. Forecasts update monthly;
the main horizon is **12 months**, with 6- and 24-month comparisons. Exact match
dates determine which performances can enter each forecast.

[Backtest results](out/report.md) report how well the models predict, against
historical entry-rate and country/calendar baselines. The sample covers the IPL
pathway, not every country's domestic player pool. International archive gaps
mean this is recorded entry, not a certified census of debuts.

## X and Y

One row is a **player × forecast date**, identified by Cricsheet's player UUID.
Previously capped players leave the risk set. Return selection is a separate task.

| Component | Definition |
| --- | --- |
| Main Y: `selected` | At least one recorded Test, ODI or T20I appearance during `[cutoff, cutoff + H months)`, for any national side. Actual participation, rather than squad nomination. |
| Secondary Y: `n_matches` | Recorded appearances in that interval, including zero. Measures opportunity and persistence, not performance quality. |
| Performance Xs | Matches, runs, balls faced, dismissals, wickets, legal balls bowled, runs conceded, batting average, strike rate, bowling average and economy. Each is computed for the observed IPL career and trailing 24 months. |
| Other performance Xs | Days since last IPL appearance and days since first observed IPL appearance. |
| Context Xs | Country affiliation known at cutoff and calendar month, in context-only and combined models. |
| Excluded from X | Names, IDs, future performance or schedules, region and caste. Age, role, first-class statistics and WAR are not yet included. |

A June 1, 2023 forecast uses completed matches through May 31, 2023. Its 12-month
Y covers June 1, 2023 through May 31, 2024. Parameters were fitted on January 1,
2023 using only training outcomes whose entire window had already finished.
Inputs update monthly; fitted parameters update each January.

Monthly forecasts retain inactive candidates under the existing two-year activity
rule and avoid making forecast frequency depend on how often someone plays.
The builder also accepts arbitrary dates. For a forecast after a match, use the
following day; match-day timestamps are not sufficiently precise for intraday use.
The reported accuracy evaluates month starts, not every possible post-match date.

## Backtesting

- Validate on monthly forecasts in 2017–2019; choose models by validation log loss.
- Test on mature monthly forecasts in 2022–2024. The 24-month horizon has follow-up
  only through the January 2024 cutoff. Never label incomplete recent windows zero.
- Compare horizons on the shared January 2022–January 2024 period, against each
  horizon's own baseline. Raw scores differ with horizon prevalence.
- Compare monthly-trained and January-only procedures on identical January test
  candidates. Report family-by-family results and independently chosen policies.
- Report log loss, Brier, average precision, ROC AUC, calibration, and within-country
  top-10 rankings; use MAE and Poisson deviance for match counts. Show unique players
  and entrants as well as repeated snapshots, and equal-player-weighted scores.

This is an exploratory temporal backtest. Data corrections were made during
project development; these years are not an untouched confirmation sample.
Repeated players and overlapping horizons are dependent. More monthly rows do not
create more independent evidence. Overseas samples remain small. No discrimination
estimates are made, and these data cannot address the 1970s or 1980s.

## Organization

```text
src/national_selection/
  data.py             Import archives, link IDs, audit coverage
  features.py         Build dated risk sets, Xs and configurable-horizon Ys
  models.py           Annual fits, dated evaluation and forecasts
  backtest.py         Matched January and common-horizon comparisons
  cli.py              Command-line entry points
  site.py             Forecast tables and rendered publication checks
  reference/          Reviewed identity links and verified appearance evidence
data/build/
  panel_6m.csv         Monthly panel with six-month labels
  panel_12m.csv        Monthly panel with twelve-month labels
  panel_24m.csv        Monthly panel with twenty-four-month labels
  ...                 Normalized inputs and linkage/coverage audits
docs/                 Design, protocol and identity decisions
out/
  report.md           Cross-horizon and cadence comparison
  monthly_12m/        Primary backtest, calibration and forecasts
  monthly_6m/         Shorter-horizon comparison
  monthly_24m/        Longer-horizon comparison
  annual_*m/         January-only benchmark at each horizon
tests/                Timing, accounting, identity and evaluation tests
```

## Run

Use Python 3.12 or newer:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
make check
make prepare evaluate forecast
```

Included normalized data make these commands independent of sibling checkouts.
`make import` rebuilds them from `../ipl_auction`, `../war` and `../side_order`.
`make all` imports, prepares, evaluates and forecasts. `make ci-docker` runs checks
in a standard Python image. GitHub CI runs tests and the complete backtest from
included inputs.

`make site` builds the Quarto website from the saved results, verifies forecast
metadata and checks the rendered links and downloadable files. The overview
includes this README, so its documentation stays synchronized. See
[publication and updates](docs/publication.md) and the
[sibling-data inventory](docs/data_sources.md).

For a single horizon or a historical forecast date:

```sh
national-selection prepare --horizons 12
national-selection evaluate --horizons 12
national-selection forecast --horizons 12 --cutoff 2024-06-01
```

The default forecast cutoff is January 1, 2026, using data through December 2025.
It has no scored future outcomes and is not a live October 2026 forecast. The
`fit_date` and `cutoff_date` are exported separately. Horizon-specific selection
metadata must exist before forecasting that horizon. Forecasts are rejected if
the policy was unavailable at the annual fit date, or if the requested cutoff
exceeds documented input coverage plus one day.

## Results and audits

- [Summary](out/report.md), [horizon comparison](out/horizon_comparison.csv),
  [matched January comparison](out/january_comparison.csv), and
  [horizon consistency](out/horizon_consistency.csv).
- [Primary report](out/monthly_12m/report.md), [metrics](out/monthly_12m/metrics.csv),
  [country metrics](out/monthly_12m/metrics_by_country.csv),
  [annual metrics](out/monthly_12m/metrics_by_year.csv),
  [calibration](out/monthly_12m/calibration.csv), and
  [dated predictions](out/monthly_12m/predictions.csv).
- [Players](data/build/players.csv), [ID crosswalk](data/build/player_crosswalk.csv),
  [primary panel](data/build/panel_12m.csv), [source manifest](data/build/manifest.json),
  [coverage](data/build/international_coverage_by_country.csv),
  [unsupported affiliations](data/build/unsupported_affiliations.csv), and
  [missing fixtures](data/build/missing_internationals.csv).
- [Monthly design](docs/monthly_design.md), [protocol](docs/protocol.md) and
  [identity decisions](docs/identity_notes.md).

The main key is Cricsheet's player UUID; names never enter prediction. Auction
nationality is a dated proxy for affiliation, not certified eligibility. Unsupported
countries and unknown identities are excluded explicitly. Independent horizon
models need not produce monotone probabilities; consistency violations are
reported, not silently repaired.

Data originate from sibling projects and their Cricsheet/auction sources. The
code's MIT license does not replace source data terms. See the manifest and
[Cricsheet licensing](https://cricsheet.org/licensing/).
