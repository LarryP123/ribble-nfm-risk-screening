# Data Dictionary — Staging Layers

Spatial database: `data/processed/ribble_nfm_staging.gpkg`
Common CRS: EPSG:27700 (British National Grid, metres)
Built by: `scripts/build_staging_layers.py` (rerun to rebuild from `data/raw/`)

Every layer is clipped to the exact Ribble Management Catchment boundary (not
the rectangular bounding boxes used when the raw data was downloaded).

| Layer | Source dataset | Geometry | Feature count | Notes |
|---|---|---|---|---|
| `catchment_boundary` | EA Catchment Data Explorer (mgmt catchment 3070) | Polygon | 1 | Dissolved from 159 downloaded sub-polygons into one clean feature (1,404.5 km²); defines the clip boundary for every other layer |
| `nfm_hotspots` | EA NFM Heat Maps | MultiPolygon | 41 | Modelled natural flood management opportunity areas, by intervention type |
| `recorded_flood_outlines` | EA Recorded Flood Outlines | MultiPolygon | 282 | Historic flood extents, records from 1946 onwards |
| `priority_habitats_inventory` | Natural England PHI | MultiPolygon | 8,278 | Existing priority habitat parcels and classification |
| `habitat_networks` | Natural England Habitat Networks | MultiPolygon | 7,887 | Habitat expansion/connectivity opportunity zones |
| `priority_habitat_creation_restoration` | EA Priority Habitat Creation and Restoration | **MultiPoint** | 85 | Recorded/planned restoration project locations (point sites, not area extents) |
| `rofrs_overall` | EA RoFRS (4-band combined) | MultiPolygon | 2,973 | Overall river/sea flood risk banding; covers 82.7 km² (5.9%) of the catchment — flood risk naturally concentrates along river corridors/floodplains, not the whole catchment |
| `rofrs_depth_0_2m` .. `rofrs_depth_1_2m` | EA RoFRS | MultiPolygon | ~3,200-3,500 each | Same flood risk product split by modelled depth band (0.2/0.3/0.6/0.9/1.2m) |
| `os_open_rivers` | Ordnance Survey OS Open Rivers | MultiLineString | 1,469 | Watercourse network (`watercourse_link` layer only); fills the Week 1 "rivers and terrain" gap |
| `os_open_roads` | Ordnance Survey OS Open Roads | MultiLineString | 54,171 | Road network (`road_link` layer only); downstream-exposure/constraint proxy |
| `os_open_built_up_areas` | Ordnance Survey OS Open Built Up Areas | MultiPolygon | 75 | Settlement extents ≥20ha; downstream-exposure/community proxy; fills the Week 1 "settlements" gap |
| `sssi` | Natural England SSSI | MultiPolygon | 43 | Sites of Special Scientific Interest — statutory protected-site constraint |
| `sac` | Natural England SAC | Polygon | 6 | Special Areas of Conservation — statutory protected-site constraint |
| `scheduled_monuments` | Historic England (National Heritage List) | MultiPolygon | 83 | Scheduled Monuments — statutory protected-site constraint |

## Validation performed

- **CRS**: all 18 layers confirmed EPSG:27700.
- **Geometry validity**: 0 invalid, 0 empty geometries across all layers.
- **Geometry purity**: ogr2ogr's clip step left a handful of `GeometryCollection`
  artifacts per layer (a real polygon bundled with a degenerate line/point
  sliver, where the clip boundary just grazes a source feature's edge). These
  were cleaned to polygon-only with no features lost; the fix is built into
  `build_staging_layers.py` so a full rebuild reproduces it automatically.
- **RoFRS acquisition coverage** (i.e. did we successfully *download* data for
  the whole catchment, distinct from what fraction of the catchment is
  actually flood-risk land): 98.8% of the catchment by area, from the 12
  manually-drawn AOI exports. See `docs/provenance_manifest.csv`.
- **Protected-site geometry recovery**: 7 of 133 raw SSSI features had
  self-intersecting rings; ogr2ogr's `-clipsrc` silently dropped them rather
  than erroring. Re-clipping with `shapely.make_valid` + `geopandas.clip`
  recovered all of them — a useful reminder that a clean exit code from
  ogr2ogr doesn't guarantee no features were lost.

## Known limitations carried into staging

- **RoFRS acquisition**: no bbox/vector API existed for this dataset, so it
  was acquired via 12 manually-drawn area-of-interest exports on the EA
  portal. A residual ~1.2% acquisition gap remains as thin slivers along the
  catchment's irregular edge.
- All layers were bbox-clipped at download time, then re-clipped here to the
  *exact* catchment polygon — so staged layers should not contain material
  outside the true catchment boundary, even though the raw downloads did.
