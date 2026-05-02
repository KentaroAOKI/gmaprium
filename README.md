# gmaprium

Folium-style Python helpers for rendering Google Maps HTML.

gmaprium can be used to create standalone HTML maps, display maps in Jupyter Notebook, add Google tile layers to existing Folium maps, and embed maps in Streamlit apps.

## Installation

```bash
pip install gmaprium
```

## Usage

```python
from gmaprium import GeoJson, HeatMap, LayerControl, Map, Marker, Polygon

m = Map(
    location=[35.6812, 139.7671],
    zoom_start=12,
    api_key="YOUR_GOOGLE_MAPS_API_KEY",
    map_type="roadmap",
    height="500px",
)

Marker([35.6812, 139.7671], popup="Tokyo Station", tooltip="Tokyo", name="Stations").add_to(m)
Polygon(
    [[35.70, 139.70], [35.70, 139.82], [35.62, 139.82], [35.62, 139.70]],
    name="Area",
).add_to(m)
HeatMap([[35.6812, 139.7671, 2], [35.6895, 139.6917, 1]], name="Heat").add_to(m)
LayerControl().add_to(m)

# Full HTML document.
m.save("map.html")

# Embeddable HTML fragment for web apps.
html = m.render_fragment()
```

You can also pass the API key with the `GOOGLE_MAPS_API_KEY` environment variable.

Markers use Google's `AdvancedMarkerElement`. If you add markers without passing `map_id=...`, the renderer uses Google's `DEMO_MAP_ID` for local testing.

## Supported Elements

- `Map`
- `Marker`
- `Polyline`
- `Polygon`
- `Circle`
- `GeoJson`
- `HeatMap`
- `LayerControl`

`GeoJson` accepts GeoJSON dictionaries, JSON file paths, objects with `__geo_interface__`, and GeoPandas-like objects with `to_json()`.

`HeatMap` uses a canvas overlay instead of Google's deprecated JavaScript `HeatmapLayer`.
It ports the Leaflet.heat/simpleheat rendering model, including `radius`, `blur`, `min_opacity`, `max_zoom`, `max_value`, and `gradient`.
The defaults match Leaflet.heat/simpleheat on a typical OSM map: `radius=25`, `blur=15`, `min_opacity=0.05`, `max_zoom=18`, `max_value=1.0`, and the blue-cyan-lime-yellow-red gradient.
Lower zoom levels are intentionally faded by Leaflet.heat's `max_zoom - zoom` intensity scale. Set `max_zoom` closer to your initial zoom if the heat fades too quickly.

The legacy `google_tiles_url()` and `add_google_tiles()` helpers are still available for projects that want to add Google tile URLs to an existing Folium map.

## Notebook

In Jupyter Notebook, display the map by returning the `Map` object as the last expression in a cell.

```python
import os

from gmaprium import HeatMap, LayerControl, Map, Marker

os.environ["GOOGLE_MAPS_API_KEY"] = "your-api-key"

m = Map(location=[35.6812, 139.7671], zoom_start=12, height="500px")
Marker([35.6812, 139.7671], popup="Tokyo Station", name="Markers").add_to(m)
HeatMap([[35.6812, 139.7671, 1.0]], name="Heat", max_zoom=14).add_to(m)
LayerControl().add_to(m)

m
```

You can also display explicitly:

```python
from IPython.display import HTML, display

display(HTML(m.render_fragment()))
```

The notebook example is available at `examples/example.ipynb`.

## Folium Extension

If you already use Folium, add Google tile layers to a `folium.Map` with `add_google_tiles()`.

```python
import folium

from gmaprium import add_google_tiles

m = folium.Map(location=[35.6812, 139.7671], zoom_start=12, tiles=None)
add_google_tiles(m, api_key="your-api-key", map_type="roadmap", name="Google Roadmap")
add_google_tiles(m, api_key="your-api-key", map_type="satellite", name="Google Satellite", show=False)

folium.LayerControl().add_to(m)
m.save("folium_google_tiles.html")
```

This Folium extension only adds Google tile layers. It does not enable the Google Maps JavaScript API renderer or gmaprium's `HeatMap`.

The Folium example is available at `examples/folium_extension.py`.

## Streamlit

Use `st_google_map()` to render a `gmaprium.Map` inside a Streamlit app.

```python
import os

import streamlit as st

from gmaprium import Map, Marker, st_google_map

api_key = os.environ["GOOGLE_MAPS_API_KEY"]

m = Map(location=[35.6812, 139.7671], zoom_start=12, api_key=api_key, height="600px")
Marker([35.6812, 139.7671], popup="Tokyo Station").add_to(m)

st_google_map(m)
```

Install the optional dependency and run the example app:

```bash
python -m pip install -e ".[dev,streamlit]"
export GOOGLE_MAPS_API_KEY="your-api-key"
streamlit run examples/streamlit_app.py
```

The Streamlit example is available at `examples/streamlit_app.py`.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```
