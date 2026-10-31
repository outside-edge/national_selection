# Publication and updates

The Quarto website uses the same publication pattern as `player_value` and
`side_order`. Documentation and saved results are built on pushes to `main` and
published only after local-equivalent tests and rendering checks pass. Pull
requests build and check the site without deploying it. A manual workflow trigger
can rebuild a publication.

The **Monthly forecast refresh** action runs on the **2nd of each month at
08:23 UTC**, and can also be started manually from GitHub Actions. It fetches
current sources, runs tests, issues new dated 6-, 12- and 24-month forecasts,
validates the website, commits the results, and passes that exact commit to the
website workflow. Schedules may be delayed by GitHub.

## Reproduce the website

Install the package's development dependencies and [Quarto](https://quarto.org/docs/get-started/), then run:

```sh
make check
make site
```

CI uses Quarto 1.10.20. Set `QUARTO=/path/to/quarto` to use another installed
executable. `make site` reads the included data, validates forecast dates and
model-selection metadata, generates tables, renders the site and checks local
links and download checksums. It does not fetch new data or refit models.

The overview includes `README.md`; backtest pages render the saved analysis
reports. Forecast tables join saved predictions to features reconstructed at
exactly the saved cutoff, using one-to-one player IDs. Publication metadata in
`out/publication.json` records input hashes and the forecast horizon and dates.
Generated include files and rendered HTML are ignored by Git.

## Data cadence versus documentation cadence

`make refresh` fetches the official IPL, Test, ODI and T20I Cricsheet archives,
the `side_order` calendar, and `ipl_auction` identity aliases. Archive extraction
uses the validated numeric-file pattern in `player_value`'s downloader. Upstream
Git commits, downloaded-file hashes, archive hashes and retrieval times are saved.
The auction-affiliation reference is a versioned snapshot of the local sibling
data; that source file is not available in its GitHub checkout. It is not guessed
or silently replaced during refreshes.

The observation endpoint is the validated `side_order` calendar's cutoff, which
must be a completed day within the last ten days. The forecast starts the next
day. Thus a scheduled run can publish a forecast dated a few days earlier than
the run. The workflow stops if a source fails, is stale, or loses previously
recorded matches. Failed runs do not publish a new site.

New inputs live in `data/current/`, predictions in `out/current/`, and dated
snapshots in `out/history/`. The [forecast history](../forecast_history.qmd)
includes downloads and source receipts. The original `data/build/` and `out/`
backtests remain the frozen benchmark. The validation-selected model family stays
fixed; parameters use only training labels that matured before January of the
forecast year. Refreshing observations does not change the prior model-selection
decision or turn the current forecasts into a new backtest.

The evaluated forecast grid is monthly. Newly issued forecasts use the available
calendar cutoff, so their exact dates need not be month starts. The site separates
these unscored forecasts from the frozen backtest. Rebuilding docs alone, via
`make site`, does not fetch or advance data.

The acquisition command uses `curl` and GitHub CLI (`gh`), both available on the
GitHub-hosted runner. A verified downloaded source bundle can be reused locally
with `python -m national_selection.refresh --workspace /path/to/sources`.
