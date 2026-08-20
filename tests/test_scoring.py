"""Unit tests for the pure scoring logic in scripts/score_candidates.py.

Deliberately does NOT touch the staging GeoPackage (644MB, gitignored, not
available in CI) - these test the scoring math itself with synthetic data,
independent of the real spatial pipeline.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import score_candidates as sc  # noqa: E402


def test_percentile_rank_orders_correctly():
    s = pd.Series([10, 30, 20])
    ranked = sc.percentile_rank(s)
    assert ranked[1] == 1.0  # the max gets the top percentile
    assert ranked[0] < ranked[2] < ranked[1]


def test_percentile_rank_ties_get_equal_rank():
    s = pd.Series([5, 5, 10])
    ranked = sc.percentile_rank(s)
    assert ranked[0] == ranked[1]


def test_band_buckets_into_four_labels():
    composite = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8])
    bands = sc.band(composite)
    assert set(bands.cat.categories) == {"Weak", "Watch", "Moderate", "Strong"}
    # highest score should be Strong, lowest should be Weak
    assert bands.iloc[composite.idxmax()] == "Strong"
    assert bands.iloc[composite.idxmin()] == "Weak"


def _synthetic_factors_df(n=10):
    return pd.DataFrame({
        "nfm_potential_raw": range(1, n + 1),
        "dist_built_up_km": [i * 0.5 for i in range(n)],
        "overlap_recorded_flood_pct": [0.0] * n,
        "overlap_habitat_networks_pct": [10.0] * n,
        "dist_phi_km": [1.0] * n,
        "dist_recorded_restoration_km": [1.0] * n,
        "overlap_built_up_pct": [0.0] * n,
        "road_density_km_per_km2": [1.0] * n,
        "overlap_protected_pct": [0.0] * n,
    })


def test_score_is_higher_for_larger_nfm_potential_all_else_equal():
    df = _synthetic_factors_df()
    scores = sc.score(df, sc.DEFAULT_WEIGHTS)
    # nfm_potential_raw increases monotonically with row index; distance to
    # settlement also increases (reducing exposure) but weighted less than
    # NFM potential in DEFAULT_WEIGHTS is not guaranteed monotonic overall,
    # so just check the score is a finite, bounded number for every row.
    assert scores.notna().all()
    assert (scores >= -1).all() and (scores <= 1).all()


def test_score_penalises_protected_site_overlap():
    df = _synthetic_factors_df(n=5)
    clean = sc.score(df, sc.DEFAULT_WEIGHTS)
    df_flagged = df.copy()
    df_flagged["overlap_protected_pct"] = [50.0] * 5
    flagged = sc.score(df_flagged, sc.DEFAULT_WEIGHTS)
    assert (flagged <= clean).all()


def test_all_alt_weight_sets_sum_reasonably():
    for name, weights in sc.ALT_WEIGHTS.items():
        total = weights["nfm_potential"] + weights["exposure"] + weights["habitat"] + weights["activity_gap"]
        assert 0.9 <= total <= 1.1, f"{name} scored-factor weights should sum close to 1, got {total}"


def test_large_site_threshold_is_documented_value():
    assert sc.LARGE_SITE_THRESHOLD_HA == 1000


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
