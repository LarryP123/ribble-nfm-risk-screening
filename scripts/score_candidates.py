"""Week 3 (corrected): screening features and candidate ranking.

Corrections applied in this version, per review:
- Flood-risk evidence: RoFRS site-overlap is reported as context only, NOT
  scored (it measures the site's own flood-risk setting, not community
  exposure or modelled NFM opportunity - blending it into either would
  conflate three different EA products). See docs/screening_methodology.md.
- Recorded Flood Outlines overlap is now calculated and DOES feed into the
  community-exposure score - unlike RoFRS, it's ground-truthed evidence of a
  real historic flood event, which is direct exposure evidence.
- "Downstream exposure" is renamed "nearby community exposure" throughout -
  no flow-direction modelling exists, so this is proximity, not a verified
  downstream relationship.
- Protected-site constraints (SSSI, SAC, Scheduled Monuments) are now
  computed and feed into the constraint penalty, plus an explicit named flag
  (a statutory constraint deserves a legible flag, not just a lower score).
- Oversized polygons (>= LARGE_SITE_THRESHOLD_HA) are labelled "Investigation
  Zone" rather than "Candidate Site" - not split, since no real sub-parcel
  data exists to split them defensibly.

Rebuild from the staging database with:
    python3 scripts/score_candidates.py
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
STAGING_GPKG = ROOT / "data" / "processed" / "ribble_nfm_staging.gpkg"
OUT_GPKG = ROOT / "data" / "processed" / "candidate_longlist.gpkg"
OUT_CSV = ROOT / "data" / "processed" / "candidate_longlist.csv"

LARGE_SITE_THRESHOLD_HA = 1000  # >= this: labelled "Investigation Zone", not "Candidate Site"

# Explicit, adjustable weights (brief: "weights will be explicit and tested
# through sensitivity analysis"). Data confidence is deliberately NOT blended
# into the score - it qualifies the recommendation instead.
DEFAULT_WEIGHTS = dict(nfm_potential=0.30, exposure=0.25, habitat=0.20, activity_gap=0.15, constraint=0.10)
ALT_WEIGHTS = {
    "default": DEFAULT_WEIGHTS,
    "equal": dict(nfm_potential=0.25, exposure=0.25, habitat=0.25, activity_gap=0.25, constraint=0.10),
    "exposure_heavy": dict(nfm_potential=0.25, exposure=0.40, habitat=0.15, activity_gap=0.10, constraint=0.10),
    "habitat_heavy": dict(nfm_potential=0.20, exposure=0.15, habitat=0.40, activity_gap=0.15, constraint=0.10),
}

BUILT_UP_DECAY_KM = 5.0
RESTORATION_DECAY_KM = 3.0
RECORDED_FLOOD_OVERLAP_SATURATION_PCT = 20.0  # overlap at/above this treated as maximal exposure evidence


def load(layer):
    return gpd.read_file(STAGING_GPKG, layer=layer)


def build_candidate_sites(hotspots):
    merged = unary_union(hotspots.geometry.buffer(0).values)
    geoms = list(merged.geoms) if merged.geom_type == "MultiPolygon" else [merged]
    sites = gpd.GeoDataFrame(
        {"candidate_id": [f"C{i+1:02d}" for i in range(len(geoms))]},
        geometry=geoms,
        crs=hotspots.crs,
    )
    sites["area_ha"] = sites.geometry.area / 10_000
    sites["site_type"] = sites["area_ha"].apply(
        lambda a: "Investigation Zone" if a >= LARGE_SITE_THRESHOLD_HA else "Candidate Site"
    )
    return sites.sort_values("area_ha", ascending=False).reset_index(drop=True)


def min_distance_km(sites, other):
    if len(other) == 0:
        return pd.Series(float("inf"), index=sites.index)
    other_union = other.geometry.union_all()
    return sites.geometry.distance(other_union) / 1000


def overlap_pct(sites, other):
    if len(other) == 0:
        return pd.Series(0.0, index=sites.index)
    other_union = other.geometry.union_all()
    return sites.geometry.apply(lambda g: g.intersection(other_union).area / g.area * 100 if g.area else 0.0)


def line_length_km_within(sites, lines):
    if len(lines) == 0:
        return pd.Series(0.0, index=sites.index)
    lines_union = lines.geometry.union_all()
    return sites.geometry.apply(lambda g: g.intersection(lines_union).length / 1000)


def overlapping_names(sites, other, name_col):
    """For each site, list the names of `other` features it actually overlaps."""
    result = []
    for g in sites.geometry:
        hits = other[other.geometry.intersects(g)]
        result.append("; ".join(sorted(hits[name_col].astype(str).str.strip().replace("", pd.NA).dropna().unique())))
    return pd.Series(result, index=sites.index)


def percentile_rank(series):
    return series.rank(pct=True, method="average")


def compute_factors(sites, layers):
    df = sites.copy()

    # --- NFM potential: modelled-area proxy only (RoFRS deliberately excluded - see module docstring) ---
    df["nfm_potential_raw"] = df["area_ha"]
    df["overlap_rofrs_pct"] = overlap_pct(sites, layers["rofrs_overall"])  # contextual only, not scored

    # --- Nearby community exposure: settlement proximity + recorded historic flood overlap ---
    df["dist_built_up_km"] = min_distance_km(sites, layers["os_open_built_up_areas"])
    df["n_built_up_within_5km"] = sites.geometry.apply(
        lambda g: (layers["os_open_built_up_areas"].geometry.distance(g) <= 5000).sum()
    )
    df["overlap_recorded_flood_pct"] = overlap_pct(sites, layers["recorded_flood_outlines"])

    # --- Habitat opportunity ---
    df["overlap_habitat_networks_pct"] = overlap_pct(sites, layers["habitat_networks"])
    df["dist_phi_km"] = min_distance_km(sites, layers["priority_habitats_inventory"])

    # --- Recorded activity gap ---
    df["dist_recorded_restoration_km"] = min_distance_km(sites, layers["priority_habitat_creation_restoration"])

    # --- Visible constraints: settlement + road + protected sites ---
    df["overlap_built_up_pct"] = overlap_pct(sites, layers["os_open_built_up_areas"])
    df["road_km_within"] = line_length_km_within(sites, layers["os_open_roads"])
    df["road_density_km_per_km2"] = df["road_km_within"] / (df["area_ha"] / 100)

    protected_union = gpd.GeoDataFrame(
        pd.concat([layers["sssi"][["geometry"]], layers["sac"][["geometry"]], layers["scheduled_monuments"][["geometry"]]]),
        crs=sites.crs,
    )
    df["overlap_protected_pct"] = overlap_pct(sites, protected_union)
    sssi_names = overlapping_names(sites, layers["sssi"], "name")
    sac_names = overlapping_names(sites, layers["sac"], "sac_name")
    monument_names = overlapping_names(sites, layers["scheduled_monuments"], "Name")
    df["protected_site_flag"] = [
        "; ".join(x for x in (s, a, m) if x) or "None"
        for s, a, m in zip(sssi_names, sac_names, monument_names)
    ]

    return df


def score(df, weights):
    nfm_potential_score = percentile_rank(df["nfm_potential_raw"])

    settlement_proximity_score = 1 - (df["dist_built_up_km"].clip(upper=BUILT_UP_DECAY_KM) / BUILT_UP_DECAY_KM)
    recorded_flood_score = (df["overlap_recorded_flood_pct"] / RECORDED_FLOOD_OVERLAP_SATURATION_PCT).clip(upper=1.0)
    exposure_score = 0.5 * settlement_proximity_score + 0.5 * recorded_flood_score

    habitat_score = 0.6 * percentile_rank(df["overlap_habitat_networks_pct"]) + 0.4 * (
        1 - percentile_rank(df["dist_phi_km"])
    )
    activity_gap_score = df["dist_recorded_restoration_km"].clip(upper=RESTORATION_DECAY_KM) / RESTORATION_DECAY_KM

    constraint_penalty = (
        0.4 * percentile_rank(df["overlap_built_up_pct"])
        + 0.2 * percentile_rank(df["road_density_km_per_km2"])
        + 0.4 * percentile_rank(df["overlap_protected_pct"])
    )

    composite = (
        weights["nfm_potential"] * nfm_potential_score
        + weights["exposure"] * exposure_score
        + weights["habitat"] * habitat_score
        + weights["activity_gap"] * activity_gap_score
        - weights["constraint"] * constraint_penalty
    )
    return composite


def band(composite):
    q = composite.rank(pct=True)
    return pd.cut(
        q, bins=[0, 0.25, 0.5, 0.75, 1.0], labels=["Weak", "Watch", "Moderate", "Strong"], include_lowest=True
    )


def confidence_flag(df, rofrs_gap_geom):
    """data_confidence is deliberately scoped to ONE thing: whether the
    contextual RoFRS flood-risk layer has coverage for this candidate.
    RoFRS is not a scored factor (see module docstring / screening_methodology.md),
    so this flag does NOT indicate anything about the reliability of the
    composite score - every layer that IS scored has full, reliable coverage
    everywhere in the catchment. It exists because RoFRS overlap is still
    shown to a practitioner as context, and that context is incomplete for
    a small number of candidates - the brief's "data confidence... qualify
    recommendation" applies to that contextual picture, not the ranking."""
    if rofrs_gap_geom is None or rofrs_gap_geom.is_empty:
        in_gap = pd.Series(False, index=df.index)
    else:
        in_gap = df.geometry.apply(lambda g: g.intersects(rofrs_gap_geom))
    level = in_gap.map({True: "Low", False: "High"})
    note = in_gap.map({
        True: "RoFRS flood-risk context (not scored) is incomplete for this candidate - falls in the acquisition gap. Does not affect the composite score.",
        False: "Full RoFRS flood-risk context coverage for this candidate. RoFRS is not a scored factor either way.",
    })
    return level, note


def main():
    print("== Loading staging layers ==")
    layers = {
        name: load(name)
        for name in [
            "nfm_hotspots",
            "recorded_flood_outlines",
            "priority_habitats_inventory",
            "habitat_networks",
            "priority_habitat_creation_restoration",
            "rofrs_overall",
            "os_open_rivers",
            "os_open_roads",
            "os_open_built_up_areas",
            "sssi",
            "sac",
            "scheduled_monuments",
            "catchment_boundary",
        ]
    }

    print("== Building candidate sites (dissolving touching hotspot fragments) ==")
    sites = build_candidate_sites(layers["nfm_hotspots"])
    n_zones = (sites["site_type"] == "Investigation Zone").sum()
    print(f"{len(layers['nfm_hotspots'])} raw hotspot polygons -> {len(sites)} candidates "
          f"({n_zones} >= {LARGE_SITE_THRESHOLD_HA}ha, labelled Investigation Zone)")

    print("== Computing screening factors ==")
    df = compute_factors(sites, layers)

    print("== Scoring (default weights + sensitivity check) ==")
    for name, weights in ALT_WEIGHTS.items():
        df[f"score_{name}"] = score(df, weights)
        df[f"rank_{name}"] = df[f"score_{name}"].rank(ascending=False, method="min").astype(int)

    df["composite_score"] = df["score_default"]
    df["rank"] = df["rank_default"]
    df["band"] = band(df["composite_score"])

    df["top10_stability"] = df.apply(
        lambda r: sum(
            r["candidate_id"] in set(df.nsmallest(10, f"rank_{alt}")["candidate_id"]) for alt in ALT_WEIGHTS
        ),
        axis=1,
    )

    rofrs_extent = layers["rofrs_overall"].geometry.union_all().convex_hull
    catchment = layers["catchment_boundary"].geometry.iloc[0]
    rofrs_gap = catchment.difference(rofrs_extent.buffer(2000))
    df["data_confidence"], df["data_confidence_note"] = confidence_flag(df, rofrs_gap)

    df = df.sort_values("rank").reset_index(drop=True)

    print("\n== Top 10 candidates (default weighting) ==")
    print(
        df.nsmallest(10, "rank")[
            ["candidate_id", "site_type", "area_ha", "band", "composite_score", "top10_stability",
             "data_confidence", "protected_site_flag"]
        ].to_string(index=False)
    )

    print(f"\nProtected-site overlaps found on {(df['protected_site_flag'] != 'None').sum()} of {len(df)} candidates")

    gpd.GeoDataFrame(df, geometry="geometry", crs=sites.crs).to_file(OUT_GPKG, driver="GPKG", layer="candidate_longlist")
    df.drop(columns="geometry").to_csv(OUT_CSV, index=False)
    print(f"\nWritten: {OUT_GPKG}")
    print(f"Written: {OUT_CSV}")


if __name__ == "__main__":
    main()
