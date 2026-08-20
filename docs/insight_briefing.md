# Insight Briefing — Ribble Catchment NFM Screening

**Status: pre-validation draft.** Written after Week 4 (screening + site cards)
and before Week 5 practitioner feedback has come back from Ribble Rivers
Trust. The findings below are what the public data shows; they are explicitly
not yet checked against local knowledge. This document will be revised once
that feedback lands — see "What happens next."

> **Every candidate named in this briefing is a SCREENING AREA — not a
> proposed construction boundary, not an engineering design, and not a
> statement that any site is ready for investment or delivery.**

## The question

Which locations in the Ribble catchment show strong potential for natural
flood management and habitat recovery, but little recorded delivery — and are
they genuine opportunities or gaps in the public data?

## What the screening found

Combining the EA's NFM Heat Maps, flood-risk and recorded-flooding data,
Natural England's habitat layers, OS settlement and river data, and SSSI/SAC/
Scheduled Monument boundaries, 41 modelled opportunity polygons were
dissolved into **35 distinct candidates** across the catchment and scored
against six factors (NFM potential, nearby community exposure, habitat
opportunity, recorded-activity gap, visible constraints, data confidence).
Any candidate ≥1,000ha is labelled an "Investigation Zone" rather than a
"Candidate Site" — 5 of the 35 fall into that category and are not presented
as individual site cards.

**Five sites were carried forward as site cards**: C16 (Sabden), C21
(Barrowford), C14 (Withnell), C22 (Gisburn), C23 (Giggleswick). They were
chosen for a combination of composite score, rank stability across four
different weighting schemes, and deliberate catchment-wide spread — not
simply the top five by rank. Full reasoning, including a correction that
changed this list after the first pass, is in
[docs/week4_manual_review.md](week4_manual_review.md).

**One geographic pattern stood out**: the top-ranked, rank-stable candidates
cluster heavily in the Pendle/Ribble Valley area near Clitheroe. That is
itself a finding — the modelled NFM signal in this catchment is not evenly
spread — not an artefact of the method.

**One candidate (C23) carries a real flagged constraint**: it overlaps two
SSSIs (Giggleswick Scar and Kinsey Cave) and a Scheduled Monument. It was
kept as a site card specifically because that flag is a useful, honest thing
for a practitioner to confirm — this is the only credible candidate near the
upper catchment, and the constraint is exactly the kind of thing worth
surfacing rather than hiding behind a clean-looking list.

**A second candidate (C17), originally a top pick, was dropped after a
correction.** At 2,076ha it's an Investigation Zone, not a site, and it
overlaps *five* separate SSSIs. Both facts were invisible under the first
version of the methodology — this correction is discussed under "What
changed" below.

## Limitations that shaped what could be found

- **"Nearby community exposure" is settlement proximity plus recorded
  historic flood overlap, not verified hydrology.** No flow-direction/DEM
  analysis was done, so a nearby settlement is treated as plausibly exposed
  rather than confirmed as downstream — the factor is named accordingly.
- **NFM potential is scored by polygon area**, because the source dataset
  carries no actual opportunity-strength attribute. Large modelled area and
  strong opportunity are not the same thing.
- **The recorded-activity signal (85 points catchment-wide) may itself be
  incomplete** — a candidate flagged as an "opportunity gap" could just mean
  the EA's project register hasn't caught up with local reality, which is
  exactly the kind of thing Week 5 outreach exists to check.
- **RoFRS flood-risk data required 12 manual exports** (no bbox API existed)
  and reaches 98.8% catchment coverage; two candidates fall in the residual
  gap and are flagged low-confidence rather than silently treated as
  equivalent to the rest. RoFRS overlap is reported per candidate as context
  only — it is not scored, since it measures the site's own flood setting,
  not community exposure (see docs/screening_methodology.md for why). **This
  means the low-confidence flag describes incomplete flood-risk context
  only — it does not mean those two candidates' rank or composite score is
  any less reliable than the rest.**

## What changed in the correction

The original methodology scored six factors but left two real gaps: it
computed RoFRS overlap without deciding what to do with it, never used the
recorded historic flood outlines at all, had no protected-site data, and
didn't act on the fact that some candidates were far too large to be a
"site." Fixing this **changed the final five**: C17 dropped out (now
correctly flagged as an oversized, heavily SSSI-constrained Investigation
Zone) and C22 replaced it. C23 stayed, but its card now says plainly that it
overlaps protected land. Full detail: docs/screening_methodology.md and
docs/week4_manual_review.md.

## Recommended next checks

1. Confirm with Ribble Rivers Trust whether C16, C21, C14, C22 have any
   unrecorded activity, ownership constraints, or access issues not visible
   in national datasets.
2. Specifically ask whether C23's SSSI/Scheduled Monument overlap rules it
   out entirely, or whether a smaller feasible area exists within it.
3. None of the five should be treated as ready for investment or delivery —
   this narrows the search and surfaces uncertainty; it does not replace
   hydrological, ecological, or engineering assessment.

## What happens next

Week 5 outreach materials (one-page summary + catchment map) are prepared
and ready to send to Ribble Rivers Trust — not yet sent. When feedback
arrives, [docs/week4_manual_review.md](week4_manual_review.md) and this
briefing get revised with what was confirmed, what was rejected, and why —
following the brief's own suggested structure: state what the data found,
then what local review changed about it.
