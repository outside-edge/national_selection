# Data and sibling repositories

The forecasting pipeline uses three sibling repositories. Their newer files
and acquisition code can support updates; a new collection system is not needed
for every input. This inventory was checked against local records on October 30,
2026. Dates below describe the inspected files, not a promise of complete coverage.

| Source | Verified local contents | Reuse |
| --- | --- | --- |
| [player_value](https://github.com/outside-edge/player_value), local directory `war` | Men's raw Cricsheet: 897 Tests through October 22, 2026; 2,607 ODIs and 3,646 T20Is through October 25. Player UUIDs and match lineups are present. | International appearance history and stable IDs. Its `fetch` command downloads each format with checksums and retrieval receipts. |
| [side_order](https://github.com/outside-edge/side_order) | 11,905 international match results, 1877–October 25, 2026, with match IDs, teams, start and completion dates. | Match calendar and independent coverage checks. Its weekly workflow provides the update/publication pattern. Results alone cannot identify which players appeared. |
| [ipl_auction](https://github.com/outside-edge/ipl_auction) | 1,188 raw IPL matches, 789 players, April 2008–April 12, 2026; 19 matches after 2025. Auction records cover seasons 2008–2026 and include nationality and speciality. | IPL performance, affiliation evidence and reviewed name aliases. Raw IPL data are newer than its cached season statistics and WAR, which end in 2023. |
| [python-espncricinfo](https://github.com/outside-edge/python-espncricinfo) | Player client exposes date of birth, role, batting/bowling styles and ESPN player IDs; match client exposes scorecards. | Enrich player profiles and investigate missing scorecards. This is acquisition code, not an already collected, complete domestic player panel. |
| `get_cricket_data`, `toss_up`, `test_selection` | Historical match summaries and a documented source-feasibility audit. The older scraper uses Python 2. | Historical fixture discovery and design evidence. The inspected summary tables lack the domestic player-performance denominator. |

## What the current forecast actually consumes

`national_selection.data.import_local` reads raw IPL matches from `ipl_auction`,
raw international matches from `war`, and the match calendar from `side_order`.
It records source-file hashes and exports linkage and coverage audits. The
benchmark import defaults to **December 31, 2025**. The monthly refresh
passes a newer endpoint from the validated calendar and writes separate current
inputs, leaving the benchmark unchanged.

The international archives were retrieved on October 27, 2026. Their local 2026
records add 21 men's Tests, 100 ODIs and 535 T20Is beyond the frozen analysis
period. The IPL cache is only part of the 2026 season. Advancing the forecast to
October using that cache would omit later IPL performances.

[Cricsheet's official downloads](https://cricsheet.org/downloads/) include an IPL
JSON archive using the same player UUID convention. The downloader in
`player_value` accepts Test, ODI and T20I. The monthly refresh uses that same
archive-validation pattern for all three formats and IPL. Its raw and prepared
international tables are ignored locally rather than tracked in Git, so a fresh
GitHub checkout must run acquisition or receive a versioned data artifact.

## Reuse contract for monthly updates

1. Refresh international archives with the existing `player_value` downloader.
   Use all available participant history for prior-cap exclusions, rather than
   only the recent window prepared for player-strength estimation.
2. Consume `side_order`'s dated calendar and compare match IDs by country and
   format. A missing fixture remains visible; a completed calendar window does
   not make incomplete player records complete.
3. Refresh the IPL archive, then use this repo's player-match accounting. Keep
   Cricsheet UUIDs as the player key. Auction `P0001`-style IDs are assigned from
   a sorted name list and should not be treated as durable cross-refresh IDs.
4. Preserve the frozen backtest inputs and reports. Store each new forecast with
   its own cutoff, input hashes, model policy and annual fit date. Score only
   horizons with completed follow-up, retaining coverage qualifications.
5. Publish validated output tables, then render documentation from those tables.

Country and role evidence need observation dates. The current conservative rule
makes a season's nationality available in January of the following year. An
updated pipeline must not silently backdate 2026 auction evidence. Age should be
computed from birth date at each cutoff, not copied from a current profile's age.
Current player-value ratings and full-season WAR are not automatically valid
historical Xs: their training and performance windows must end before each cutoff.

## Included data and audits

- [Source manifest](../data/build/manifest.json)
- [Player IDs](../data/build/players.csv) and [auction crosswalk](../data/build/player_crosswalk.csv)
- [Coverage by country, format and year](../data/build/international_coverage_by_country.csv)
- [Missing international fixtures](../data/build/missing_internationals.csv)
- [Unsupported affiliations](../data/build/unsupported_affiliations.csv)
- [Identity decisions](identity_notes.md)

The site publishes current snapshots when available and retains the frozen
benchmark. The [monthly workflow](publication.md) records its actual source
versions and coverage dates. The table above documents the sibling-file inventory
before the refresh, not the date of the current forecast.

## Affiliation reference used by automation

The local `ipl_auction/data/acquisitions/sources/clod/ipl_2008_2026.csv` is not
tracked at the upstream Git commit inspected for automation. The three fields
`year`, `player`, and `nationality` are therefore preserved in this package's
`reference/auction_affiliations.csv`: 3,385 source rows, without inferred values.
The importer retains its conservative January-after-season availability rule.
Match feeds update monthly; this affiliation reference needs an explicit update
when new source evidence is collected. Unlinked players remain in the audit.
