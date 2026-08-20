"""Week 6 addendum: a queryable analytical database.

The GeoPackage (data/processed/ribble_nfm_staging.gpkg, candidate_longlist.gpkg)
remains the spatially queryable source. This script builds a lightweight,
DuckDB-based *tabular* companion for easy SQL analysis:
data/processed/ribble_nfm.duckdb

Contains:
- candidate_summary: one clean row per candidate, plain-English columns
- restoration_projects, recorded_flood_events: non-spatial reference tables
  (attribute data from the staging GeoPackage, geometry dropped)
- provenance: the dataset provenance manifest, so source/licence context is
  queryable alongside the results
- Views: strong_candidates, high_confidence_candidates, opportunity_gaps,
  flagged_constraints, final_five

Rebuild with:
    python3 scripts/build_query_database.py
"""
import csv
from pathlib import Path

import duckdb
import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
STAGING_GPKG = ROOT / "data" / "processed" / "ribble_nfm_staging.gpkg"
LONGLIST_GPKG = ROOT / "data" / "processed" / "candidate_longlist.gpkg"
PROVENANCE_CSV = ROOT / "docs" / "provenance_manifest.csv"
OUT_DB = ROOT / "data" / "processed" / "ribble_nfm.duckdb"

FINAL_FIVE = ["C16", "C21", "C14", "C22", "C23"]
OPPORTUNITY_GAP_KM = 2.0  # "genuine gap": no recorded restoration activity within this distance


def nearest_place(sites, built_up):
    """For every candidate, the name and distance (km) of the nearest settlement."""
    names, dists = [], []
    for g in sites.geometry:
        d = built_up.geometry.distance(g)
        idx = d.idxmin()
        names.append(built_up.loc[idx, "name1_text"])
        dists.append(d.min() / 1000)
    return pd.Series(names, index=sites.index), pd.Series(dists, index=sites.index)


def suggested_next_investigation(row):
    if row["protected_site_flag"] not in (None, "None", "") and pd.notna(row["protected_site_flag"]):
        return f"Confirm consent requirements with Natural England / Historic England before proceeding ({row['protected_site_flag']})"
    if row["data_confidence"] != "High":
        return "Confirm flood-risk context locally - this candidate falls in the RoFRS acquisition gap"
    if row["site_type"] == "Investigation Zone":
        return "Identify specific sub-sites within this zone via local walkover before treating it as one site"
    if row["overlap_built_up_pct"] > 10:
        return "Check settlement-overlap extent on the ground - may reduce the deliverable area"
    return "Local practitioner walkover to confirm land use, ownership and access; check for unrecorded delivery"


def build_candidate_summary():
    sites = gpd.read_file(LONGLIST_GPKG)
    built_up = gpd.read_file(STAGING_GPKG, layer="os_open_built_up_areas")

    sites["nearest_place"], sites["nearest_place_dist_km"] = nearest_place(sites, built_up)
    sites["suggested_next_investigation"] = sites.apply(suggested_next_investigation, axis=1)

    # Column names deliberately keep `data_confidence` and `overlap_built_up_pct`
    # as-is (not renamed) since those are the names used in the brief's example
    # query - everything else gets a clearer name.
    df = sites.drop(columns="geometry").rename(columns={
        "dist_built_up_km": "community_proximity_km",
        "overlap_rofrs_pct": "flood_risk_overlap_pct",
        "overlap_recorded_flood_pct": "historic_flood_overlap_pct",
        "overlap_habitat_networks_pct": "habitat_network_overlap_pct",
        "dist_recorded_restoration_km": "recorded_activity_dist_km",
        "overlap_protected_pct": "protected_site_overlap_pct",
    })

    cols = [
        "candidate_id", "nearest_place", "nearest_place_dist_km",
        "rank", "band", "data_confidence", "data_confidence_note", "site_type",
        "area_ha", "composite_score", "top10_stability",
        "community_proximity_km", "n_built_up_within_5km",
        "flood_risk_overlap_pct", "historic_flood_overlap_pct",
        "habitat_network_overlap_pct", "dist_phi_km",
        "recorded_activity_dist_km",
        "overlap_built_up_pct", "road_density_km_per_km2",
        "protected_site_overlap_pct", "protected_site_flag",
        "suggested_next_investigation",
    ]
    return df[cols].sort_values("rank").reset_index(drop=True)


def build_reference_tables():
    restoration = gpd.read_file(STAGING_GPKG, layer="priority_habitat_creation_restoration").drop(columns="geometry")
    flood_events = gpd.read_file(STAGING_GPKG, layer="recorded_flood_outlines").drop(columns="geometry")
    return restoration, flood_events


def load_provenance():
    with open(PROVENANCE_CSV) as f:
        return pd.DataFrame(list(csv.DictReader(f)))


VIEWS = {
    "strong_candidates": "SELECT * FROM candidate_summary WHERE band = 'Strong' ORDER BY rank",
    "high_confidence_candidates": "SELECT * FROM candidate_summary WHERE data_confidence = 'High' ORDER BY rank",
    "opportunity_gaps": f"SELECT * FROM candidate_summary WHERE recorded_activity_dist_km >= {OPPORTUNITY_GAP_KM} ORDER BY rank",
    "flagged_constraints": (
        "SELECT * FROM candidate_summary "
        "WHERE (protected_site_flag IS NOT NULL AND protected_site_flag != 'None') "
        "   OR overlap_built_up_pct > 5 "
        "ORDER BY rank"
    ),
    "final_five": "SELECT * FROM candidate_summary WHERE candidate_id IN ({}) ORDER BY rank".format(
        ", ".join(f"'{c}'" for c in FINAL_FIVE)
    ),
}


def main():
    print("== Building candidate_summary ==")
    candidate_summary = build_candidate_summary()
    print(f"{len(candidate_summary)} candidates")

    print("== Building reference tables ==")
    restoration_projects, recorded_flood_events = build_reference_tables()
    provenance = load_provenance()

    OUT_DB.parent.mkdir(parents=True, exist_ok=True)
    if OUT_DB.exists():
        OUT_DB.unlink()

    con = duckdb.connect(str(OUT_DB))
    con.execute("CREATE TABLE candidate_summary AS SELECT * FROM candidate_summary")
    con.execute("CREATE TABLE restoration_projects AS SELECT * FROM restoration_projects")
    con.execute("CREATE TABLE recorded_flood_events AS SELECT * FROM recorded_flood_events")
    con.execute("CREATE TABLE provenance AS SELECT * FROM provenance")

    print("== Creating views ==")
    for name, sql in VIEWS.items():
        con.execute(f"CREATE OR REPLACE VIEW {name} AS {sql}")
        n = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"{name}: {n} rows")

    con.close()
    print(f"\nWritten: {OUT_DB}")


if __name__ == "__main__":
    main()
