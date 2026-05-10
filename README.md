# gmaprium

Folium-style Python helpers for rendering Google Maps HTML.

gmaprium can be used to create standalone HTML maps, display maps in Jupyter Notebook, add Google tile layers to existing Folium maps, and embed maps in Streamlit apps.

## Installation

```bash
pip install gmaprium
```

## Usage

```python
from gmaprium import Choropleth, Draw, GeoJson, HeatMap, LayerControl, Map, Marker, Polygon

m = Map(
    location=[35.6812, 139.7671],
    zoom_start=12,
    api_key="YOUR_GOOGLE_MAPS_API_KEY",
    map_type="roadmap",
    height="500px",
    fullscreen_control=False,
    street_view_control=False,
)

Marker([35.6812, 139.7671], popup="Tokyo Station", tooltip="Tokyo", name="Stations").add_to(m)
Polygon(
    [[35.70, 139.70], [35.70, 139.82], [35.62, 139.82], [35.62, 139.70]],
    name="Area",
).add_to(m)
Choropleth(
    geo_data={
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": "central"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[139.735, 35.675], [139.755, 35.675], [139.755, 35.690], [139.735, 35.690], [139.735, 35.675]]],
                },
            }
        ],
    },
    data={"central": 42},
    key_on="feature.properties.id",
    name="Choropleth",
    legend_name="Sample values",
).add_to(m)
HeatMap([[35.6812, 139.7671, 2], [35.6895, 139.6917, 1]], name="Heat").add_to(m)
Draw(export=True, filename="drawn.geojson").add_to(m)
LayerControl().add_to(m)

# Full HTML document.
m.save("map.html")

# Embeddable HTML fragment for web apps.
html = m.render_fragment()
```

You can also pass the API key with the `GOOGLE_MAPS_API_KEY` environment variable.

Set `fullscreen_control=True` or `fullscreen_control=False` to control Google Maps SDK's built-in fullscreen button.
Set `street_view_control=True` or `street_view_control=False` to control the built-in Street View button.

Markers use Google's `AdvancedMarkerElement`. If you add markers without passing `map_id=...`, the renderer uses Google's `DEMO_MAP_ID` for local testing.

## Supported Elements

- `Map`
- `Marker`
- `Polyline`
- `Polygon`
- `Circle`
- `GeoJson`
- `Choropleth`
- `Draw`
- `HeatMap`
- `LayerControl`

`GeoJson` accepts GeoJSON dictionaries, JSON file paths, objects with `__geo_interface__`, and GeoPandas-like objects with `to_json()`.

`Choropleth` accepts GeoJSON plus Folium-style `data`, `columns`, `key_on`, `bins`, fill/stroke styling, missing-value styling, highlight, and legend options.
It renders as a Google Maps `Data` layer and can be toggled with `LayerControl`.

`Draw` adds a Folium-style drawing toolbar for markers, polylines, polygons, rectangles, and circles.
Set `export=True` to let users download drawn features as GeoJSON.
Use `draw_options` to show or hide specific drawing tools:

```python
Draw(
    draw_options={
        "marker": True,
        "polyline": False,
        "polygon": True,
        "rectangle": False,
        "circle": True,
    },
    export=True,
).add_to(m)
```

`HeatMap` uses a canvas overlay instead of Google's deprecated JavaScript `HeatmapLayer`.
It ports the Leaflet.heat/simpleheat rendering model, including `radius`, `blur`, `min_opacity`, `max_zoom`, `max_value`, and `gradient`.
The defaults match Leaflet.heat/simpleheat on a typical OSM map: `radius=25`, `blur=15`, `min_opacity=0.05`, `max_zoom=18`, `max_value=1.0`, and the blue-cyan-lime-yellow-red gradient.
Lower zoom levels are intentionally faded by Leaflet.heat's `max_zoom - zoom` intensity scale. Set `max_zoom` closer to your initial zoom if the heat fades too quickly.

## Configuration Reference

### Map

| Option | Default | Description |
| --- | --- | --- |
| `location` | required | Initial map center as `[lat, lng]`. |
| `zoom_start` | `10` | Initial Google Maps zoom level. |
| `api_key` | `None` | Google Maps API key. If omitted, `GOOGLE_MAPS_API_KEY` is used. |
| `map_type` | `"roadmap"` | One of `"roadmap"`, `"satellite"`, `"hybrid"`, or `"terrain"`. |
| `width` | `"100%"` | CSS width for HTML and notebook rendering. Integers are treated as pixels. |
| `height` | `"100%"` | CSS height for HTML and notebook rendering. Integers are treated as pixels. |
| `map_id` | `None` | Google Maps Map ID. Markers and Draw use `DEMO_MAP_ID` if needed and no ID is supplied. |
| `fullscreen_control` | `None` | Enable or disable Google Maps fullscreen control. `None` leaves the SDK default. |
| `street_view_control` | `None` | Enable or disable Google Maps Street View control. `None` leaves the SDK default. |
| `options` | `{}` | Extra raw Google Maps JavaScript `MapOptions`. |

### Vector Elements

| Element | Options |
| --- | --- |
| `Marker` | `location`, `popup`, `tooltip`, `icon`, `draggable`, `name` |
| `Polyline` | `locations`, `color`, `weight`, `opacity`, `name` |
| `Polygon` | `locations`, `color`, `fill_color`, `fill_opacity`, `weight`, `name` |
| `Circle` | `location`, `radius`, `color`, `fill_color`, `fill_opacity`, `weight`, `name` |
| `GeoJson` | `data`, `name`, `style_function` |

`name` makes the element available in `LayerControl`. `style_function` is called with a sample GeoJSON feature and should return Google Maps style options such as `fillColor`, `fillOpacity`, `strokeColor`, and `strokeWeight`.

### Draw

| Option | Default | Description |
| --- | --- | --- |
| `export` | `False` | Show the `Export` button when `True`. |
| `filename` | `"data.geojson"` | Download filename used by the `Export` button. |
| `position` | `"topleft"` | Toolbar position: `"topleft"`, `"topright"`, `"bottomleft"`, or `"bottomright"`. |
| `show_geometry_on_click` | `True` | Show drawn feature GeoJSON in an alert when a completed drawing is clicked. |
| `draw_options` | `{}` | Drawing tool visibility and style options. |
| `feature_group` | `None` | Reserved for Folium compatibility; currently unsupported. |
| `edit_options` | `{}` | Reserved for Folium compatibility. |
| `on` | `{}` | Reserved for Folium-style event compatibility. |

`draw_options` supports these visibility keys: `marker`, `polyline`, `polygon`, `rectangle`, and `circle`. Set a key to `False` to hide that drawing tool.

```python
Draw(draw_options={"marker": True, "polyline": False, "circle": False}).add_to(m)
```

The same dictionary also accepts style keys used for newly drawn shapes: `strokeColor`, `strokeOpacity`, `strokeWeight`, `fillColor`, and `fillOpacity`.

### Choropleth

| Option | Default | Description |
| --- | --- | --- |
| `geo_data` | required | GeoJSON dict, path, `__geo_interface__` object, or GeoPandas-like object. |
| `data` | `None` | Mapping, sequence of pairs, Series-like, or DataFrame-like data to join. |
| `columns` | `None` | Key/value column names for DataFrame-like data. |
| `key_on` | `None` | GeoJSON feature path such as `"feature.properties.id"`. |
| `bins` | `6` | Number of bins or explicit bin edges. |
| `fill_color` | `"Blues"` when data is supplied | ColorBrewer palette name, or a CSS color when no joined data is supplied. |
| `nan_fill_color` | `"black"` | Fill color for missing or non-numeric values. |
| `fill_opacity` | `0.6` | Fill opacity for matched values. |
| `nan_fill_opacity` | `fill_opacity` | Fill opacity for missing values. |
| `line_color` | `"black"` | Boundary color. |
| `line_weight` | `1` | Boundary width. |
| `line_opacity` | `1` | Boundary opacity. |
| `name` | `None` | Layer name used by `LayerControl`. |
| `legend_name` | `""` | Caption for the generated legend. |
| `highlight` | `False` | Highlight features on hover. |
| `use_jenks` | `False` | Use Jenks natural breaks. Requires `jenkspy`. |

`topojson` is not supported yet. `threshold_scale` is accepted as a Folium-compatible alias for `bins`.

### HeatMap

| Option | Default | Description |
| --- | --- | --- |
| `data` | required | Points as `[lat, lng]`, `[lat, lng, weight]`, or `{"location": [lat, lng], "weight": n}`. |
| `name` | `None` | Layer name used by `LayerControl`. |
| `radius` | `25` | Point radius in pixels. |
| `blur` | `15` | Blur radius in pixels. |
| `min_opacity` | `0.05` | Minimum alpha for rendered points. |
| `max_zoom` | `18` | Leaflet.heat-style zoom intensity reference. |
| `max_value` | `1.0` | Weight value that maps to full intensity. |
| `gradient` | simpleheat gradient | Mapping of stop positions to CSS colors. |
| `opacity` | `1.0` | Reserved overall layer opacity option. |
| `intensity` | `1.0` | Reserved intensity multiplier option. |
| `threshold` | `0.03` | Reserved low-alpha threshold option. |
| `scale_radius_with_zoom` | `False` | Reserved option for zoom-scaled radius. |
| `min_radius` | `6` | Minimum radius when zoom scaling is enabled. |
| `max_radius` | `240` | Maximum radius when zoom scaling is enabled. |

### Streamlit

| Option | Default | Description |
| --- | --- | --- |
| `map_obj` | required | `gmaprium.Map` instance to render. |
| `height` | map height in pixels | Component height. If omitted, pixel values from `Map.height` are used. |
| `width` | `None` | Component width. `None` lets Streamlit choose the width. |
| `scrolling` | `False` | Enable iframe scrolling. |
| `returned_objects` | `["all_drawings", "last_active_drawing"]` | Draw result fields to return. Use `[]` to avoid reruns from Draw updates. |
| `key` | `None` | Stable Streamlit component key. Recommended when using `Draw`. |
| `default` | generated from `returned_objects` | Initial return value before any Draw action. |

`st_gmaprium()` returns a dictionary with `all_drawings` and `last_active_drawing` by default. Both values use GeoJSON Feature dictionaries.

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

Use `st_gmaprium()` to render a `gmaprium.Map` inside a Streamlit app.
Draw results are returned in a `st_folium`-style dictionary with `all_drawings` and `last_active_drawing`.

```python
import os

import streamlit as st

from gmaprium import Draw, Map, Marker, st_gmaprium

api_key = os.environ["GOOGLE_MAPS_API_KEY"]

m = Map(location=[35.6812, 139.7671], zoom_start=12, api_key=api_key, height="600px")
Marker([35.6812, 139.7671], popup="Tokyo Station").add_to(m)
Draw(export=True).add_to(m)

draw_result = st_gmaprium(m, key="main-map")
st.json(draw_result)
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
