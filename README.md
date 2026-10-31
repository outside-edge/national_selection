# National selection

Predict whether a previously uncapped Indian IPL player makes a recorded senior
international appearance in the next two years, and how many international
matches he plays during that window. The initial pilot uses existing sibling
archives. It covers the IPL pathway, not the entire domestic first-class pool.

The main key is **Cricsheet's player UUID**, shared by IPL and international match
records. Names never enter the prediction model. An exported crosswalk links
these IDs to the sibling auction registry and records unresolved identities.

## Run

Use Python 3.12 or newer:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
make check
make prepare evaluate forecast
```

The included normalized data make these commands independent of sibling checkouts.
To rebuild the normalized inputs from this workspace, run `make import`; it reads
`../ipl_auction`, `../war`, and `../side_order`. For another location:

```sh
national-selection import --workspace /path/to/outside-edge
```

`make all` imports, prepares, evaluates and forecasts. `make ci-docker` runs checks
in the standard `python:3.12-slim` image when Docker is available. The CI workflow
also rebuilds the panel, evaluates models and creates forecasts from included data.

## Outputs

- [Results report](out/report.md), [metrics](out/metrics.csv), [year-specific metrics](out/metrics_by_year.csv),
  [calibration](out/calibration.csv), and [held-out predictions](out/predictions.csv).
- [January 2026 forecasts for 2026–2027](out/forecast.csv): an unscored snapshot
  based on data through December 2025, not a live October 2026 forecast.
- [Players](data/build/players.csv), [auction ID crosswalk](data/build/player_crosswalk.csv),
  [risk panel](data/build/panel.csv), and [source manifest](data/build/manifest.json).
- [Protocol and interpretation](docs/protocol.md), including limitations of the
  outcome archive and the distinction between opportunity and performance.

The baseline comparison includes historical selection frequency, regularized
logistic regression, small boosted trees, a constant match-count forecast,
a zero-count forecast, and Poisson regression. Model settings are fixed; the
classifier is selected by 2017–2019 validation log loss. The 2022–2024 forecast
snapshots are evaluated against their following two calendar years. Training
uses only labels whose full two-year window ended before each forecast date.

This is an exploratory backtest. Identity corrections were made while developing
and inspecting results, so the later years are temporally held out for fitting
but are not a pristine, untouched confirmation sample. Some international matches
are absent from the archive: outcomes mean **recorded first entry and recorded
match counts**, not a certified census of debuts or career totals. Source and
identity gaps are exported rather than filled with invented records.

Data originate from sibling projects and their Cricsheet/auction sources. The
code's MIT license does not replace the source data's terms. See the source
receipts and [Cricsheet licensing](https://cricsheet.org/licensing/).
