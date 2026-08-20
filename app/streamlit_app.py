"""Interactive explorer for the Ribble catchment NFM candidate screening.

Combines the DuckDB tabular database (filters, table, metrics) with the
GeoPackage's geometry (the interactive map) - the two outputs from Week 6
working together rather than duplicating either one.

Run with:
    streamlit run app/streamlit_app.py
"""
from pathlib import Path

import duckdb
import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "processed" / "ribble_nfm.duckdb"
LONGLIST_GPKG = ROOT / "data" / "processed" / "candidate_longlist.gpkg"
STAGING_GPKG = ROOT / "data" / "processed" / "ribble_nfm_staging.gpkg"

FINAL_FIVE = ["C16", "C21", "C14", "C22", "C23"]
BAND_COLORS = {"Strong": "#2e7d32", "Moderate": "#9e9d24", "Watch": "#ef6c00", "Weak": "#b0bec5"}

st.set_page_config(page_title="Ribble NFM Candidate Explorer", layout="wide")


@st.cache_data
def load_summary():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute("SELECT * FROM candidate_summary").df()
    con.close()
    return df


@st.cache_data
def load_geometries():
    gdf = gpd.read_file(LONGLIST_GPKG)[["candidate_id", "geometry"]]
    return gdf.to_crs("EPSG:4326")


@st.cache_data
def load_context():
    catchment = gpd.read_file(STAGING_GPKG, layer="catchment_boundary").to_crs("EPSG:4326")
    settlements = gpd.read_file(STAGING_GPKG, layer="os_open_built_up_areas").to_crs("EPSG:4326")
    return catchment, settlements


def disclaimer():
    st.markdown(
        """
        <div style="background:#FDECEA;border:1.5px solid #B71C1C;border-radius:6px;
                    padding:10px 16px;margin-bottom:14px;">
          <b style="color:#B71C1C;">SCREENING AREAS — NOT PROPOSED CONSTRUCTION BOUNDARIES.</b>
          <span style="color:#243142;"> Public-data screening only, not yet validated on the ground.
          See docs/screening_methodology.md for what each score does and doesn't claim.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_map(filtered, geoms, catchment, settlements):
    merged = geoms.merge(filtered, on="candidate_id", how="inner")
    center = [53.86, -2.45]
    m = folium.Map(location=center, zoom_start=10, tiles="cartodbpositron")

    folium.GeoJson(
        catchment,
        style_function=lambda f: {"color": "#17324D", "weight": 1.5, "fillOpacity": 0},
        name="Catchment boundary",
    ).add_to(m)

    folium.GeoJson(
        settlements,
        style_function=lambda f: {"color": "none", "fillColor": "#cfd8dc", "fillOpacity": 0.5, "weight": 0},
        name="Settlements",
    ).add_to(m)

    for _, row in merged.iterrows():
        color = BAND_COLORS.get(row["band"], "#999999")
        is_final = row["candidate_id"] in FINAL_FIVE
        flag = row["protected_site_flag"]
        flag_txt = flag if flag and flag != "None" and pd.notna(flag) else "None"
        popup_html = (
            f"<b>{row['candidate_id']}</b> ({row['site_type']})<br>"
            f"Nearest place: {row['nearest_place']} ({row['nearest_place_dist_km']:.2f}km)<br>"
            f"Rank {int(row['rank'])} of 35 &middot; Band: {row['band']} &middot; Flood-risk context: {row['data_confidence']}<br>"
            f"Area: {row['area_ha']:.0f} ha &middot; Composite score: {row['composite_score']:.3f}<br>"
            f"Protected site flag: {flag_txt}<br>"
            f"<i>{row['suggested_next_investigation']}</i>"
        )
        folium.GeoJson(
            row["geometry"],
            style_function=lambda f, color=color, is_final=is_final: {
                "fillColor": color,
                "color": "#17324D" if is_final else "#333333",
                "weight": 2.2 if is_final else 0.6,
                "fillOpacity": 0.75 if is_final else 0.55,
            },
            tooltip=f"{row['candidate_id']} — {row['band']}" + (" (final five)" if is_final else ""),
            popup=folium.Popup(popup_html, max_width=300),
        ).add_to(m)

    folium.LayerControl().add_to(m)
    return m


def main():
    st.title("Ribble Catchment — NFM Candidate Explorer")
    st.caption("Interactive companion to the DuckDB query database and GeoPackage — filter the table, see it on the map.")
    disclaimer()

    summary = load_summary()
    geoms = load_geometries()
    catchment, settlements = load_context()

    st.sidebar.header("Filters")
    bands = st.sidebar.multiselect("Band", options=["Strong", "Moderate", "Watch", "Weak"],
                                    default=["Strong", "Moderate", "Watch", "Weak"])
    confidence = st.sidebar.radio(
        "Flood-risk context coverage", options=["All", "High", "Low only"], index=0,
        help="Whether the contextual RoFRS layer has coverage for a candidate. Not a scored factor - doesn't affect rank or composite score.",
    )
    site_type = st.sidebar.radio("Site type", options=["All", "Candidate Site", "Investigation Zone"], index=0)
    protected = st.sidebar.radio("Protected-site overlap", options=["All", "Flagged only", "Clean only"], index=0)
    final_five_only = st.sidebar.checkbox("Final five only", value=False)
    area_range = st.sidebar.slider("Area (ha)", 0, int(summary["area_ha"].max()) + 1,
                                    (0, int(summary["area_ha"].max()) + 1))
    place_search = st.sidebar.text_input("Nearest place contains")

    filtered = summary[summary["band"].isin(bands)]
    if confidence == "High":
        filtered = filtered[filtered["data_confidence"] == "High"]
    elif confidence == "Low only":
        filtered = filtered[filtered["data_confidence"] != "High"]
    if site_type != "All":
        filtered = filtered[filtered["site_type"] == site_type]
    if protected == "Flagged only":
        filtered = filtered[filtered["protected_site_flag"].notna() & (filtered["protected_site_flag"] != "None")]
    elif protected == "Clean only":
        filtered = filtered[filtered["protected_site_flag"].isna() | (filtered["protected_site_flag"] == "None")]
    if final_five_only:
        filtered = filtered[filtered["candidate_id"].isin(FINAL_FIVE)]
    filtered = filtered[(filtered["area_ha"] >= area_range[0]) & (filtered["area_ha"] <= area_range[1])]
    if place_search:
        filtered = filtered[filtered["nearest_place"].str.contains(place_search, case=False, na=False)]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Candidates shown", len(filtered))
    c2.metric("Strong band", int((filtered["band"] == "Strong").sum()))
    c3.metric("Protected-site flags", int((filtered["protected_site_flag"].notna() & (filtered["protected_site_flag"] != "None")).sum()))
    c4.metric("Avg. composite score", f"{filtered['composite_score'].mean():.3f}" if len(filtered) else "-")

    map_col, table_col = st.columns([3, 2])
    with map_col:
        st.subheader("Map")
        if len(filtered):
            m = build_map(filtered, geoms, catchment, settlements)
            st_folium(m, width=None, height=560, returned_objects=[])
        else:
            st.info("No candidates match the current filters.")

    with table_col:
        st.subheader(f"Candidates ({len(filtered)})")
        display_cols = ["candidate_id", "nearest_place", "rank", "band", "data_confidence",
                         "area_ha", "composite_score", "protected_site_flag"]
        st.dataframe(filtered[display_cols].sort_values("rank"), hide_index=True, height=520)
        st.download_button(
            "Download filtered results (CSV)",
            filtered.to_csv(index=False).encode("utf-8"),
            file_name="ribble_nfm_filtered_candidates.csv",
            mime="text/csv",
        )

    st.divider()
    with st.expander("Suggested next investigation, for the currently filtered candidates"):
        st.dataframe(
            filtered[["candidate_id", "suggested_next_investigation"]].sort_values("candidate_id"),
            hide_index=True,
        )

    st.caption(
        "Sources: EA NFM Heat Maps, EA RoFRS, EA Recorded Flood Outlines, EA Priority Habitat Creation and "
        "Restoration, Natural England Habitat Networks/Priority Habitats Inventory/SSSI/SAC, Historic England "
        "Scheduled Monuments, OS Open Rivers/Roads/Built Up Areas. Open Government Licence v3.0. "
        "See docs/provenance_manifest.csv for full detail."
    )


if __name__ == "__main__":
    main()
