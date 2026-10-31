# National selection

Predict international cricket entry across countries using players' earlier IPL
performance. At each January cutoff, the main outcome is a recorded senior Test,
ODI or T20I appearance in the next two years among players with no known earlier
international appearance. A secondary outcome is the recorded number of matches
in that window, including zero. This pilot covers the IPL pathway; it does not
represent every country's domestic player pool.

## X and Y

One row is a **player × annual cutoff**, identified by Cricsheet's player UUID.

| Component | Definition |
| --- | --- |
| Main Y: `selected` | At least one recorded senior international appearance during the next two calendar years, for any national side. Actual participation, rather than squad nomination. |
| Secondary Y: `n_matches` | Recorded international appearances in the same window. Measures opportunity and persistence, not performance quality. |
| Performance Xs | Matches, runs, balls faced, dismissals, wickets, legal balls bowled, runs conceded, batting average, strike rate, bowling average and economy. Each is computed for the observed IPL career and the previous two years. |
| Additional performance Xs | Days since the last IPL match and days since the first observed IPL match. |
| Country X | Auction nationality documented before the cutoff, used as a proxy for country affiliation in the country-only and combined models. |
| Excluded from X | Names, player IDs, future performance, region and caste. Age, role, first-class statistics and WAR are not yet included. |

For example, the January 2022 snapshot uses completed matches through December
2021 and predicts appearances from January 2022 through December 2023. Every
training label must have finished before the forecast date.

Country-only, performance-only and combined classifiers distinguish performance's
predictive contribution from country differences. Results are reported pooled
and by country. Countries with no prior international appearance coverage are
excluded rather than assigned false-negative outcomes. Known prior appearances
from independent sources also exclude players when the archive missed their cap.

## Organization

```text
src/national_selection/
  data.py             Import archives, link IDs, audit coverage
  features.py         Build dated risk sets, Xs and Ys
  models.py           Fit, evaluate and forecast
  cli.py              Command-line entry points
  reference/          Reviewed identity links and prior-cap evidence
data/build/          Normalized inputs, panel and linkage/coverage audits
docs/                Research protocol and identity decisions
out/                 Metrics, predictions and results report
tests/               Leakage, accounting, identity and evaluation tests
```

The main key is **Cricsheet's player UUID**, shared by IPL and international match
records. An exported crosswalk links these IDs to the sibling auction registry.
Unknown identities remain unresolved.

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
`make import` rebuilds inputs from `../ipl_auction`, `../war`, and `../side_order`.
For another workspace, run `national-selection import --workspace /path/to/workspace`.
`make all` imports, prepares, evaluates and forecasts. `make ci-docker` runs checks
in the standard `python:3.12-slim` image when Docker is available. GitHub CI also
rebuilds the panel, evaluates models and forecasts from included inputs.

## Outputs

- [Results](out/report.md), [pooled metrics](out/metrics.csv),
  [country metrics](out/metrics_by_country.csv),
  [equal-country averages](out/metrics_country_macro.csv),
  [annual metrics](out/metrics_by_year.csv), [calibration](out/calibration.csv),
  and [held-out predictions](out/predictions.csv).
- [January 2026 forecasts for 2026–2027](out/forecast.csv): an unscored snapshot
  using data through December 2025, not a live October 2026 forecast.
- [Players](data/build/players.csv), [ID crosswalk](data/build/player_crosswalk.csv),
  [risk panel](data/build/panel.csv), [country risk sets](data/build/risk_set_by_country.csv),
  and [source hashes](data/build/manifest.json).
- [International coverage](data/build/international_coverage_by_country.csv),
  [unsupported affiliations](data/build/unsupported_affiliations.csv),
  [missing fixtures](data/build/missing_internationals.csv),
  and [inconsistent appearances](data/build/inconsistent_appearances.csv).
- [Protocol](docs/protocol.md) and [identity decisions](docs/identity_notes.md).

Settings are fixed; the classifier is selected by 2017–2019 validation log loss.
The 2022–2024 snapshots are evaluated against their following two calendar years.
This remains an exploratory backtest: identity corrections and coverage checks
were made while inspecting results. Outcomes are recorded first entry and recorded
counts, not a certified census of debuts or career totals. Overseas uncapped IPL
samples are small. Missing earlier caps can still contaminate risk sets, and
missing subsequent matches can suppress labels. No discrimination estimates are
made, and these data cannot address selection in the 1970s or 1980s.

Data originate from sibling projects and their Cricsheet/auction sources. The
code's MIT license does not replace source data terms. See the manifest and
[Cricsheet licensing](https://cricsheet.org/licensing/).
