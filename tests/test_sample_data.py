"""Tests against the committed sample outputs (data/processed/candidate_longlist.csv
and ribble_nfm.duckdb) - these ARE checked into git (unlike the raw/staging
data) specifically so CI and new clones have something real to test against.
"""
from pathlib import Path

import duckdb
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "processed" / "candidate_longlist.csv"
DB_PATH = ROOT / "data" / "processed" / "ribble_nfm.duckdb"

FINAL_FIVE = {"C16", "C21", "C14", "C22", "C23"}

pytestmark = pytest.mark.skipif(
    not (CSV_PATH.exists() and DB_PATH.exists()),
    reason="Sample data not present - run scripts/score_candidates.py and build_query_database.py first",
)


def test_candidate_csv_has_expected_columns():
    df = pd.read_csv(CSV_PATH)
    for col in ["candidate_id", "rank", "band", "data_confidence", "data_confidence_note",
                "site_type", "area_ha", "composite_score", "protected_site_flag"]:
        assert col in df.columns, f"missing column {col}"


def test_candidate_csv_has_35_unique_candidates():
    df = pd.read_csv(CSV_PATH)
    assert len(df) == 35
    assert df["candidate_id"].nunique() == 35


def test_candidate_csv_band_values_are_valid():
    df = pd.read_csv(CSV_PATH)
    assert set(df["band"].unique()) <= {"Strong", "Moderate", "Watch", "Weak"}


def test_candidate_csv_confidence_values_are_valid():
    df = pd.read_csv(CSV_PATH)
    assert set(df["data_confidence"].unique()) <= {"High", "Low"}


def test_investigation_zone_threshold_applied_consistently():
    df = pd.read_csv(CSV_PATH)
    zones = df[df["site_type"] == "Investigation Zone"]
    sites = df[df["site_type"] == "Candidate Site"]
    assert (zones["area_ha"] >= 1000).all()
    assert (sites["area_ha"] < 1000).all()


def test_duckdb_candidate_summary_matches_csv_row_count():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    n = con.execute("SELECT COUNT(*) FROM candidate_summary").fetchone()[0]
    con.close()
    assert n == 35


def test_duckdb_final_five_view_has_exactly_five_rows():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    ids = set(r[0] for r in con.execute("SELECT candidate_id FROM final_five").fetchall())
    con.close()
    assert ids == FINAL_FIVE


def test_duckdb_example_query_from_brief_runs():
    """The exact query given when this database was requested - if the schema
    ever drifts (a rename, a dropped column) this is the first thing that
    should fail."""
    con = duckdb.connect(str(DB_PATH), read_only=True)
    result = con.execute("""
        SELECT candidate_id, nearest_place, composite_score
        FROM candidate_summary
        WHERE band = 'Strong'
          AND data_confidence = 'High'
          AND overlap_built_up_pct < 10
        ORDER BY composite_score DESC
    """).fetchall()
    con.close()
    assert len(result) > 0


def test_duckdb_views_exist():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    tables = set(r[0] for r in con.execute("SHOW TABLES").fetchall())
    con.close()
    for expected in ["candidate_summary", "restoration_projects", "recorded_flood_events",
                      "provenance", "strong_candidates", "high_confidence_candidates",
                      "opportunity_gaps", "flagged_constraints", "final_five"]:
        assert expected in tables


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
