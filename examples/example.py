from __future__ import annotations

import os
from pathlib import Path

from gmaprium import Choropleth, Circle, Draw, GeoJson, HeatMap, LayerControl, Map, Marker, Polygon, Polyline


api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "YOUR_GOOGLE_MAPS_API_KEY")
output_path = Path(__file__).with_name("example.html")

m = Map(
    location=[35.6812, 139.7671],
    zoom_start=12,
    api_key=api_key,
    map_type="roadmap",
    height="600px",
)

Marker(
    [35.6812, 139.7671],
    popup="Tokyo Station",
    tooltip="Tokyo Station",
    name="Markers",
).add_to(m)

Polyline(
    [[35.6812, 139.7671], [35.6895, 139.6917]],
    color="#0b57d0",
    weight=4,
    name="Route",
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

Choropleth(
    geo_data={
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": "central"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [139.760, 35.675],
                            [139.785, 35.675],
                            [139.785, 35.695],
                            [139.760, 35.695],
                            [139.760, 35.675],
                        ]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {"id": "east"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [139.790, 35.675],
                            [139.815, 35.675],
                            [139.815, 35.695],
                            [139.790, 35.695],
                            [139.790, 35.675],
                        ]
                    ],
                },
            },
        ],
    },
    data={"central": 32, "east": 74},
    key_on="feature.properties.id",
    bins=[0, 50, 100],
    fill_color="YlOrRd",
    name="Choropleth",
    legend_name="Sample values",
    highlight=True,
).add_to(m)

HeatMap(
    [
        [35.6812, 139.7671, 1.0],
        [35.6825, 139.7685, 0.95],
        [35.6840, 139.7700, 0.9],
        [35.6895, 139.6917, 0.85],
        [35.6920, 139.6940, 0.8],
        [35.6586, 139.7454, 0.8],
        [35.6600, 139.7480, 0.75],
        {"location": [35.7101, 139.8107], "weight": 0.85},
        {"location": [35.7085, 139.8088], "weight": 0.8},
    ],
    name="Heat",
    max_zoom=14,
).add_to(m)

Draw(export=True, filename="drawn.geojson", position="topleft").add_to(m)

LayerControl().add_to(m)

m.save(output_path)
print(f"Wrote {output_path}")
