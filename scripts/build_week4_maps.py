"""Week 4 (revised): catchment overview, opportunity-gap map, and five site
maps (each with a locator inset) for the final five candidates chosen in
docs/week4_manual_review.md.

Revisions in this version: place-name labels, clearer/larger legends, and a
prominent "screening area, not a construction boundary" banner on every map.

Rebuild with:
    python3 scripts/build_week4_maps.py
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent.parent
STAGING = ROOT / "data" / "processed" / "ribble_nfm_staging.gpkg"
LONGLIST = ROOT / "data" / "processed" / "candidate_longlist.gpkg"
OUT_DIR = ROOT / "outputs" / "maps" / "week4"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FINAL_FIVE = ["C16", "C21", "C14", "C22", "C23"]
FINAL_FIVE_PLACES = {"Sabden", "Barrowford", "Withnell", "Gisburn", "Giggleswick"}
BAND_COLORS = {"Strong": "#2e7d32", "Moderate": "#9e9d24", "Watch": "#ef6c00", "Weak": "#b0bec5"}
NAVY, TEAL, MUTED = "#17324D", "#247D78", "#667085"
DISCLAIMER = "SCREENING AREA — NOT A PROPOSED CONSTRUCTION BOUNDARY. Public data only; not validated on the ground."


def load_all():
    names = [
        "catchment_boundary", "os_open_rivers", "os_open_roads", "os_open_built_up_areas",
        "rofrs_overall", "habitat_networks", "priority_habitats_inventory",
        "priority_habitat_creation_restoration", "recorded_flood_outlines",
        "sssi", "sac", "scheduled_monuments",
    ]
    layers = {n: gpd.read_file(STAGING, layer=n) for n in names}
    layers["candidates"] = gpd.read_file(LONGLIST)
    return layers


def north_arrow(ax, x=0.94, y=0.90):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.06), xycoords="axes fraction",
                fontsize=11, fontweight="bold", ha="center",
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1.5))


def scale_bar(ax, gdf_crs_units_per_km=1000, length_km=5, x_frac=0.05, y_frac=0.04):
    xlim = ax.get_xlim()
    span = xlim[1] - xlim[0]
    x0 = xlim[0] + x_frac * span
    y0 = ax.get_ylim()[0] + y_frac * (ax.get_ylim()[1] - ax.get_ylim()[0])
    length = length_km * gdf_crs_units_per_km
    ax.plot([x0, x0 + length], [y0, y0], color="black", linewidth=3, solid_capstyle="butt")
    ax.annotate(f"{length_km} km", xy=(x0 + length / 2, y0), xytext=(0, 4),
                textcoords="offset points", ha="center", fontsize=8)


def source_note(fig, text, y=0.012):
    fig.text(0.02, y, text, fontsize=6.5, color=MUTED)


def disclaimer_banner(fig, y=0.975):
    fig.text(0.5, y, DISCLAIMER, fontsize=8.5, color="#b71c1c", fontweight="bold",
              ha="center", va="center",
              bbox=dict(boxstyle="round,pad=0.35", fc="#fff3e0", ec="#b71c1c", lw=1))


def label_places(ax, built_up, min_area_ha=150, force_names=None, fontsize=7.2, view_bounds=None):
    """Label settlement names: anything above the size threshold, plus any
    name explicitly forced in (small villages that matter to this project
    even though they're below the size cutoff), restricted to the current
    view if bounds are given."""
    force_names = force_names or set()
    df = built_up
    if view_bounds is not None:
        minx, miny, maxx, maxy = view_bounds
        df = df.cx[minx:maxx, miny:maxy]
    mask = (df["areahectares"] >= min_area_ha) | (df["name1_text"].isin(force_names))
    for _, row in df[mask].iterrows():
        c = row.geometry.centroid
        ax.annotate(
            row["name1_text"].split(" (")[0], (c.x, c.y), fontsize=fontsize, color="#37474f",
            ha="center", va="top", xytext=(0, -11), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.7),
        )


def catchment_overview(layers):
    fig, ax = plt.subplots(figsize=(9, 11))
    layers["catchment_boundary"].boundary.plot(ax=ax, color="black", linewidth=1.3)
    layers["os_open_rivers"].plot(ax=ax, color="#4a90d9", linewidth=0.5, alpha=0.7)
    layers["os_open_built_up_areas"].plot(ax=ax, color="#cfd8dc", edgecolor="none", alpha=0.9)
    protected = gpd.GeoDataFrame(
        pd.concat([layers["sssi"][["geometry"]], layers["sac"][["geometry"]], layers["scheduled_monuments"][["geometry"]]]),
        crs=layers["sssi"].crs,
    )
    protected.plot(ax=ax, facecolor="none", edgecolor="#c62828", linewidth=0.4, alpha=0.6)

    for band, color in BAND_COLORS.items():
        subset = layers["candidates"][layers["candidates"]["band"] == band]
        subset.plot(ax=ax, color=color, edgecolor="black", linewidth=0.25, alpha=0.85)

    final5 = layers["candidates"][layers["candidates"]["candidate_id"].isin(FINAL_FIVE)]
    final5.boundary.plot(ax=ax, color=NAVY, linewidth=1.8)
    for _, row in final5.iterrows():
        c = row.geometry.centroid
        ax.annotate(row["candidate_id"], (c.x, c.y), fontsize=9, fontweight="bold", color="white",
                    ha="center", va="center",
                    bbox=dict(boxstyle="circle,pad=0.2", fc=NAVY, ec="white", lw=1))

    label_places(ax, layers["os_open_built_up_areas"], min_area_ha=150, force_names=FINAL_FIVE_PLACES)

    patches = [mpatches.Patch(color=c, label=f"{b} candidate") for b, c in BAND_COLORS.items()]
    patches.append(mpatches.Patch(color="#cfd8dc", label="Settlement"))
    patches.append(Line2D([0], [0], color="#4a90d9", lw=1.5, label="Watercourse"))
    patches.append(mpatches.Patch(facecolor="none", edgecolor="#c62828", label="Protected site (SSSI/SAC/Monument)"))
    patches.append(Line2D([0], [0], color=NAVY, lw=2, label="Final five (bold outline)"))
    # Placed in the empty water/whitespace west of the catchment's narrow
    # upper-middle "neck" (near Slaidburn) - the old lower-left position
    # covered the Preston/Fylde peninsula at the bottom of the catchment.
    leg = ax.legend(handles=patches, loc="center left", bbox_to_anchor=(0.0, 0.66),
                     fontsize=9, framealpha=0.95, title="Legend", title_fontsize=9.5)
    leg.get_frame().set_edgecolor("#bbbbbb")
    ax.set_title("Ribble catchment — all 35 candidates, main rivers, settlements, protected sites", fontsize=12, color=NAVY)
    ax.set_axis_off()
    north_arrow(ax)
    scale_bar(ax)
    disclaimer_banner(fig)
    source_note(fig, "Sources: EA NFM Heat Maps, EA RoFRS, Natural England Habitat Networks/SSSI/SAC, Historic England Scheduled Monuments, OS Open Rivers/Roads/Built Up Areas. OGL v3.0.")
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(OUT_DIR / "01_catchment_overview.png", dpi=150, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


def opportunity_gap_map(layers):
    fig, ax = plt.subplots(figsize=(9, 11))
    layers["catchment_boundary"].boundary.plot(ax=ax, color="black", linewidth=1.3)

    cands = layers["candidates"].copy()
    gap = cands["dist_recorded_restoration_km"].clip(upper=3.0)
    sc = ax.scatter(
        cands.geometry.centroid.x, cands.geometry.centroid.y,
        s=(cands["area_ha"].clip(upper=2000) / 6 + 20),
        c=gap, cmap="RdYlGn", edgecolor="black", linewidth=0.4, vmin=0, vmax=3, zorder=3,
    )
    layers["priority_habitat_creation_restoration"].plot(ax=ax, marker="x", color="#555555", markersize=25, zorder=2)
    label_places(ax, layers["os_open_built_up_areas"], min_area_ha=250, fontsize=7)

    cbar = fig.colorbar(sc, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Distance to nearest recorded restoration project (km, capped at 3km)\nGreen = far from recorded activity (opportunity gap)  |  Red = already worked nearby", fontsize=8)

    legend_handles = [Line2D([0], [0], marker="x", color="#555555", label="Recorded restoration project", linestyle="None", markersize=7)]
    leg = ax.legend(handles=legend_handles, loc="lower left", fontsize=9, framealpha=0.95)
    leg.get_frame().set_edgecolor("#bbbbbb")

    ax.set_title("Opportunity-gap map — modelled NFM potential vs. recorded activity", fontsize=12, color=NAVY)
    ax.set_axis_off()
    north_arrow(ax)
    scale_bar(ax)
    disclaimer_banner(fig)
    source_note(fig, "Point size = candidate area (capped at 2000ha for display). Sources: EA NFM Heat Maps, EA Priority Habitat Creation and Restoration. OGL v3.0.")
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(OUT_DIR / "02_opportunity_gap.png", dpi=150, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


def site_map(layers, candidate_id):
    cands = layers["candidates"]
    site = cands[cands["candidate_id"] == candidate_id].iloc[0]
    geom = site.geometry
    buf = geom.buffer(1500)  # 1.5km context buffer
    minx, miny, maxx, maxy = buf.bounds

    fig = plt.figure(figsize=(8, 6.6))
    # Bottom margin (0.16) is deliberately generous - the two-row fig.legend
    # below is anchored at figure y=0 and was overlapping the last ~10% of
    # map content when this was 0.06.
    ax = fig.add_axes([0.03, 0.16, 0.94, 0.7])

    def clip_to_view(gdf):
        return gdf.cx[minx:maxx, miny:maxy]

    clip_to_view(layers["priority_habitats_inventory"]).plot(ax=ax, color="#c8e6c9", edgecolor="none", alpha=0.6)
    clip_to_view(layers["habitat_networks"]).plot(ax=ax, color="#81c784", edgecolor="none", alpha=0.4)
    clip_to_view(layers["rofrs_overall"]).plot(ax=ax, color="#90caf9", edgecolor="none", alpha=0.55)
    clip_to_view(layers["os_open_built_up_areas"]).plot(ax=ax, color="#cfd8dc", edgecolor="none", alpha=0.9)
    protected = gpd.GeoDataFrame(
        pd.concat([layers["sssi"][["geometry"]], layers["sac"][["geometry"]], layers["scheduled_monuments"][["geometry"]]]),
        crs=layers["sssi"].crs,
    )
    clip_to_view(protected).plot(ax=ax, facecolor="none", edgecolor="#c62828", hatch="///", linewidth=1.1, alpha=0.9)
    clip_to_view(layers["os_open_rivers"]).plot(ax=ax, color="#1565c0", linewidth=0.9)
    clip_to_view(layers["os_open_roads"]).plot(ax=ax, color="#8d6e63", linewidth=0.5, alpha=0.8)

    gpd.GeoSeries([geom]).boundary.plot(ax=ax, color=NAVY, linewidth=2.2)
    gpd.GeoSeries([geom]).plot(ax=ax, color=NAVY, alpha=0.15)

    # label every settlement visible in this tight view, regardless of size
    view_bua = layers["os_open_built_up_areas"].cx[minx:maxx, miny:maxy]
    for _, row in view_bua.iterrows():
        c = row.geometry.centroid
        ax.annotate(row["name1_text"].split(" (")[0], (c.x, c.y), fontsize=8, color="#37474f",
                    fontweight="bold", ha="center", va="bottom", xytext=(0, 3), textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="#37474f", lw=0.4, alpha=0.85))

    restoration_pts = clip_to_view(layers["priority_habitat_creation_restoration"])
    if len(restoration_pts):
        restoration_pts.plot(ax=ax, marker="x", color="#d32f2f", markersize=40, zorder=5)

    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_axis_off()
    ax.set_title(f"Candidate site {candidate_id}", fontsize=13, color=NAVY, fontweight="bold", loc="left")
    north_arrow(ax, x=0.92, y=0.88)
    scale_bar(ax, length_km=1, y_frac=0.03)

    # Locator inset
    inset = fig.add_axes([0.74, 0.66, 0.22, 0.22])
    layers["catchment_boundary"].boundary.plot(ax=inset, color="black", linewidth=0.6)
    cands.plot(ax=inset, color="#cccccc", edgecolor="none")
    gpd.GeoSeries([geom]).plot(ax=inset, color=NAVY)
    inset.set_axis_off()
    inset.set_title("Location in catchment", fontsize=6.5)

    legend_patches = [
        mpatches.Patch(color="#c8e6c9", label="Existing priority habitat"),
        mpatches.Patch(color="#81c784", label="Habitat network opportunity"),
        mpatches.Patch(color="#90caf9", label="Flood risk extent (RoFRS, context only)"),
        mpatches.Patch(color="#cfd8dc", label="Settlement"),
        mpatches.Patch(facecolor="none", edgecolor="#c62828", hatch="///", label="Protected site (SSSI/SAC/Monument)"),
        Line2D([0], [0], color="#1565c0", lw=1.5, label="Watercourse"),
        Line2D([0], [0], color="#8d6e63", lw=1, label="Road"),
        Line2D([0], [0], marker="x", color="#d32f2f", label="Recorded restoration project", linestyle="None"),
    ]
    leg = fig.legend(handles=legend_patches, loc="lower center", ncol=2, fontsize=8, frameon=True,
                      framealpha=0.95, bbox_to_anchor=(0.5, 0.0), edgecolor="#bbbbbb")

    flag_bit = "  |  PROTECTED SITE OVERLAP" if site.get("protected_site_flag") not in (None, "None", "") and not pd.isna(site.get("protected_site_flag")) else ""
    fig.text(0.02, 0.94, f"Area: {site['area_ha']:.0f} ha  |  Type: {site['site_type']}  |  Band: {site['band']}  |  Flood-risk context: {site['data_confidence']}{flag_bit}", fontsize=8, color=MUTED)
    disclaimer_banner(fig, y=0.985)

    fig.savefig(OUT_DIR / f"site_{candidate_id}.png", dpi=150, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


def outreach_map(layers):
    """A compact, simplified locator map for the one-page outreach summary -
    just the final five and orientation context, not all 35 candidates. Sized
    to actually fit on one page alongside the rest of that document, which the
    full 35-candidate overview (with its large legend) does not."""
    fig, ax = plt.subplots(figsize=(6, 6.6))
    layers["catchment_boundary"].boundary.plot(ax=ax, color="black", linewidth=1.1)
    layers["os_open_rivers"].plot(ax=ax, color="#4a90d9", linewidth=0.4, alpha=0.6)
    layers["os_open_built_up_areas"].plot(ax=ax, color="#cfd8dc", edgecolor="none", alpha=0.9)

    final5 = layers["candidates"][layers["candidates"]["candidate_id"].isin(FINAL_FIVE)]
    final5.plot(ax=ax, color=NAVY, edgecolor="white", linewidth=0.6, alpha=0.85)
    for _, row in final5.iterrows():
        c = row.geometry.centroid
        ax.annotate(row["candidate_id"], (c.x, c.y), fontsize=8, fontweight="bold", color="white",
                    ha="center", va="center",
                    bbox=dict(boxstyle="circle,pad=0.18", fc=NAVY, ec="white", lw=1))

    label_places(ax, layers["os_open_built_up_areas"], min_area_ha=300, force_names=FINAL_FIVE_PLACES, fontsize=6.5)

    ax.set_axis_off()
    north_arrow(ax, x=0.9, y=0.93)
    scale_bar(ax, length_km=5, y_frac=0.03)
    fig.text(0.5, 0.975, "The five candidate sites in context", fontsize=12, color=NAVY, ha="center")
    fig.text(0.5, 0.955, "Navy = candidate site. Screening area, not a construction boundary.",
              fontsize=7.5, color="#b71c1c", fontweight="bold", ha="center")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "03_outreach_locator.png", dpi=150, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)


def main():
    layers = load_all()
    print("Building catchment overview...")
    catchment_overview(layers)
    print("Building opportunity-gap map...")
    opportunity_gap_map(layers)
    for cid in FINAL_FIVE:
        print(f"Building site map for {cid}...")
        site_map(layers, cid)
    print("Building outreach locator map...")
    outreach_map(layers)
    print(f"\nAll maps written to {OUT_DIR}")


if __name__ == "__main__":
    main()
