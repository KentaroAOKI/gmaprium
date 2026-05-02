from __future__ import annotations

import os
from pathlib import Path

import folium
from folium import Circle, GeoJson, Polygon
from folium.plugins import HeatMap

from gmaprium import add_google_tiles


api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "YOUR_GOOGLE_MAPS_API_KEY")
output_path = Path(__file__).with_name("folium_extension.html")

m = folium.Map(location=[35.6812, 139.7671], zoom_start=12, tiles=None)

add_google_tiles(
    m,
    api_key=api_key,
    map_type="roadmap",
    name="Google Roadmap",
)
add_google_tiles(
    m,
    api_key=api_key,
    map_type="satellite",
    name="Google Satellite",
    show=False,
)

folium.Marker(
    [35.6812, 139.7671],
    popup="Tokyo Station",
    tooltip="Tokyo Station",
).add_to(m)

Polygon(
    [[35.7000, 139.7000], [35.7000, 139.8200], [35.6200, 139.8200], [35.6200, 139.7000]],
    color="#188038",
    fill_color="#34a853",
    fill_opacity=0.18,
    name="Area",
).add_to(m)

Circle(
    [35.6895, 139.6917],
    radius=700,
    color="#d93025",
    fill_color="#f28b82",
    fill_opacity=0.25,
    name="Circle",
).add_to(m)

GeoJson(
    {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Sample GeoJSON"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [139.735, 35.675],
                            [139.755, 35.675],
                            [139.755, 35.690],
                            [139.735, 35.690],
                            [139.735, 35.675],
                        ]
                    ],
                },
            }
        ],
    },
    name="GeoJSON",
    style_function=lambda feature: {
        "fillColor": "#fbbc04",
        "fillOpacity": 0.3,
        "strokeColor": "#f9ab00",
        "strokeWeight": 2,
    },
).add_to(m)

HeatMap(
    [
        [35.6812, 139.7671],
        [35.6825, 139.7685],
        [35.6840, 139.7700],
        [35.6895, 139.6917],
        [35.6920, 139.6940],
        [35.6586, 139.7454],
        [35.6600, 139.7480],
    ],
    name="Heat",
).add_to(m)

folium.LayerControl().add_to(m)

m.save(output_path)
print(f"Wrote {output_path}")
