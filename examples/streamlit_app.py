from __future__ import annotations

import os
import random

import streamlit as st

from gmaprium import HeatMap, LayerControl, Map, Marker, st_google_map


st.set_page_config(page_title="gmaprium Streamlit example", layout="wide")
st.title("gmaprium")


@st.cache_data
def generate_japan_heatmap_points(count: int = 10_000, seed: int = 42) -> list[list[float]]:
    rng = random.Random(seed)
    return [
        [
            rng.uniform(24.0, 46.0),
            rng.uniform(123.0, 146.0),
            rng.uniform(0.6, 0.7),
        ]
        for _ in range(count)
    ]

api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
if not api_key:
    st.warning("Set GOOGLE_MAPS_API_KEY before running this example.")
    st.stop()

m = Map(
    location=[36.2048, 138.2529],
    zoom_start=5,
    api_key=api_key,
    height="650px",
)

Marker([35.6812, 139.7671], popup="Tokyo Station", tooltip="Tokyo Station", name="Markers").add_to(m)
HeatMap(
    generate_japan_heatmap_points(),
    name="Heat",
    max_zoom=7,
).add_to(m)
LayerControl().add_to(m)

st_google_map(m)
