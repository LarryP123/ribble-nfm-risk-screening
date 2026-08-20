"""Week 2: build validated spatial staging layers.

Reprojects every raw source to a common CRS (EPSG:27700, British National Grid),
clips it precisely to the Ribble Management Catchment boundary (not just the
bounding-box extent used when downloading), fixes invalid geometries, and
writes everything into one GeoPackage that acts as the project's spatial
database: data/processed/ribble_nfm_staging.gpkg.

Rebuild from raw files with:
    python3 scripts/build_staging_layers.py
"""
import json
import shutil
import subprocess
from pathlib import Path

import geopandas as gpd
import pyogrio
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
STAGING_GPKG = PROCESSED / "ribble_nfm_staging.gpkg"
TARGET_CRS = "EPSG:27700"

CATCHMENT_WGS84 = RAW / "ribble_management_catchment.geojson"
CATCHMENT_BNG = INTERIM / "catchment_boundary_27700.gpkg"

# (source path, source EPSG, ogr layer name to select or None, output layer name)
WGS84_SOURCES = [
    (RAW / "nfm_hotspots_ribble.geojson", "nfm_hotspots"),
    (RAW / "recorded_flood_outlines_ribble.geojson", "recorded_flood_outlines"),
    (RAW / "priority_habitats_inventory_ribble.geojson", "priority_habitats_inventory"),
    (RAW / "habitat_networks_ribble.geojson", "habitat_networks"),
]

# These sources contain self-intersecting/nested-shell geometries that make
# ogr2ogr's -clipsrc fail silently on individual features (confirmed: it drops
# them rather than erroring). Cleaned and clipped with geopandas/shapely
# make_valid instead, which recovers all of them.
ROBUST_CLIP_SOURCES = [
    (RAW / "sssi_ribble.geojson", "sssi"),
    (RAW / "sac_ribble.geojson", "sac"),
    (RAW / "scheduled_monuments_ribble.geojson", "scheduled_monuments"),
]

BNG_SOURCES = [
    (RAW / "priority_habitat_creation_restoration_extracted" / "Priority_Habitat_Creation_and_Restoration.gpkg", "priority_habitat_creation_restoration"),
    (RAW / "rofrs_combined" / "rofrs_4bandPolygon.gpkg", "rofrs_overall"),
    (RAW / "rofrs_combined" / "rofrs_4band_0_2m_depthPolygon.gpkg", "rofrs_depth_0_2m"),
    (RAW / "rofrs_combined" / "rofrs_4band_0_3m_depthPolygon.gpkg", "rofrs_depth_0_3m"),
    (RAW / "rofrs_combined" / "rofrs_4band_0_6m_depthPolygon.gpkg", "rofrs_depth_0_6m"),
    (RAW / "rofrs_combined" / "rofrs_4band_0_9m_depthPolygon.gpkg", "rofrs_depth_0_9m"),
    (RAW / "rofrs_combined" / "rofrs_4band_1_2m_depthPolygon.gpkg", "rofrs_depth_1_2m"),
]

BNG_SOURCES_WITH_LAYER = [
    (RAW / "os_open_data" / "extracted" / "rivers" / "Data" / "oprvrs_gb.gpkg", "watercourse_link", "os_open_rivers"),
    (RAW / "os_open_data" / "extracted" / "built_up_areas" / "os_open_built_up_areas.gpkg", "os_open_built_up_areas", "os_open_built_up_areas"),
    (RAW / "os_open_data" / "extracted" / "roads" / "Data" / "oproad_gb.gpkg", "road_link", "os_open_roads"),
]


def build_catchment_boundary():
    """Dissolve the 159-feature catchment download into one clean polygon,
    in both WGS84 (to clip WGS84 sources) and BNG (to clip BNG sources and
    as the reference layer in the staging database)."""
    gdf = gpd.read_file(CATCHMENT_WGS84)
    dissolved = unary_union(gdf.geometry.values)
    catchment_wgs84 = gpd.GeoDataFrame({"name": ["Ribble Management Catchment"]}, geometry=[dissolved], crs="EPSG:4326")

    INTERIM.mkdir(parents=True, exist_ok=True)
    catchment_wgs84_path = INTERIM / "catchment_boundary_4326.geojson"
    catchment_wgs84.to_file(catchment_wgs84_path, driver="GeoJSON")

    catchment_bng = catchment_wgs84.to_crs(TARGET_CRS)
    catchment_bng.to_file(CATCHMENT_BNG, driver="GPKG", layer="catchment_boundary")

    PROCESSED.mkdir(parents=True, exist_ok=True)
    if STAGING_GPKG.exists():
        STAGING_GPKG.unlink()
    catchment_bng.to_file(STAGING_GPKG, driver="GPKG", layer="catchment_boundary")
    print(f"catchment_boundary: 1 dissolved feature, area {catchment_bng.geometry.area.sum() / 1e6:.1f} km2")
    return catchment_wgs84_path


def ogr_reproject_clip(source, layer_name, clip_source, clip_srs_matches_source, source_layer=None):
    """Reproject `source` to TARGET_CRS, clip to the catchment boundary, fix
    invalid geometries, and append as `layer_name` in the staging GeoPackage.
    `source_layer` selects one layer out of a multi-layer source GeoPackage."""
    cmd = [
        "ogr2ogr",
        "-f", "GPKG",
        "-update", "-append",
        str(STAGING_GPKG),
        str(source),
    ]
    if source_layer:
        cmd.append(source_layer)
    cmd += [
        "-t_srs", TARGET_CRS,
        "-clipsrc", str(clip_source),
        "-makevalid",
        "-nln", layer_name,
        "-nlt", "PROMOTE_TO_MULTI",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FAILED {layer_name}:\n{result.stderr}")
        raise SystemExit(1)
    count = subprocess.run(
        ["ogrinfo", "-so", str(STAGING_GPKG), layer_name],
        capture_output=True, text=True,
    ).stdout
    feature_count = next((l for l in count.splitlines() if "Feature Count" in l), "?")
    print(f"{layer_name}: {feature_count.strip()}")


POLYGONAL = ("Polygon", "MultiPolygon")
LINEAL = ("LineString", "MultiLineString")
PUNTAL = ("Point", "MultiPoint")


def extract_matching(geom, keep_types):
    """ogr2ogr's -clipsrc sometimes returns a GeometryCollection when the clip
    boundary just grazes a source feature's edge (the real feature plus a
    degenerate lower-dimension sliver). Keep only the part matching the
    layer's own geometry family."""
    if geom is None or geom.geom_type in keep_types:
        return geom
    if geom.geom_type == "GeometryCollection":
        parts = [g for g in geom.geoms if g.geom_type in keep_types]
        return unary_union(parts) if parts else None
    return geom


def clean_geometry_collections():
    """Post-process every layer in the staging GeoPackage to remove
    GeometryCollection artifacts left by clipping."""
    print("\n== Cleaning clip artifacts (GeometryCollection -> single-family geometry) ==")
    layers = [l[0] for l in pyogrio.list_layers(STAGING_GPKG)]
    for layer in layers:
        gdf = gpd.read_file(STAGING_GPKG, layer=layer)
        n_gc = (gdf.geometry.geom_type == "GeometryCollection").sum()
        if n_gc == 0:
            continue
        non_gc_types = gdf.loc[gdf.geometry.geom_type != "GeometryCollection", "geometry"].geom_type
        dominant = non_gc_types.mode().iloc[0] if len(non_gc_types) else "MultiPolygon"
        keep_types = POLYGONAL if dominant in POLYGONAL else LINEAL if dominant in LINEAL else PUNTAL
        gdf["geometry"] = gdf.geometry.apply(lambda g: extract_matching(g, keep_types))
        before = len(gdf)
        gdf = gdf[~gdf.geometry.isna()]
        dropped = before - len(gdf)
        gdf.to_file(STAGING_GPKG, driver="GPKG", layer=layer, mode="w")
        print(f"{layer}: cleaned {n_gc} GeometryCollections, dropped {dropped} fully-degenerate features")


def robust_clean_clip(source, layer_name, catchment_gdf):
    """geopandas/shapely version of the clip, for sources whose geometries
    trip up ogr2ogr's clip (self-intersections, nested shells)."""
    gdf = gpd.read_file(source)
    gdf["geometry"] = gdf.geometry.apply(lambda g: make_valid(g) if g is not None and not g.is_valid else g)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
    gdf = gdf.to_crs(TARGET_CRS)
    clipped = gpd.clip(gdf, catchment_gdf)
    clipped = clipped[~clipped.geometry.is_empty]
    clipped.to_file(STAGING_GPKG, driver="GPKG", layer=layer_name)
    print(f"{layer_name}: {len(gdf)} raw -> {len(clipped)} after clip")


def main():
    print("== Building catchment boundary ==")
    catchment_wgs84_path = build_catchment_boundary()

    print("\n== WGS84 sources (clip in EPSG:4326, then reproject) ==")
    for source, layer_name in WGS84_SOURCES:
        ogr_reproject_clip(source, layer_name, catchment_wgs84_path, clip_srs_matches_source=True)

    print("\n== BNG sources (already EPSG:27700, clip directly) ==")
    for source, layer_name in BNG_SOURCES:
        ogr_reproject_clip(source, layer_name, CATCHMENT_BNG, clip_srs_matches_source=True)

    print("\n== BNG sources with named source layers (OS Open Data) ==")
    for source, source_layer, layer_name in BNG_SOURCES_WITH_LAYER:
        ogr_reproject_clip(source, layer_name, CATCHMENT_BNG, clip_srs_matches_source=True, source_layer=source_layer)

    print("\n== Robust-clip sources (protected sites - fragile geometries) ==")
    catchment_bng_gdf = gpd.read_file(STAGING_GPKG, layer="catchment_boundary")
    for source, layer_name in ROBUST_CLIP_SOURCES:
        robust_clean_clip(source, layer_name, catchment_bng_gdf)

    clean_geometry_collections()

    print(f"\nStaging database written to {STAGING_GPKG}")


if __name__ == "__main__":
    main()
