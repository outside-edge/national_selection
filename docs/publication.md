# Publication and updates

The Quarto website uses the same publication pattern as `player_value` and
`side_order`. Documentation and saved results are built on pushes to `main` and
published only after local-equivalent tests and rendering checks pass. Pull
requests build and check the site without deploying it. A manual workflow trigger
can rebuild a publication.

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

Rebuilding a website does not refresh its observations. This publication remains
the January 2026 forecast based on data through December 2025. Model parameters
refit annually and the evaluated forecast grid is monthly. Weekly data ingestion
and a weekly forecast grid would be separately versioned changes.

The [sibling-data inventory](data_sources.md) identifies the existing acquisition
components to reuse. Weekly data updates are not enabled in this initial docs
deployment. Until that integration is complete, the site retains its original
data and forecast dates rather than presenting a new build as a fresh prediction.
