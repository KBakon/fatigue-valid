# Public release inventory

`RELEASE_MANIFEST.csv` enumerates payload files; `SHA256SUMS.txt` verifies the payload plus the release manifest. Each excludes itself to avoid a hash cycle.

- `analysis_code/`: project-authored WP-02/WP-03 and WP-04/WP-05/WP-06 scripts and a release checker; privacy/portability adaptations are documented in `reproduction/REPRODUCIBILITY.md`. The WP-02 preparation derivative traces to the earlier project-authored MIT release and removes only hard-coded individual exclusions into a controlled local file.
- `aggregate_results/`: selected aggregate WP-04/05/06 results and method specifications. HIGH-DOWN retains all 40 author-approved rows unchanged. For privacy, original single-transition extrema, index-specific small-cell regime counts and LOW/MIDDLE/UP-reference subgroup rows are excluded; the included core claims and approved tables are retained.
- `figures/` and `tables/`: approved figures, main tables and aggregate S1–S4 CSVs. Only provenance path columns were removed from the supplementary CSVs; scientific fields are unchanged.
- `supplementary/`: publication-facing PDF and editable LaTeX with the four table sources. The approved v1.3 source and PDF retain the CC BY notice and all 40 HIGH-DOWN summaries; the internal adjudication sentence was removed and Table S4 type enlarged.
- `LICENSES/`, `reproduction/`, README, citation, source references and provenance documentation complete the package.

Excluded: original participant-level source CSVs and RAR, raw sensor data, individual trajectories and outcomes, participant identifiers, private path/eligibility manifests, third-party source code, internal disclosure/authorization records, and the unfinished manuscript and its PDF. Licenses do not apply to linked third-party material.
