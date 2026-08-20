# Query Database — DuckDB

`data/processed/ribble_nfm.duckdb`, built by `scripts/build_query_database.py`.

The GeoPackage (`data/processed/ribble_nfm_staging.gpkg`,
`candidate_longlist.gpkg`) remains the spatially queryable source — it has
the actual geometry, and DuckDB's spatial extension can query it directly
(see the earlier SQL walkthrough in this project). This database is the
**tabular** companion: no geometry, plain columns, fast to filter/aggregate/
join with ordinary SQL, ideal for the kind of question that doesn't need a
map to answer.

## Tables

| Table | Rows | What it is |
|---|---|---|
| `candidate_summary` | 35 | One row per candidate — the clean, analysis-ready table (see below) |
| `restoration_projects` | 85 | Attribute data from `priority_habitat_creation_restoration` (geometry dropped) - recorded EA restoration/creation projects |
| `recorded_flood_events` | 282 | Attribute data from `recorded_flood_outlines` (geometry dropped) - historic flood records from 1946 onwards |
| `provenance` | 13 | The full `docs/provenance_manifest.csv` as a table - source, licence, date, and known gaps for every dataset used in this project |

### `candidate_summary` columns

| Column | Meaning |
|---|---|
| `candidate_id` | e.g. `C16` |
| `nearest_place`, `nearest_place_dist_km` | Nearest OS Open Built Up Area, and its distance |
| `rank`, `band` | From the Week 3 composite score |
| `data_confidence`, `data_confidence_note` | **Scoped specifically to RoFRS flood-risk context coverage - nothing else.** `High`/`Low` (kept as clean two-value strings, and named to match the brief's example query verbatim); `data_confidence_note` spells out what it does and doesn't mean. It does **not** indicate anything about the reliability of the composite score - RoFRS isn't a scored factor, and every layer that *is* scored has full, reliable coverage everywhere. It flags that the contextual RoFRS figure shown alongside a candidate (`flood_risk_overlap_pct`) is missing for the 2 candidates in the acquisition gap - see `docs/screening_methodology.md`. |
| `site_type` | `Candidate Site` or `Investigation Zone` (≥1,000ha) |
| `area_ha`, `composite_score`, `top10_stability` | Size and score detail |
| `community_proximity_km`, `n_built_up_within_5km` | Nearby-community-exposure inputs |
| `flood_risk_overlap_pct` | RoFRS overlap - **contextual only, not scored** (see `docs/screening_methodology.md`) |
| `historic_flood_overlap_pct` | Recorded Flood Outlines overlap - **is** scored, into exposure |
| `habitat_network_overlap_pct`, `dist_phi_km` | Habitat opportunity inputs |
| `recorded_activity_dist_km` | Distance to nearest recorded restoration project |
| `overlap_built_up_pct`, `road_density_km_per_km2`, `protected_site_overlap_pct`, `protected_site_flag` | Constraint inputs - `protected_site_flag` names the actual SSSI/SAC/Monument when one overlaps |
| `suggested_next_investigation` | Rule-based next step, e.g. "confirm consent with Natural England" when a protected site is flagged |

## Views

| View | Definition |
|---|---|
| `strong_candidates` | `band = 'Strong'` |
| `high_confidence_candidates` | `data_confidence = 'High'` |
| `opportunity_gaps` | `recorded_activity_dist_km >= 2.0` - no recorded restoration activity nearby |
| `flagged_constraints` | Protected-site overlap OR settlement overlap > 5% |
| `final_five` | The five site-card candidates: C16, C21, C14, C22, C23 |

## Example queries

The brief's own filter - strong, reliable, and clean of settlement overlap:

```sql
SELECT candidate_id, nearest_place, composite_score
FROM candidate_summary
WHERE band = 'Strong'
  AND data_confidence = 'High'
  AND overlap_built_up_pct < 10
ORDER BY composite_score DESC;
```

Candidates that look good on paper but carry a real flag underneath (this is
the query that reconstructs why C17 was dropped in the Week 3 correction):

```sql
SELECT candidate_id, rank, top10_stability, protected_site_flag, overlap_built_up_pct
FROM candidate_summary
WHERE top10_stability >= 3
  AND (
      (protected_site_flag IS NOT NULL AND protected_site_flag != 'None')
      OR overlap_built_up_pct > 8
  )
ORDER BY rank;
```

How much of the modelled area is unusable as a single site:

```sql
SELECT site_type, COUNT(*) AS n, SUM(area_ha) AS total_area_ha
FROM candidate_summary
GROUP BY site_type;
```

Cross-reference against the provenance table - which datasets actually feed
the constraint columns:

```sql
SELECT dataset, source_organisation, notes
FROM provenance
WHERE dataset ILIKE '%SSSI%' OR dataset ILIKE '%SAC%' OR dataset ILIKE '%Monument%';
```

Five more worked examples, each with an explanation of what the result
actually means, are in
[notebooks/explore_candidates.ipynb](../notebooks/explore_candidates.ipynb).

## From the command line

```bash
duckdb data/processed/ribble_nfm.duckdb -c "SELECT * FROM final_five;"
```

## Rebuilding

```bash
python3 scripts/build_query_database.py
```

Reads `data/processed/candidate_longlist.gpkg` and
`data/processed/ribble_nfm_staging.gpkg` - rerun `score_candidates.py` first
if the underlying scoring has changed.
