# Scope Note — Week 1

## Catchment selected
**River Ribble catchment, Lancashire**

## Why
- Active local partner: [Ribble Rivers Trust](https://ribbletrust.org.uk/community-catchments/), currently running a "Community Catchments" initiative in Wrea Green, Darwen and Clitheroe.
- Identifiable downstream communities with documented flood history (Ribble Valley towns, including Clitheroe and Darwen).
- NFM delivery in the catchment is early-stage rather than exhaustive, leaving room for the project to find genuine gaps between national model potential and recorded activity — rather than re-surfacing already-known sites.
- Fully within England, so all core national datasets apply without cross-border data gaps (EA NFM Heat Maps, Natural England Priority Habitats Inventory / Habitat Networks).

## Spatial unit for screening
**Ribble Management Catchment** (EA Catchment Data Explorer ID 3070) — confirmed as the study area envelope, matching how the Environment Agency and Ribble Rivers Trust already report on the river.

## Week 1 checklist (from project brief)
- [x] Select catchment and define rationale
- [x] Confirm exact spatial boundary (management vs. operational catchment)
- [x] Identify and download each data source; retain raw files
- [x] Populate provenance manifest (source, date, licence, resolution)

## Data acquisition notes
All 7 datasets are in `data/raw/` — see `docs/provenance_manifest.csv` for full detail. One dataset (RoFRS) required manual acquisition: the EA exposes it only via WMS raster tiles and an interactive area-of-interest export tool (no bbox-queryable vector API like the other sources). It was acquired through 12 manually-drawn AOI exports, merged into a single GeoPackage per depth band, reaching 98.8% coverage of the catchment by area (76% of NFM hotspot candidates fall within covered area). The remaining ~1.2% is thin edge slivers along the catchment's irregular boundary — accepted as immaterial.
