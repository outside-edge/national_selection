# Why some countries have no forecasts

The model accepts multiple country affiliations, but the current performance data
cover **IPL participants**, not all domestic cricketers in each country. The
target is a **first senior international appearance**, not a return to a national
team. Most overseas players reach the IPL after their international debut.

At the January 1, 2026 cutoff, all 19 Australian players with an IPL appearance in
the preceding 24 months had a known earlier international appearance. They are
therefore excluded. Examples include Travis Head, Cameron Green, Xavier Bartlett
and Jake Fraser-McGurk. Prior appearances for any country count: Tim David's
earlier Singapore appearances also exclude him from a first-international model.

Australia is not banned by a country filter. Earlier Australian candidates do
appear in the historical panel: the 12-month panel has 10 distinct Australian
players and 119 monthly snapshots. That is still too small and selective to
validate an Australian domestic-entry model. The 2022–2024 test set has no
Australian candidates.

The October 26, 2026 refresh has 15 active players identified as Australian; all
15 have known earlier international appearances. It has 51 candidates, all
identified as Indian. Another 56 active IPL players have unresolved affiliation
at that cutoff and are excluded separately. This includes limitations of name
linkage and the conservative nationality-availability rule; these players must
not be silently assigned to a country.

The [forecast page](../forecasts.qmd) shows every observed affiliation,
including countries with zero candidates, with downloadable player-level
exclusions. The table is generated from inputs at each saved forecast cutoff and
checked against the actual forecast population. Unknown or conflicting
affiliations remain visible rather than being guessed from names.

Afghanistan is a different case: the international archive lacks country coverage.
Its candidates are excluded as unsupported, rather than treating missing
international records as proof they have never played.

## What broader country forecasts require

For Australia, add dated Big Bash and preferably Sheffield Shield and domestic
one-day performances. Analogous domestic competitions are needed for the other
countries. Keep stable player IDs, country-affiliation evidence and match format;
an overseas player's franchise location is not their national affiliation.

The first model can be a comparable domestic-T20 pathway across countries, with
format-specific performance features and country-level backtests. Forecasting
Test entry from first-class careers needs the corresponding domestic histories.
Simply retaining already-capped overseas IPL players would change the question to
future international participation, which should be a separate model.
