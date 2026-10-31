# Identity and prior-cap decisions

The reference CSV takes precedence over exact names and transitive sibling aliases.
A link to a name absent from the IPL archive deliberately remains unresolved.
These links correct identity metadata; they do not provide performance features.

- Ravi Bishnoi and Rajesh Bishnoi (`R Bishnoi`) have different UUIDs; likewise
  Navdeep Saini and Nitin Saini (`N Saini`). Preserve their distinct direct names.
- Fabian Allen maps to `FA Allen`. Finn Allen must not inherit Fabian's UUID;
  his reference points to `Finn Allen`, which has no appearance in this IPL input.
- Aryaman Birla must not map to `UA Birla` (Udit Alok Birla). The
  [MPCA archive](https://www.mpcaonline.com/assets/uploads/archives_files/mens_1565773984.pdf)
  lists Udit and Aryaman separately. Aryaman remains unresolved here; Udit maps to
  `UA Birla`.
- Ansh Patel must not inherit Axar Patel's `AR Patel` UUID. The
  [official Ansh profile](https://www.iplt20.com/teams/punjab-kings/squad-details/20608/2022/4)
  and [2022 auction list](https://documents.iplt20.com/documents/IPL/document/2022/02/IPL2022PlayerAuction_List_Sets.pdf)
  identify Ansh separately. His absent scorecard identity remains unresolved.
- Kuldip Yadav maps to `K Yadav`, UUID `030f3089`, rather than Kuldeep Yadav's
  `8d2c70ad`. Rajasthan Royals' [2021 recap](https://www.rajasthanroyals.com/latest-news/ipl-2021-recap)
  identifies their debuting pacer; this agrees with the imported Rajasthan
  scorecards beginning October 2021.

Other full-name/scorecard links are manually curated interpretations and still
warrant independent checking. The many-names-per-UUID review is not a complete
external identity certification.

The imported match `1229824` lists `J Butler`, UUID `efcb778e`, for both Guernsey
and Isle of Man. The whole fixture is quarantined; neither side counts as fully
covered. The conflicting rows are in `inconsistent_appearances.csv`.

Independent evidence also prevents two known capped players entering later risk
sets merely because their earlier appearances are missing from Cricsheet:

- Alfonso Thomas played South Africa–Pakistan on February 2, 2007:
  [match lineup](https://www.cricbuzz.com/cricket-match-squads/3897/rsa-vs-pak-only-t20i-pakistan-in-south-africa-t20i-match-2007).
- Matheesha Pathirana debuted against Afghanistan on August 27, 2022:
  [ICC player profile](https://www.icc-cricket.com/rankings/73830/matheesha-pathirana).

The source URLs, UUIDs, event dates and review dates are in `prior_appearances.csv`.
This is exclusion evidence, not an exhaustive debut register; recorded outcome
counts are still computed from imported complete match lineups.
