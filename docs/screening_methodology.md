# Screening Methodology — Week 3 (corrected)

Built by: `scripts/score_candidates.py` (rerun to rebuild from the staging database)
Output: `data/processed/candidate_longlist.gpkg` / `.csv`

**This is a corrected version of the original Week 3 methodology.** The
corrections and the reasoning behind each are recorded here rather than
silently overwritten, since the changes materially affected the ranking (see
[docs/week4_manual_review.md](week4_manual_review.md) for the resulting
change to the final five).

## Spatial unit, and large polygons

The 41 raw `nfm_hotspots` polygons range from 2ha to 5,543ha. Touching/
overlapping polygons are dissolved into **35 candidates**. Any candidate
**≥1,000ha is labelled an "Investigation Zone" rather than a "Candidate
Site"** — this threshold was chosen because it's roughly the scale at which a
polygon stops being something a practitioner could walk and assess as one
unit. Oversized polygons are **not** algorithmically subdivided: no real
sub-parcel or ownership data exists in this project to split them
defensibly, and a geometric split (e.g. a grid) would create false precision
without adding real information. 5 of the 35 candidates are Investigation
Zones under this rule (C17, C20, C10, C13, C25 — see the CSV `site_type`
column). Investigation Zones are not presented as individual site cards.

## Flood-risk evidence: two different signals, treated differently

Two flood datasets touch this analysis, and they measure genuinely different
things - conflating them would be a mistake, so they're handled separately
and the reasoning is explicit:

- **RoFRS** (`overlap_rofrs_pct`) is a *modelled* flood-risk product
  describing the site's own hydrological setting. It is **not** blended into
  any score. It isn't evidence of community exposure (it doesn't show who's
  downstream), and it isn't the same modelled product as the NFM Heat Maps
  (blending it into "NFM potential" would silently combine two different EA
  outputs into one number). It's kept as **contextual evidence only** -
  reported per candidate, useful for interpreting a site, not scored.
- **Recorded Flood Outlines** (`overlap_recorded_flood_pct`) is
  ground-truthed evidence of an actual historic flood event. Unlike RoFRS,
  this **is** scored, as part of nearby community exposure (below) - a
  candidate whose area overlaps a recorded historic flood is directly
  evidenced as flood-affected, which is stronger evidence than a settlement
  merely being nearby.

## The six factors

| Factor | What's computed | Change from the original version |
|---|---|---|
| **NFM potential** | Candidate area (ha), percentile-ranked | Unchanged - still the modelled-area proxy, still a known weakness (area is not the same as opportunity strength) |
| **Nearby community exposure** *(renamed from "downstream exposure")* | 50% settlement proximity (decays to 0 beyond 5km) + 50% recorded-flood-outline overlap (saturates at 20% overlap) | Renamed because no flow-direction/hydrology modelling exists here - this is proximity, not a verified downstream relationship. Recorded flood overlap is new. |
| **Habitat opportunity** | 60% overlap with `habitat_networks`, 40% inverse distance to `priority_habitats_inventory` | Unchanged |
| **Recorded-activity gap** | Distance to nearest recorded restoration/creation point (decays to 0 beyond 3km) | Unchanged |
| **Visible constraints** | 40% settlement overlap + 20% road density + 40% protected-site overlap (SSSI/SAC/Scheduled Monuments) | Protected-site overlap is new. Road density's weight dropped from 50% to 20% to make room for it, since a statutory designation is a harder constraint than road density |
| **Data confidence** | Flags candidates in the residual ~1.2% RoFRS acquisition gap | Scoped more explicitly this round - see "What data confidence actually covers" below |

### What data confidence actually covers (and doesn't)

`data_confidence` is deliberately narrow: it flags whether the *contextual*
RoFRS layer (`flood_risk_overlap_pct`) has coverage for a given candidate -
nothing more. This needed spelling out explicitly, because on its own it's
easy to misread as "how much should I trust this candidate's score," which
it does not mean:

- RoFRS is **not** a scored factor (see "Flood-risk evidence" above) - it's
  shown to a practitioner as context, not fed into the composite score.
- Every layer that **is** scored (habitat networks, priority habitats,
  recorded restoration points, settlements, roads, SSSI/SAC/Scheduled
  Monuments) has full, reliable coverage across the whole catchment - none
  of them have an acquisition gap like RoFRS does.
- So a candidate flagged `Low` has an incomplete *contextual* picture (you
  can't see whether it sits in mapped flood risk), but its rank and
  composite score are exactly as reliable as any `High` candidate's.

Per the brief's own framework, this still legitimately "qualifies the
recommendation" - it's just a qualification about one specific piece of
context shown alongside a candidate, not about the ranking itself. The
`data_confidence_note` field (in the DuckDB `candidate_summary` table and
the CSV/GeoPackage) spells this out per-row rather than leaving it implicit.

### Protected-site constraints (new)

SSSI, SAC, and Scheduled Monument boundaries (Natural England / Historic
England) are now acquired and clipped to the catchment (see
`docs/provenance_manifest.csv`). Any candidate overlapping one gets:

1. A contribution to the constraint-penalty score (proportional to overlap %), and
2. An explicit **`protected_site_flag`** column naming the overlapping
   site(s) - a statutory constraint is legible information a practitioner
   needs to see directly, not something that should only show up as a
   slightly lower composite score.

**9 of 35 candidates** overlap a protected site. One (C24) is 87.5%
inside an SSSI (Langcliffe Scars / Jubilee, Albert and Victoria Caves) - its
"opportunity gap" almost certainly reflects that conventional NFM delivery
there would need SSSI consent, not that it's genuinely overlooked.

## Terminology

- **"Downstream exposure" → "Nearby community exposure"**, everywhere in
  this project, until real flow-direction modelling exists.
- **"Possible interventions" → "Interventions to investigate"**, on site
  cards - the original phrasing read more like a recommendation than a
  prompt for further work.

## Weights (explicit, adjustable)

| Factor | Weight |
|---|---|
| NFM potential | 0.30 |
| Nearby community exposure | 0.25 |
| Habitat opportunity | 0.20 |
| Recorded-activity gap | 0.15 |
| Constraint penalty (subtracted) | 0.10 |

Unchanged from the original version - the correction changed what feeds
*into* exposure and constraint, not their overall weight in the composite.

## Sensitivity analysis

Unchanged process: the score is recomputed under `equal`, `exposure_heavy`,
and `habitat_heavy` alternative weightings alongside `default`.
`top10_stability` counts how many of the 4 weightings place a candidate in
that weighting's own top 10 (0-4). **Re-running after the correction changed
several candidates' stability** - most notably C17 stayed 4/4 stable by rank,
but is no longer presented as a site card because of its size and protected-
site overlap; stability alone doesn't capture deliverability.

## What Week 3 does *not* claim

- This is a longlist, not a shortlist.
- "Nearby community exposure" is proximity, not verified hydrological
  connection - still true after this correction; only the label changed to
  be honest about it.
- Investigation Zones are not excluded from the dataset, only from the
  site-card selection - they remain visible in the full longlist and on the
  catchment overview map.
