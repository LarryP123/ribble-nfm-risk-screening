"""Unit tests for the pure text-formatting helpers in build_site_cards.py -
these produced a real bug once (a stray .capitalize() call lower-cased
proper nouns like "SSSI"), so they're worth pinning down."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_site_cards as bsc  # noqa: E402


def test_shorten_names_passes_through_short_lists():
    assert bsc.shorten_names("SSSI One") == "SSSI One"
    assert bsc.shorten_names("SSSI One; SSSI Two") == "SSSI One; SSSI Two"


def test_shorten_names_truncates_long_lists_with_count():
    result = bsc.shorten_names("A; B; C; D")
    assert "A" in result and "B" in result
    assert "+2 more" in result


def test_infer_interventions_never_empty():
    row = {"overlap_rofrs_pct": 0, "overlap_habitat_networks_pct": 0, "dist_recorded_restoration_km": 0}
    result = bsc.infer_interventions(row)
    assert len(result) > 0


def test_infer_interventions_suggests_floodplain_when_rofrs_overlaps():
    row = {"overlap_rofrs_pct": 5, "overlap_habitat_networks_pct": 0, "dist_recorded_restoration_km": 0}
    assert "floodplain" in bsc.infer_interventions(row).lower()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
