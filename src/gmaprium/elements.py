"""Folium-style map elements for Google Maps output."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Iterable, Sequence


Location = Sequence[float]
_MAP_TYPES = {"roadmap", "satellite", "hybrid", "terrain"}
_DEMO_MAP_ID = "DEMO_MAP_ID"
_CHOROPLETH_STYLE_PROPERTY = "__gmaprium_choropleth_style"
_COLOR_BREWER = {
    "Blues": ["#f7fbff", "#deebf7", "#c6dbef", "#9ecae1", "#6baed6", "#4292c6", "#2171b5", "#08519c", "#08306b"],
    "BuGn": ["#f7fcfd", "#e5f5f9", "#ccece6", "#99d8c9", "#66c2a4", "#41ae76", "#238b45", "#006d2c", "#00441b"],
    "BuPu": ["#f7fcfd", "#e0ecf4", "#bfd3e6", "#9ebcda", "#8c96c6", "#8c6bb1", "#88419d", "#810f7c", "#4d004b"],
    "GnBu": ["#f7fcf0", "#e0f3db", "#ccebc5", "#a8ddb5", "#7bccc4", "#4eb3d3", "#2b8cbe", "#0868ac", "#084081"],
    "Greens": ["#f7fcf5", "#e5f5e0", "#c7e9c0", "#a1d99b", "#74c476", "#41ab5d", "#238b45", "#006d2c", "#00441b"],
    "Greys": ["#ffffff", "#f0f0f0", "#d9d9d9", "#bdbdbd", "#969696", "#737373", "#525252", "#252525", "#000000"],
    "Oranges": ["#fff5eb", "#fee6ce", "#fdd0a2", "#fdae6b", "#fd8d3c", "#f16913", "#d94801", "#a63603", "#7f2704"],
    "OrRd": ["#fff7ec", "#fee8c8", "#fdd49e", "#fdbb84", "#fc8d59", "#ef6548", "#d7301f", "#b30000", "#7f0000"],
    "PuBu": ["#fff7fb", "#ece7f2", "#d0d1e6", "#a6bddb", "#74a9cf", "#3690c0", "#0570b0", "#045a8d", "#023858"],
    "PuBuGn": ["#fff7fb", "#ece2f0", "#d0d1e6", "#a6bddb", "#67a9cf", "#3690c0", "#02818a", "#016c59", "#014636"],
    "PuRd": ["#f7f4f9", "#e7e1ef", "#d4b9da", "#c994c7", "#df65b0", "#e7298a", "#ce1256", "#980043", "#67001f"],
    "Purples": ["#fcfbfd", "#efedf5", "#dadaeb", "#bcbddc", "#9e9ac8", "#807dba", "#6a51a3", "#54278f", "#3f007d"],
    "RdPu": ["#fff7f3", "#fde0dd", "#fcc5c0", "#fa9fb5", "#f768a1", "#dd3497", "#ae017e", "#7a0177", "#49006a"],
    "Reds": ["#fff5f0", "#fee0d2", "#fcbba1", "#fc9272", "#fb6a4a", "#ef3b2c", "#cb181d", "#a50f15", "#67000d"],
    "YlGn": ["#ffffe5", "#f7fcb9", "#d9f0a3", "#addd8e", "#78c679", "#41ab5d", "#238443", "#006837", "#004529"],
    "YlGnBu": ["#ffffd9", "#edf8b1", "#c7e9b4", "#7fcdbb", "#41b6c4", "#1d91c0", "#225ea8", "#253494", "#081d58"],
    "YlOrBr": ["#ffffe5", "#fff7bc", "#fee391", "#fec44f", "#fe9929", "#ec7014", "#cc4c02", "#993404", "#662506"],
    "YlOrRd": ["#ffffcc", "#ffeda0", "#fed976", "#feb24c", "#fd8d3c", "#fc4e2a", "#e31a1c", "#bd0026", "#800026"],
}


class GoogleMapsError(RuntimeError):
    """Raised when a map cannot be rendered with the supplied configuration."""


class Element:
    """Base class for objects that can be added to a map."""

    def add_to(self, map_obj: "Map") -> "Element":
        map_obj.add_child(self)
        return self

    def to_spec(self) -> dict[str, Any]:
        raise NotImplementedError


class Map:
    """A Folium-style Google Maps HTML renderer."""

    def __init__(
        self,
        location: Location,
        zoom_start: int = 10,
        *,
        api_key: str | None = None,
        map_type: str = "roadmap",
        width: str | int = "100%",
        height: str | int = "100%",
        map_id: str | None = None,
        fullscreen_control: bool | None = None,
        street_view_control: bool | None = None,
        options: dict[str, Any] | None = None,
    ) -> None:
        self.location = _location(location)
        self.zoom_start = zoom_start
        self.api_key = api_key
        if map_type not in _MAP_TYPES:
            supported = ", ".join(sorted(_MAP_TYPES))
            raise ValueError(f"Unsupported map_type {map_type!r}. Expected one of: {supported}.")
        self.map_type = map_type
        self.width = _css_size(width)
        self.height = _css_size(height)
        self.map_id = map_id
        self.fullscreen_control = fullscreen_control
        self.street_view_control = street_view_control
        self.options = options or {}
        self.children: list[Element] = []
        self._id = f"fgm_{id(self):x}"

    def add_child(self, child: Element) -> Element:
        self.children.append(child)
        return child

    def render_fragment(self) -> str:
        api_key = self._resolve_api_key()
        specs = [child.to_spec() for child in self.children]
        needs_marker = any(spec["type"] in {"marker", "draw"} for spec in specs)
        layer_control = any(spec["type"] == "layer_control" for spec in specs)
        drawable_specs = [spec for spec in specs if spec["type"] != "layer_control"]
        config = {
            "center": {"lat": self.location[0], "lng": self.location[1]},
            "zoom": self.zoom_start,
            "mapTypeId": self.map_type,
            **self.options,
        }
        if self.fullscreen_control is not None:
            config["fullscreenControl"] = self.fullscreen_control
        if self.street_view_control is not None:
            config["streetViewControl"] = self.street_view_control
        if self.map_id or needs_marker:
            config["mapId"] = self.map_id or _DEMO_MAP_ID

        context = {
            "api_key": api_key,
            "callback": f"{self._id}_init",
            "config": config,
            "height": self.height,
            "map_id": self._id,
            "specs": drawable_specs,
            "width": self.width,
            "layer_control": layer_control,
        }
        return _render_fragment(context)

    def render_html(self) -> str:
        fragment = self.render_fragment()
        return "\n".join(
            [
                "<!doctype html>",
                '<html lang="en">',
                "<head>",
                '  <meta charset="utf-8">',
                '  <meta name="viewport" content="width=device-width, initial-scale=1">',
                "  <title>Google Map</title>",
                "</head>",
                "<body>",
                fragment,
                "</body>",
                "</html>",
            ]
        )

    def save(self, path: str | os.PathLike[str]) -> None:
        Path(path).write_text(self.render_html(), encoding="utf-8")

    def _repr_html_(self) -> str:
        return self.render_fragment()

    def _resolve_api_key(self) -> str:
        api_key = self.api_key or os.environ.get("GOOGLE_MAPS_API_KEY")
        if not api_key:
            raise GoogleMapsError("Google Maps API key is required. Pass api_key=... or set GOOGLE_MAPS_API_KEY.")
        return api_key


class Marker(Element):
    def __init__(
        self,
        location: Location,
        *,
        popup: str | None = None,
        tooltip: str | None = None,
        icon: str | None = None,
        draggable: bool = False,
        name: str | None = None,
    ) -> None:
        self.location = _location(location)
        self.popup = popup
        self.tooltip = tooltip
        self.icon = icon
        self.draggable = draggable
        self.name = name

    def to_spec(self) -> dict[str, Any]:
        return {
            "type": "marker",
            "name": self.name,
            "position": {"lat": self.location[0], "lng": self.location[1]},
            "popup": self.popup,
            "tooltip": self.tooltip,
            "icon": self.icon,
            "draggable": self.draggable,
        }


class Polyline(Element):
    def __init__(
        self,
        locations: Iterable[Location],
        *,
        color: str = "#3388ff",
        weight: int = 3,
        opacity: float = 1.0,
        name: str | None = None,
    ) -> None:
        self.locations = [_lat_lng(location) for location in locations]
        self.color = color
        self.weight = weight
        self.opacity = opacity
        self.name = name

    def to_spec(self) -> dict[str, Any]:
        return {
            "type": "polyline",
            "name": self.name,
            "path": self.locations,
            "options": {"strokeColor": self.color, "strokeWeight": self.weight, "strokeOpacity": self.opacity},
        }


class Polygon(Element):
    def __init__(
        self,
        locations: Iterable[Location] | Iterable[Iterable[Location]],
        *,
        color: str = "#3388ff",
        fill_color: str | None = None,
        fill_opacity: float = 0.2,
        weight: int = 3,
        name: str | None = None,
    ) -> None:
        self.locations = _polygon_paths(locations)
        self.color = color
        self.fill_color = fill_color or color
        self.fill_opacity = fill_opacity
        self.weight = weight
        self.name = name

    def to_spec(self) -> dict[str, Any]:
        return {
            "type": "polygon",
            "name": self.name,
            "paths": self.locations,
            "options": {
                "strokeColor": self.color,
                "strokeWeight": self.weight,
                "fillColor": self.fill_color,
                "fillOpacity": self.fill_opacity,
            },
        }


class Circle(Element):
    def __init__(
        self,
        location: Location,
        radius: float,
        *,
        color: str = "#3388ff",
        fill_color: str | None = None,
        fill_opacity: float = 0.2,
        weight: int = 3,
        name: str | None = None,
    ) -> None:
        self.location = _location(location)
        self.radius = radius
        self.color = color
        self.fill_color = fill_color or color
        self.fill_opacity = fill_opacity
        self.weight = weight
        self.name = name

    def to_spec(self) -> dict[str, Any]:
        return {
            "type": "circle",
            "name": self.name,
            "center": {"lat": self.location[0], "lng": self.location[1]},
            "radius": self.radius,
            "options": {
                "strokeColor": self.color,
                "strokeWeight": self.weight,
                "fillColor": self.fill_color,
                "fillOpacity": self.fill_opacity,
            },
        }


class GeoJson(Element):
    def __init__(self, data: Any, *, name: str | None = None, style_function: Any | None = None) -> None:
        self.data = _geojson_data(data)
        self.name = name
        self.style_function = style_function

    def to_spec(self) -> dict[str, Any]:
        style = None
        if self.style_function:
            style = self.style_function(_sample_geojson_feature(self.data))
        return {"type": "geojson", "name": self.name, "data": self.data, "style": style}


class Choropleth(Element):
    """A Folium-style choropleth rendered as a Google Maps Data layer."""

    def __init__(
        self,
        geo_data: Any,
        data: Any | None = None,
        columns: Sequence[Any] | None = None,
        key_on: str | None = None,
        bins: int | Sequence[float] = 6,
        fill_color: str | None = None,
        nan_fill_color: str = "black",
        fill_opacity: float = 0.6,
        nan_fill_opacity: float | None = None,
        line_color: str = "black",
        line_weight: float = 1,
        line_opacity: float = 1,
        name: str | None = None,
        legend_name: str = "",
        overlay: bool = True,
        control: bool = True,
        show: bool = True,
        topojson: str | None = None,
        smooth_factor: float | None = None,
        highlight: bool = False,
        use_jenks: bool = False,
        **kwargs: Any,
    ) -> None:
        if topojson is not None:
            raise NotImplementedError("Choropleth topojson is not supported yet.")
        if smooth_factor is not None:
            # Google Maps Data layers do not expose Folium/Leaflet's smoothing option.
            pass
        if "threshold_scale" in kwargs and kwargs["threshold_scale"] is not None:
            bins = kwargs["threshold_scale"]

        self.data = _geojson_data(geo_data)
        self.name = name
        self.overlay = overlay
        self.control = control
        self.show = show
        self.legend_name = legend_name
        self.highlight = highlight
        self.fill_color = fill_color or ("blue" if data is None else "Blues")
        self.nan_fill_color = nan_fill_color
        self.fill_opacity = fill_opacity
        self.nan_fill_opacity = fill_opacity if nan_fill_opacity is None else nan_fill_opacity
        self.line_color = line_color
        self.line_weight = line_weight
        self.line_opacity = line_opacity
        self.color_data = _choropleth_color_data(data, columns)
        self.key_on = _normalize_key_on(key_on)
        self.bin_edges: list[float] | None = None
        self.color_range: list[str] | None = None
        self.use_jenks = use_jenks
        self.bins = bins

    def to_spec(self) -> dict[str, Any]:
        styled_data, legend = self._styled_geojson()
        return {
            "type": "choropleth",
            "name": self.name,
            "data": styled_data,
            "legend": legend,
            "highlightStyle": (
                {"strokeWeight": self.line_weight + 2, "fillOpacity": min(self.fill_opacity + 0.2, 1)}
                if self.highlight
                else None
            ),
        }

    def _styled_geojson(self) -> tuple[dict[str, Any], dict[str, Any] | None]:
        data = json.loads(json.dumps(self.data, ensure_ascii=False))
        features = _geojson_features(data)
        legend = None

        if self.color_data is not None and self.key_on is not None:
            bin_edges = _choropleth_bins(self.color_data.values(), self.bins, self.use_jenks)
            color_range = _choropleth_colors(self.fill_color, len(bin_edges) - 1)
            self.bin_edges = bin_edges
            self.color_range = color_range
            legend = _choropleth_legend(self.legend_name, bin_edges, color_range)
            adjusted_edges = list(bin_edges)
            increasing = adjusted_edges[0] <= adjusted_edges[-1]
            adjusted_edges[-1] = math.nextafter(adjusted_edges[-1], math.inf if increasing else -math.inf)
            for feature in features:
                key = _get_by_key(feature, self.key_on)
                if key is None:
                    raise ValueError(f"key_on {self.key_on!r} not found in GeoJSON.")
                value = _lookup_choropleth_value(self.color_data, key)
                color, opacity = self._color_for_value(value, adjusted_edges, color_range)
                _set_feature_style(feature, self._style(color, opacity))
        else:
            for feature in features:
                _set_feature_style(feature, self._style(self.fill_color, self.fill_opacity))

        return data, legend

    def _style(self, fill_color: str, fill_opacity: float) -> dict[str, Any]:
        return {
            "strokeWeight": self.line_weight,
            "strokeOpacity": self.line_opacity,
            "strokeColor": self.line_color,
            "fillOpacity": fill_opacity,
            "fillColor": fill_color,
        }

    def _color_for_value(self, value: Any, bin_edges: Sequence[float], color_range: Sequence[str]) -> tuple[str, float]:
        if value is None:
            return self.nan_fill_color, self.nan_fill_opacity
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return self.nan_fill_color, self.nan_fill_opacity
        if math.isnan(numeric):
            return self.nan_fill_color, self.nan_fill_opacity
        if numeric < min(bin_edges) or numeric > max(bin_edges):
            raise ValueError("All values are expected to fall into one of the provided bins or be NaN.")
        color_idx = max(0, min(len(color_range) - 1, _bisect_right(bin_edges, numeric) - 1))
        return color_range[color_idx], self.fill_opacity


class Draw(Element):
    """A Folium-style drawing control implemented with core Google Maps overlays."""

    _POSITIONS = {"topleft", "topright", "bottomleft", "bottomright"}

    def __init__(
        self,
        export: bool = False,
        feature_group: Any | None = None,
        filename: str = "data.geojson",
        position: str = "topleft",
        show_geometry_on_click: bool = True,
        draw_options: dict[str, Any] | None = None,
        edit_options: dict[str, Any] | None = None,
        on: dict[str, Any] | None = None,
    ) -> None:
        if feature_group is not None:
            raise NotImplementedError("Draw feature_group is not supported yet.")
        if position not in self._POSITIONS:
            supported = ", ".join(sorted(self._POSITIONS))
            raise ValueError(f"Unsupported Draw position {position!r}. Expected one of: {supported}.")
        self.export = export
        self.filename = filename
        self.position = position
        self.show_geometry_on_click = show_geometry_on_click
        self.draw_options = draw_options or {}
        self.edit_options = edit_options or {}
        self.on = on or {}

    def to_spec(self) -> dict[str, Any]:
        return {
            "type": "draw",
            "export": self.export,
            "filename": self.filename,
            "position": self.position,
            "showGeometryOnClick": self.show_geometry_on_click,
            "drawOptions": self.draw_options,
            "editOptions": self.edit_options,
            "events": list(self.on),
        }


class HeatMap(Element):
    def __init__(
        self,
        data: Iterable[Any],
        *,
        name: str | None = None,
        radius: int = 25,
        blur: int = 15,
        min_opacity: float = 0.05,
        max_zoom: int | None = 18,
        max_value: float = 1.0,
        gradient: dict[float, str] | None = None,
        opacity: float = 1.0,
        intensity: float = 1.0,
        threshold: float = 0.03,
        scale_radius_with_zoom: bool = False,
        min_radius: int = 6,
        max_radius: int = 240,
    ) -> None:
        self.data = [_heatmap_point(point) for point in data]
        self.name = name
        self.radius = radius
        self.blur = blur
        self.min_opacity = min_opacity
        self.max_zoom = max_zoom
        self.max_value = max_value
        self.gradient = gradient or {0.4: "blue", 0.6: "cyan", 0.7: "lime", 0.8: "yellow", 1.0: "red"}
        self.opacity = opacity
        self.intensity = intensity
        self.threshold = threshold
        self.scale_radius_with_zoom = scale_radius_with_zoom
        self.min_radius = min_radius
        self.max_radius = max_radius

    def to_spec(self) -> dict[str, Any]:
        return {
            "type": "heatmap",
            "name": self.name,
            "data": self.data,
            "options": {
                "radiusPixels": self.radius,
                "blurPixels": self.blur,
                "minOpacity": self.min_opacity,
                "maxZoom": self.max_zoom,
                "max": self.max_value,
                "gradient": self.gradient,
                "opacity": self.opacity,
                "intensity": self.intensity,
                "threshold": self.threshold,
                "scaleRadiusWithZoom": self.scale_radius_with_zoom,
                "minRadiusPixels": self.min_radius,
                "maxRadiusPixels": self.max_radius,
            },
        }


class LayerControl(Element):
    def to_spec(self) -> dict[str, Any]:
        return {"type": "layer_control"}


def _location(value: Location) -> tuple[float, float]:
    if len(value) != 2:
        raise ValueError("Location must be a [lat, lng] pair.")
    return (float(value[0]), float(value[1]))


def _lat_lng(value: Location) -> dict[str, float]:
    lat, lng = _location(value)
    return {"lat": lat, "lng": lng}


def _css_size(value: str | int) -> str:
    if isinstance(value, int):
        return f"{value}px"
    return value


def _polygon_paths(locations: Iterable[Location] | Iterable[Iterable[Location]]) -> list[Any]:
    items = list(locations)
    if not items:
        return []
    first = items[0]
    if _looks_like_location(first):
        return [_lat_lng(item) for item in items]  # type: ignore[arg-type]
    return [[_lat_lng(point) for point in path] for path in items]  # type: ignore[arg-type]


def _looks_like_location(value: Any) -> bool:
    return isinstance(value, Sequence) and len(value) == 2 and all(isinstance(item, (int, float)) for item in value)


def _geojson_data(data: Any) -> dict[str, Any]:
    if isinstance(data, (str, os.PathLike)):
        return json.loads(Path(data).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data
    if hasattr(data, "__geo_interface__"):
        return data.__geo_interface__
    if hasattr(data, "to_json"):
        return json.loads(data.to_json())
    raise TypeError("GeoJson data must be a dict, path, __geo_interface__ object, or object with to_json().")


def _sample_geojson_feature(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("type") == "FeatureCollection" and data.get("features"):
        return data["features"][0]
    if data.get("type") == "Feature":
        return data
    return {"type": "Feature", "properties": {}, "geometry": None}


def _geojson_features(data: dict[str, Any]) -> list[dict[str, Any]]:
    if data.get("type") == "FeatureCollection":
        return data.get("features", [])
    if data.get("type") == "Feature":
        return [data]
    return []


def _set_feature_style(feature: dict[str, Any], style: dict[str, Any]) -> None:
    properties = feature.setdefault("properties", {})
    properties[_CHOROPLETH_STYLE_PROPERTY] = style


def _normalize_key_on(key_on: str | None) -> str | None:
    if key_on is None:
        return None
    return key_on[8:] if key_on.startswith("feature.") else key_on


def _get_by_key(obj: Any, key: str) -> Any:
    value = obj
    for part in key.split("."):
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) and part.isdigit():
            index = int(part)
            value = value[index] if index < len(value) else None
        elif isinstance(value, dict):
            value = value.get(part)
        else:
            return None
        if value is None:
            return None
    return value


def _choropleth_color_data(data: Any | None, columns: Sequence[Any] | None) -> dict[Any, Any] | None:
    if data is None:
        return None
    if hasattr(data, "set_index"):
        if columns is None or len(columns) < 2:
            raise ValueError("columns must contain key and value columns when data is DataFrame-like.")
        return data.set_index(columns[0])[columns[1]].to_dict()
    if hasattr(data, "to_dict"):
        return data.to_dict()
    return dict(data)


def _lookup_choropleth_value(color_data: dict[Any, Any], key: Any) -> Any:
    if key in color_data:
        return color_data[key]
    try:
        if isinstance(key, int):
            return color_data[str(key)]
        if isinstance(key, str):
            return color_data[int(key)]
    except (KeyError, ValueError):
        return None
    except TypeError:
        return None
    return None


def _choropleth_bins(values: Iterable[Any], bins: int | Sequence[float], use_jenks: bool) -> list[float]:
    real_values = [_finite_float(value) for value in values]
    real_values = [value for value in real_values if value is not None]
    if not real_values:
        raise ValueError("Choropleth data must contain at least one finite value.")
    if use_jenks:
        if not isinstance(bins, int):
            raise ValueError("bins must be an integer when use_jenks=True.")
        try:
            from jenkspy import jenks_breaks
        except ImportError as exc:
            raise RuntimeError("use_jenks=True requires jenkspy to be installed.") from exc
        return [float(edge) for edge in jenks_breaks(real_values, bins)]
    if isinstance(bins, int):
        if bins < 1:
            raise ValueError("bins must be a positive integer.")
        minimum = min(real_values)
        maximum = max(real_values)
        if minimum == maximum:
            minimum -= 0.5
            maximum += 0.5
        step = (maximum - minimum) / bins
        return [minimum + step * index for index in range(bins)] + [maximum]
    bin_edges = [float(edge) for edge in bins]
    if len(bin_edges) < 2:
        raise ValueError("bins must contain at least two edges.")
    if any(next_edge < edge for edge, next_edge in zip(bin_edges, bin_edges[1:])):
        raise ValueError("bins must be sorted in ascending order.")
    minimum = min(bin_edges)
    maximum = max(bin_edges)
    if any(value < minimum or value > maximum for value in real_values):
        raise ValueError("All values are expected to fall into one of the provided bins or be NaN.")
    return bin_edges


def _finite_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(numeric) else numeric


def _choropleth_colors(fill_color: str, count: int) -> list[str]:
    palette = _COLOR_BREWER.get(fill_color)
    if palette is None:
        raise ValueError(f"Unsupported ColorBrewer palette {fill_color!r}.")
    if count <= 0:
        raise ValueError("Choropleth requires at least one color.")
    if count == 1:
        return [palette[-1]]
    if count <= len(palette):
        return [palette[round(index * (len(palette) - 1) / (count - 1))] for index in range(count)]
    return [_interpolate_color(palette, index / (count - 1)) for index in range(count)]


def _interpolate_color(palette: Sequence[str], position: float) -> str:
    scaled = position * (len(palette) - 1)
    lower = int(math.floor(scaled))
    upper = min(len(palette) - 1, lower + 1)
    fraction = scaled - lower
    low_rgb = _hex_to_rgb(palette[lower])
    high_rgb = _hex_to_rgb(palette[upper])
    rgb = tuple(round(low + (high - low) * fraction) for low, high in zip(low_rgb, high_rgb))
    return "#%02x%02x%02x" % rgb


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    color = value.lstrip("#")
    return (int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16))


def _choropleth_legend(caption: str, bin_edges: Sequence[float], colors: Sequence[str]) -> dict[str, Any]:
    entries = []
    for index, color in enumerate(colors):
        entries.append({"color": color, "label": f"{_format_bin(bin_edges[index])} - {_format_bin(bin_edges[index + 1])}"})
    return {"caption": caption, "entries": entries}


def _format_bin(value: float) -> str:
    return f"{value:g}"


def _bisect_right(values: Sequence[float], item: float) -> int:
    low = 0
    high = len(values)
    while low < high:
        middle = (low + high) // 2
        if item < values[middle]:
            high = middle
        else:
            low = middle + 1
    return low


def _heatmap_point(point: Any) -> dict[str, Any]:
    if isinstance(point, dict):
        location = point.get("location")
        if location is None:
            location = [point.get("lat"), point.get("lng")]
        lat, lng = _location(location)
        return {"position": [lng, lat], "weight": float(point.get("weight", 1))}

    if isinstance(point, Sequence) and len(point) in {2, 3}:
        lat, lng = _location(point[:2])
        weight = float(point[2]) if len(point) == 3 else 1.0
        return {"position": [lng, lat], "weight": weight}

    raise TypeError("HeatMap points must be [lat, lng], [lat, lng, weight], or {'location': [lat, lng], 'weight': n}.")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _render_fragment(context: dict[str, Any]) -> str:
    specs_json = _json(context["specs"])
    config_json = _json(context["config"])
    api_key = _json(context["api_key"])
    map_id = context["map_id"]
    callback = context["callback"]
    control_style = (
        f"<style>#{map_id}_layers{{background:#fff;"
        "border:1px solid #dadce0;border-radius:4px;padding:8px;font:13px Arial,sans-serif;"
        "box-shadow:0 1px 4px rgba(0,0,0,.2);margin:10px}"
        f"#{map_id}_layers label{{display:block;white-space:nowrap;margin:4px 0}}</style>\n"
        if context["layer_control"]
        else ""
    )
    fullscreen_style = (
        f"<style>#{map_id}_wrap:fullscreen,#{map_id}_wrap:fullscreen>#{map_id},"
        f"#{map_id}:fullscreen,#{map_id}:fullscreen .gm-style{{width:100vw!important;height:100vh!important}}"
        f"#{map_id}_wrap:-webkit-full-screen,#{map_id}_wrap:-webkit-full-screen>#{map_id},"
        f"#{map_id}:-webkit-full-screen,#{map_id}:-webkit-full-screen .gm-style{{width:100vw!important;height:100vh!important}}</style>\n"
    )
    control_div = f'<div id="{map_id}_layers" hidden></div>' if context["layer_control"] else ""
    return f"""<div id="{map_id}_wrap" style="position:relative;width:{context['width']};height:{context['height']};">
  <div id="{map_id}" style="position:relative;width:100%;height:100%;"></div>
  {control_div}
</div>
{fullscreen_style}{control_style}<script>
function {callback}_loadScript(src, test) {{
  if (test()) return Promise.resolve();
  return new Promise((resolve, reject) => {{
    const existing = Array.from(document.scripts).find(script => script.dataset.fgmSrc === src);
    if (existing) {{
      existing.addEventListener("load", resolve, {{ once: true }});
      existing.addEventListener("error", reject, {{ once: true }});
      if (test()) resolve();
      return;
    }}
    const script = document.createElement("script");
    script.async = true;
    script.dataset.fgmSrc = src;
    script.src = src;
    script.addEventListener("load", resolve, {{ once: true }});
    script.addEventListener("error", reject, {{ once: true }});
    document.head.appendChild(script);
  }});
}}

window.{callback} = async function() {{
  const specs = {specs_json};
  const config = {config_json};
  const namedLayers = [];
  const legends = [];
  const {{ Map, InfoWindow, Polyline, Polygon, Circle, Rectangle }} = await google.maps.importLibrary("maps");
  const {{ AdvancedMarkerElement }} = await google.maps.importLibrary("marker");
  const map = new Map(document.getElementById("{map_id}"), config);
  const panorama = map.getStreetView();
  let streetViewVisible = panorama.getVisible();

  function track(name, layer, setVisible, options = {{}}) {{
    if (!name) return;
    const entry = {{
      name,
      layer,
      setVisible,
      hideInStreetView: Boolean(options.hideInStreetView),
      layerVisible: true,
      applyVisibility() {{
        setVisible(this.layerVisible && !(this.hideInStreetView && streetViewVisible));
      }}
    }};
    namedLayers.push(entry);
  }}

  function drawControlPosition(position) {{
    const positions = {{
      topleft: google.maps.ControlPosition.TOP_LEFT,
      topright: google.maps.ControlPosition.TOP_RIGHT,
      bottomleft: google.maps.ControlPosition.BOTTOM_LEFT,
      bottomright: google.maps.ControlPosition.BOTTOM_RIGHT
    }};
    return positions[position] || google.maps.ControlPosition.TOP_LEFT;
  }}

  function setupDrawControl(spec) {{
    const drawnItems = [];
    let mode = null;
    let draftPath = [];
    let draftOverlay = null;
    let startPoint = null;
    let finishButton = null;
    let clearButton = null;
    let exportLink = null;
    const drawOptions = spec.drawOptions || {{}};
    const strokeOptions = {{
      strokeColor: drawOptions.strokeColor || "#3388ff",
      strokeOpacity: drawOptions.strokeOpacity ?? 1,
      strokeWeight: drawOptions.strokeWeight || 3,
      fillColor: drawOptions.fillColor || "#3388ff",
      fillOpacity: drawOptions.fillOpacity ?? 0.2
    }};

    const control = document.createElement("div");
    control.dataset.fgmDrawControl = "true";
    control.style.background = "#fff";
    control.style.border = "1px solid #dadce0";
    control.style.borderRadius = "4px";
    control.style.boxShadow = "0 1px 4px rgba(0,0,0,.2)";
    control.style.display = "flex";
    control.style.flexWrap = "wrap";
    control.style.gap = "4px";
    control.style.margin = "10px";
    control.style.padding = "6px";

    function addSeparator() {{
      const separator = document.createElement("span");
      separator.dataset.fgmDrawSeparator = "true";
      separator.style.alignSelf = "stretch";
      separator.style.borderLeft = "1px solid #dadce0";
      separator.style.margin = "0 2px";
      control.appendChild(separator);
    }}

    function addButton(label, nextMode) {{
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.dataset.fgmDrawMode = nextMode;
      button.style.background = "#fff";
      button.style.border = "1px solid #dadce0";
      button.style.borderRadius = "3px";
      button.style.color = "#202124";
      button.style.cursor = "pointer";
      button.style.font = "12px Arial,sans-serif";
      button.style.padding = "4px 6px";
      button.addEventListener("click", () => setMode(mode === nextMode ? null : nextMode));
      control.appendChild(button);
    }}

    function addActionButton(label, handler, colors = {{}}) {{
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.dataset.fgmDrawAction = label.toLowerCase();
      button.style.background = colors.background || "#f8f9fa";
      button.style.border = "1px solid " + (colors.border || "#dadce0");
      button.style.borderRadius = "3px";
      button.style.color = colors.color || "#202124";
      button.style.cursor = "pointer";
      button.style.font = "12px Arial,sans-serif";
      button.style.padding = "4px 6px";
      button.addEventListener("click", handler);
      control.appendChild(button);
      return button;
    }}

    function setMode(nextMode) {{
      mode = nextMode;
      draftPath = [];
      startPoint = null;
      if (draftOverlay) {{
        draftOverlay.setMap(null);
        draftOverlay = null;
      }}
      for (const button of control.querySelectorAll("button[data-fgm-draw-mode]")) {{
        const selected = button.dataset.fgmDrawMode === mode;
        button.style.background = selected ? "#1a73e8" : "#fff";
        button.style.borderColor = selected ? "#1a73e8" : "#dadce0";
        button.style.color = selected ? "#fff" : "#202124";
      }}
      updateFinishButton();
    }}

    function updateFinishButton() {{
      if (!finishButton) return;
      const canFinish = (mode === "polyline" && draftPath.length >= 2) || (mode === "polygon" && draftPath.length >= 3);
      finishButton.disabled = !canFinish;
      finishButton.style.background = canFinish ? "#1a73e8" : "#f1f3f4";
      finishButton.style.borderColor = canFinish ? "#1a73e8" : "#dadce0";
      finishButton.style.color = canFinish ? "#fff" : "#9aa0a6";
      finishButton.style.cursor = canFinish ? "pointer" : "default";
      finishButton.style.opacity = canFinish ? "1" : "0.65";
    }}

    function updateDrawnActionButtons() {{
      const hasDrawnItems = drawnItems.length > 0;
      if (clearButton) {{
        clearButton.disabled = !hasDrawnItems;
        clearButton.style.background = hasDrawnItems ? "#fce8e6" : "#f1f3f4";
        clearButton.style.borderColor = hasDrawnItems ? "#fad2cf" : "#dadce0";
        clearButton.style.color = hasDrawnItems ? "#a50e0e" : "#9aa0a6";
        clearButton.style.cursor = hasDrawnItems ? "pointer" : "default";
        clearButton.style.opacity = hasDrawnItems ? "1" : "0.65";
      }}
      if (exportLink) {{
        exportLink.setAttribute("aria-disabled", hasDrawnItems ? "false" : "true");
        exportLink.style.background = hasDrawnItems ? "#e6f4ea" : "#f1f3f4";
        exportLink.style.borderColor = hasDrawnItems ? "#ceead6" : "#dadce0";
        exportLink.style.color = hasDrawnItems ? "#137333" : "#9aa0a6";
        exportLink.style.cursor = hasDrawnItems ? "pointer" : "default";
        exportLink.style.opacity = hasDrawnItems ? "1" : "0.65";
      }}
    }}

    function enabled(name) {{
      return drawOptions[name] !== false;
    }}

    if (enabled("marker")) addButton("Marker", "marker");
    if (enabled("polyline")) addButton("Line", "polyline");
    if (enabled("polygon")) addButton("Polygon", "polygon");
    if (enabled("rectangle")) addButton("Rectangle", "rectangle");
    if (enabled("circle")) addButton("Circle", "circle");
    addSeparator();
    finishButton = addActionButton("Finish", () => finishPath());
    updateFinishButton();
    clearButton = addActionButton("Clear", () => clearDrawnItems(), {{ background: "#fce8e6", border: "#fad2cf", color: "#a50e0e" }});

    if (spec.export) {{
      exportLink = document.createElement("a");
      exportLink.href = "#";
      exportLink.textContent = "Export";
      exportLink.download = spec.filename || "data.geojson";
      exportLink.dataset.fgmDrawExport = "true";
      exportLink.style.alignSelf = "center";
      exportLink.style.background = "#e6f4ea";
      exportLink.style.border = "1px solid #ceead6";
      exportLink.style.borderRadius = "3px";
      exportLink.style.color = "#137333";
      exportLink.style.font = "12px Arial,sans-serif";
      exportLink.style.padding = "4px 6px";
      exportLink.style.textDecoration = "none";
      exportLink.addEventListener("click", event => {{
        if (!drawnItems.length) {{
          event.preventDefault();
          return;
        }}
        const data = "text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(toFeatureCollection()));
        exportLink.setAttribute("href", "data:" + data);
      }});
      control.appendChild(exportLink);
    }}
    updateDrawnActionButtons();

    map.controls[drawControlPosition(spec.position)].push(control);

    map.addListener("click", event => {{
      if (!mode || !event.latLng) return;
      if (mode === "marker") {{
        addDrawnOverlay("marker", new AdvancedMarkerElement({{ map, position: event.latLng, gmpClickable: spec.showGeometryOnClick }}));
      }} else if (mode === "polyline" || mode === "polygon") {{
        addPathPoint(event.latLng);
      }} else if (mode === "rectangle") {{
        handleRectanglePoint(event.latLng);
      }} else if (mode === "circle") {{
        handleCirclePoint(event.latLng);
      }}
    }});

    map.addListener("mousemove", event => {{
      if (!event.latLng) return;
      if ((mode === "polyline" || mode === "polygon") && draftOverlay && draftPath.length) {{
        updatePathPreview(event.latLng);
      }} else if (!startPoint) {{
        return;
      }} else if (mode === "rectangle" && draftOverlay) {{
        draftOverlay.setBounds(boundsFrom(startPoint, event.latLng));
      }} else if (mode === "circle" && draftOverlay) {{
        draftOverlay.setRadius(distanceMeters(startPoint, event.latLng));
      }}
    }});

    map.addListener("dblclick", () => finishPath());

    function addPathPoint(latLng) {{
      draftPath.push(latLng);
      if (!draftOverlay) {{
        draftOverlay = mode === "polygon"
          ? new Polygon({{ map, paths: draftPath, clickable: false, ...strokeOptions }})
          : new Polyline({{ map, path: draftPath, clickable: false, ...strokeOptions }});
      }} else if (mode === "polygon") {{
        draftOverlay.setPaths(draftPath);
      }} else {{
        draftOverlay.setPath(draftPath);
      }}
      updateFinishButton();
    }}

    function updatePathPreview(latLng) {{
      const previewPath = [...draftPath, latLng];
      if (mode === "polygon") {{
        draftOverlay.setPaths(previewPath);
      }} else {{
        draftOverlay.setPath(previewPath);
      }}
    }}

    function finishPath() {{
      if (!draftOverlay || !mode) return;
      if (mode === "polyline" && draftPath.length >= 2) {{
        draftOverlay.setPath(draftPath);
        draftOverlay.setOptions({{ clickable: spec.showGeometryOnClick }});
        addDrawnOverlay("polyline", draftOverlay);
        draftOverlay = null;
      }} else if (mode === "polygon" && draftPath.length >= 3) {{
        draftOverlay.setPaths(draftPath);
        draftOverlay.setOptions({{ clickable: spec.showGeometryOnClick }});
        addDrawnOverlay("polygon", draftOverlay);
        draftOverlay = null;
      }}
      setMode(null);
    }}

    function handleRectanglePoint(latLng) {{
      if (!startPoint) {{
        startPoint = latLng;
        draftOverlay = new Rectangle({{ map, bounds: boundsFrom(startPoint, latLng), clickable: false, ...strokeOptions }});
      }} else {{
        draftOverlay.setBounds(boundsFrom(startPoint, latLng));
        draftOverlay.setOptions({{ clickable: spec.showGeometryOnClick }});
        addDrawnOverlay("rectangle", draftOverlay);
        draftOverlay = null;
        setMode(null);
      }}
    }}

    function handleCirclePoint(latLng) {{
      if (!startPoint) {{
        startPoint = latLng;
        draftOverlay = new Circle({{ map, center: startPoint, radius: 1, clickable: false, ...strokeOptions }});
      }} else {{
        draftOverlay.setRadius(distanceMeters(startPoint, latLng));
        draftOverlay.setOptions({{ clickable: spec.showGeometryOnClick }});
        addDrawnOverlay("circle", draftOverlay);
        draftOverlay = null;
        setMode(null);
      }}
    }}

    function addDrawnOverlay(type, overlay) {{
      const item = {{ type, overlay }};
      drawnItems.push(item);
      if (spec.showGeometryOnClick) {{
        const clickEvent = type === "marker" ? "gmp-click" : "click";
        overlay.addListener(clickEvent, () => alert(JSON.stringify(toFeature(item))));
      }}
      const feature = toFeature(item);
      window.dispatchEvent(new CustomEvent("gmaprium-draw-created", {{ detail: {{ type, feature }} }}));
      dispatchDrawState(feature);
      updateDrawnActionButtons();
    }}

    function clearDrawnItems() {{
      for (const item of drawnItems) {{
        if (item.type === "marker") item.overlay.map = null;
        else item.overlay.setMap(null);
      }}
      drawnItems.length = 0;
      dispatchDrawState(null);
      updateDrawnActionButtons();
    }}

    function toFeatureCollection() {{
      return {{ type: "FeatureCollection", features: drawnItems.map(toFeature) }};
    }}

    function drawState(lastFeature) {{
      return {{ all_drawings: drawnItems.map(toFeature), last_active_drawing: lastFeature }};
    }}

    function dispatchDrawState(lastFeature) {{
      window.dispatchEvent(new CustomEvent("gmaprium-draw-updated", {{ detail: drawState(lastFeature) }}));
    }}

    function toFeature(item) {{
      if (item.type === "marker") {{
        return {{ type: "Feature", properties: {{}}, geometry: {{ type: "Point", coordinates: latLngCoordinates(item.overlay.position) }} }};
      }}
      if (item.type === "polyline") {{
        return {{ type: "Feature", properties: {{}}, geometry: {{ type: "LineString", coordinates: pathCoordinates(item.overlay.getPath()) }} }};
      }}
      if (item.type === "polygon") {{
        const coordinates = pathCoordinates(item.overlay.getPath());
        if (coordinates.length && (coordinates[0][0] !== coordinates[coordinates.length - 1][0] || coordinates[0][1] !== coordinates[coordinates.length - 1][1])) {{
          coordinates.push(coordinates[0]);
        }}
        return {{ type: "Feature", properties: {{}}, geometry: {{ type: "Polygon", coordinates: [coordinates] }} }};
      }}
      if (item.type === "rectangle") {{
        return {{ type: "Feature", properties: {{}}, geometry: {{ type: "Polygon", coordinates: [rectangleCoordinates(item.overlay.getBounds())] }} }};
      }}
      const center = item.overlay.getCenter();
      return {{
        type: "Feature",
        properties: {{ radiusMeters: item.overlay.getRadius() }},
        geometry: {{ type: "Point", coordinates: [center.lng(), center.lat()] }}
      }};
    }}

    function latLngCoordinates(value) {{
      const lng = typeof value.lng === "function" ? value.lng() : value.lng;
      const lat = typeof value.lat === "function" ? value.lat() : value.lat;
      return [lng, lat];
    }}

    function pathCoordinates(path) {{
      const coordinates = [];
      for (let i = 0; i < path.getLength(); i++) {{
        const point = path.getAt(i);
        coordinates.push(latLngCoordinates(point));
      }}
      return coordinates;
    }}

    function rectangleCoordinates(bounds) {{
      const ne = bounds.getNorthEast();
      const sw = bounds.getSouthWest();
      return [[sw.lng(), sw.lat()], [ne.lng(), sw.lat()], [ne.lng(), ne.lat()], [sw.lng(), ne.lat()], [sw.lng(), sw.lat()]];
    }}

    function boundsFrom(a, b) {{
      return new google.maps.LatLngBounds(
        new google.maps.LatLng(Math.min(a.lat(), b.lat()), Math.min(a.lng(), b.lng())),
        new google.maps.LatLng(Math.max(a.lat(), b.lat()), Math.max(a.lng(), b.lng()))
      );
    }}

    function distanceMeters(a, b) {{
      const radius = 6371008.8;
      const lat1 = a.lat() * Math.PI / 180;
      const lat2 = b.lat() * Math.PI / 180;
      const dLat = lat2 - lat1;
      const dLng = (b.lng() - a.lng()) * Math.PI / 180;
      const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
      return 2 * radius * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
    }}
  }}

  for (const spec of specs) {{
    if (spec.type === "marker") {{
      const markerOptions = {{
        map,
        position: spec.position,
        title: spec.tooltip || undefined,
        gmpClickable: Boolean(spec.popup),
        gmpDraggable: spec.draggable || false
      }};
      if (spec.icon) {{
        const img = document.createElement("img");
        img.src = spec.icon;
        markerOptions.content = img;
      }}
      const marker = new AdvancedMarkerElement(markerOptions);
      if (spec.popup) {{
        const info = new InfoWindow({{ content: spec.popup }});
        marker.addListener("gmp-click", () => info.open({{ anchor: marker, map }}));
      }}
      track(spec.name, marker, visible => marker.map = visible ? map : null);
    }} else if (spec.type === "polyline") {{
      const layer = new Polyline({{ map, path: spec.path, ...spec.options }});
      track(spec.name, layer, visible => layer.setMap(visible ? map : null));
    }} else if (spec.type === "polygon") {{
      const layer = new Polygon({{ map, paths: spec.paths, ...spec.options }});
      track(spec.name, layer, visible => layer.setMap(visible ? map : null));
    }} else if (spec.type === "circle") {{
      const layer = new Circle({{ map, center: spec.center, radius: spec.radius, ...spec.options }});
      track(spec.name, layer, visible => layer.setMap(visible ? map : null));
    }} else if (spec.type === "geojson") {{
      const layer = new google.maps.Data({{ map }});
      layer.addGeoJson(spec.data);
      if (spec.style) layer.setStyle(spec.style);
      track(spec.name, layer, visible => layer.setMap(visible ? map : null));
    }} else if (spec.type === "choropleth") {{
      const layer = new google.maps.Data({{ map }});
      layer.addGeoJson(spec.data);
      layer.setStyle(feature => feature.getProperty("{_CHOROPLETH_STYLE_PROPERTY}") || {{}});
      if (spec.highlightStyle) {{
        layer.addListener("mouseover", event => layer.overrideStyle(event.feature, spec.highlightStyle));
        layer.addListener("mouseout", event => layer.revertStyle(event.feature));
      }}
      if (spec.legend) legends.push(spec.legend);
      track(spec.name, layer, visible => layer.setMap(visible ? map : null));
    }} else if (spec.type === "draw") {{
      setupDrawControl(spec);
    }} else if (spec.type === "heatmap") {{
      class CanvasHeatmapOverlay extends google.maps.OverlayView {{
        constructor(data, options, baseZoom) {{
          super();
          this.data = data;
          this.options = options;
          this.baseZoom = baseZoom;
          this.canvas = null;
          this.listeners = [];
          this.circle = null;
          this.circleRadius = null;
          this.circleBlur = null;
          this.gradientPixels = null;
          this.gradientKey = null;
          this.resizeObserver = null;
          this.drawScheduled = false;
          this.delayedDrawScheduled = false;
          this.delayedDrawTimers = [];
          this.handleResize = () => this.scheduleDraw(true);
        }}

        onAdd() {{
          this.canvas = document.createElement("canvas");
          this.canvas.style.position = "absolute";
          this.canvas.style.left = "0";
          this.canvas.style.top = "0";
          this.canvas.style.zIndex = "5";
          this.canvas.style.pointerEvents = "none";
          this.canvas.dataset.fgmHeatmap = "true";
          this.getPanes().overlayLayer.appendChild(this.canvas);
          this.listeners.push(google.maps.event.addListener(this.getMap(), "idle", () => this.scheduleDraw()));
          this.listeners.push(google.maps.event.addListener(this.getMap(), "bounds_changed", () => this.scheduleDraw()));
          this.listeners.push(google.maps.event.addListener(this.getMap(), "zoom_changed", () => this.scheduleDraw()));
          if (window.ResizeObserver) {{
            this.resizeObserver = new ResizeObserver(() => this.scheduleDraw(true));
            this.resizeObserver.observe(this.getMap().getDiv());
          }}
          window.addEventListener("resize", this.handleResize);
          document.addEventListener("fullscreenchange", this.handleResize);
        }}

        scheduleDraw(delayed = false) {{
          if (!this.drawScheduled) {{
            this.drawScheduled = true;
            window.requestAnimationFrame(() => {{
              this.drawScheduled = false;
              this.draw();
            }});
          }}
          if (delayed && !this.delayedDrawScheduled) {{
            this.delayedDrawScheduled = true;
            for (const delay of [100, 300, 700]) {{
              const timer = window.setTimeout(() => {{
                this.scheduleDraw();
                if (delay === 700) this.delayedDrawScheduled = false;
              }}, delay);
              this.delayedDrawTimers.push(timer);
            }}
          }}
        }}

        draw() {{
          if (!this.canvas) return;
          const projection = this.getProjection();
          const panes = this.getPanes();
          const map = this.getMap();
          const mapDiv = this.getMap().getDiv();
          if (!projection || !panes || !mapDiv) return;
          if (this.canvas.parentElement !== panes.overlayLayer) {{
            panes.overlayLayer.appendChild(this.canvas);
          }}
          const viewport = this.getDrawViewport(mapDiv);
          const width = viewport.width;
          const height = viewport.height;
          const centerPixel = projection.fromLatLngToDivPixel(map.getCenter());
          if (!centerPixel) return;
          const topLeft = {{ x: centerPixel.x - width / 2, y: centerPixel.y - height / 2 }};
          if (this.canvas.width !== width) this.canvas.width = width;
          if (this.canvas.height !== height) this.canvas.height = height;
          this.canvas.style.left = Math.round(topLeft.x) + "px";
          this.canvas.style.top = Math.round(topLeft.y) + "px";
          this.canvas.style.width = width + "px";
          this.canvas.style.height = height + "px";

          const ctx = this.canvas.getContext("2d", {{ willReadFrequently: true }});
          ctx.clearRect(0, 0, width, height);

          const radius = this.options.radiusPixels || 25;
          const blur = this.options.blurPixels === undefined ? 15 : this.options.blurPixels;
          const drawRadius = radius + blur;
          const circle = this.getCircle(radius, blur);
          const zoom = this.getMap().getZoom() ?? this.baseZoom;
          const maxZoom = this.options.maxZoom ?? 18;
          const zoomIntensity = 1 / Math.pow(2, Math.max(0, Math.min(maxZoom - zoom, 12)));
          const maxValue = this.options.max || 1;
          const minOpacity = this.options.minOpacity ?? 0.05;
          const bounds = {{
            minX: -drawRadius,
            minY: -drawRadius,
            maxX: width + drawRadius,
            maxY: height + drawRadius
          }};
          const geoBounds = this.getExpandedGeoBounds(projection, topLeft, width, height, drawRadius);
          const cellSize = drawRadius / 2;
          const grid = [];
          let hasCells = false;

          for (const point of this.data) {{
            const lng = point.position[0];
            const lat = point.position[1];
            if (geoBounds && !this.containsLatLng(geoBounds, lat, lng)) continue;
            const divPixel = projection.fromLatLngToDivPixel(new google.maps.LatLng(lat, lng));
            if (!divPixel) continue;
            const pixel = {{ x: divPixel.x - topLeft.x, y: divPixel.y - topLeft.y }};
            if (pixel.x < bounds.minX || pixel.x > bounds.maxX || pixel.y < bounds.minY || pixel.y > bounds.maxY) continue;
            const x = Math.floor(pixel.x / cellSize) + 2;
            const y = Math.floor(pixel.y / cellSize) + 2;
            const value = (point.weight === undefined ? 1 : point.weight) * zoomIntensity;
            grid[y] = grid[y] || [];
            const cell = grid[y][x];
            if (!cell) {{
              grid[y][x] = [pixel.x, pixel.y, value];
            }} else {{
              cell[0] = (cell[0] * cell[2] + pixel.x * value) / (cell[2] + value);
              cell[1] = (cell[1] * cell[2] + pixel.y * value) / (cell[2] + value);
              cell[2] += value;
            }}
            hasCells = true;
          }}

          if (!hasCells) return;

          for (const row of grid) {{
            if (!row) continue;
            for (const cell of row) {{
              if (!cell) continue;
              ctx.globalAlpha = Math.min(Math.max(cell[2] / maxValue, minOpacity), 1);
              ctx.drawImage(circle, Math.round(cell[0]) - drawRadius, Math.round(cell[1]) - drawRadius);
            }}
          }}
          ctx.globalAlpha = 1;

          const image = ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
          this.colorize(image.data, this.getGradient());
          ctx.putImageData(image, 0, 0);
        }}

        getExpandedGeoBounds(projection, topLeft, width, height, margin) {{
          const northWest = projection.fromDivPixelToLatLng(new google.maps.Point(topLeft.x - margin, topLeft.y - margin));
          const southEast = projection.fromDivPixelToLatLng(new google.maps.Point(topLeft.x + width + margin, topLeft.y + height + margin));
          if (!northWest || !southEast) return null;
          return {{
            north: northWest.lat(),
            south: southEast.lat(),
            west: northWest.lng(),
            east: southEast.lng()
          }};
        }}

        containsLatLng(bounds, lat, lng) {{
          if (lat > bounds.north || lat < bounds.south) return false;
          if (bounds.west <= bounds.east) return lng >= bounds.west && lng <= bounds.east;
          return lng >= bounds.west || lng <= bounds.east;
        }}

        getDrawViewport(mapDiv) {{
          const fullscreenElement = document.fullscreenElement || document.webkitFullscreenElement;
          const inFullscreen = fullscreenElement && (
            fullscreenElement === mapDiv ||
            fullscreenElement.contains(mapDiv) ||
            mapDiv.contains(fullscreenElement)
          );
          if (inFullscreen) {{
            const visualViewport = window.visualViewport;
            const rect = fullscreenElement.getBoundingClientRect();
            return {{
              width: Math.max(1, Math.round((visualViewport && visualViewport.width) || window.innerWidth || rect.width || mapDiv.clientWidth)),
              height: Math.max(1, Math.round((visualViewport && visualViewport.height) || window.innerHeight || rect.height || mapDiv.clientHeight))
            }};
          }}
          return {{
            width: Math.max(1, mapDiv.clientWidth),
            height: Math.max(1, mapDiv.clientHeight)
          }};
        }}

        getCircle(radius, blur) {{
          if (this.circle && this.circleRadius === radius && this.circleBlur === blur) return this.circle;
          const drawRadius = radius + blur;
          const circle = document.createElement("canvas");
          const ctx = circle.getContext("2d");
          circle.width = circle.height = drawRadius * 2;
          ctx.shadowOffsetX = ctx.shadowOffsetY = drawRadius * 2;
          ctx.shadowBlur = blur;
          ctx.shadowColor = "black";
          ctx.beginPath();
          ctx.arc(-drawRadius, -drawRadius, radius, 0, Math.PI * 2, true);
          ctx.closePath();
          ctx.fill();
          this.circle = circle;
          this.circleRadius = radius;
          this.circleBlur = blur;
          return circle;
        }}

        getGradient() {{
          const gradient = this.options.gradient || {{ 0.4: "blue", 0.6: "cyan", 0.7: "lime", 0.8: "yellow", 1.0: "red" }};
          const key = JSON.stringify(gradient);
          if (this.gradientPixels && this.gradientKey === key) return this.gradientPixels;
          const canvas = document.createElement("canvas");
          const ctx = canvas.getContext("2d", {{ willReadFrequently: true }});
          const linearGradient = ctx.createLinearGradient(0, 0, 0, 256);
          canvas.width = 1;
          canvas.height = 256;
          for (const stop in gradient) {{
            linearGradient.addColorStop(Number(stop), gradient[stop]);
          }}
          ctx.fillStyle = linearGradient;
          ctx.fillRect(0, 0, 1, 256);
          this.gradientPixels = ctx.getImageData(0, 0, 1, 256).data;
          this.gradientKey = key;
          return this.gradientPixels;
        }}

        colorize(pixels, gradient) {{
          for (let i = 0; i < pixels.length; i += 4) {{
            const j = pixels[i + 3] * 4;
            if (j) {{
              pixels[i] = gradient[j];
              pixels[i + 1] = gradient[j + 1];
              pixels[i + 2] = gradient[j + 2];
            }}
          }}
        }}

        onRemove() {{
          for (const listener of this.listeners) {{
            google.maps.event.removeListener(listener);
          }}
          this.listeners = [];
          if (this.resizeObserver) {{
            this.resizeObserver.disconnect();
            this.resizeObserver = null;
          }}
          for (const timer of this.delayedDrawTimers) {{
            window.clearTimeout(timer);
          }}
          this.delayedDrawTimers = [];
          window.removeEventListener("resize", this.handleResize);
          document.removeEventListener("fullscreenchange", this.handleResize);
          if (this.canvas) {{
            this.canvas.remove();
            this.canvas = null;
          }}
        }}
      }}

      const layer = new CanvasHeatmapOverlay(spec.data, spec.options, config.zoom);
      layer.setMap(map);
      track(spec.name, layer, visible => layer.setMap(visible ? map : null), {{ hideInStreetView: true }});
    }}
  }}

  panorama.addListener("visible_changed", () => {{
    streetViewVisible = panorama.getVisible();
    for (const entry of namedLayers) {{
      entry.applyVisibility();
    }}
  }});

  for (const legend of legends) {{
    const legendControl = document.createElement("div");
    legendControl.style.background = "#fff";
    legendControl.style.border = "1px solid #dadce0";
    legendControl.style.borderRadius = "4px";
    legendControl.style.boxShadow = "0 1px 4px rgba(0,0,0,.2)";
    legendControl.style.font = "12px Arial,sans-serif";
    legendControl.style.margin = "10px";
    legendControl.style.padding = "8px";
    legendControl.dataset.fgmChoroplethLegend = "true";
    if (legend.caption) {{
      const caption = document.createElement("div");
      caption.style.fontWeight = "600";
      caption.style.marginBottom = "6px";
      caption.textContent = legend.caption;
      legendControl.appendChild(caption);
    }}
    for (const entry of legend.entries || []) {{
      const row = document.createElement("div");
      row.style.alignItems = "center";
      row.style.display = "flex";
      row.style.gap = "6px";
      row.style.margin = "2px 0";
      const swatch = document.createElement("span");
      swatch.style.background = entry.color;
      swatch.style.border = "1px solid rgba(0,0,0,.25)";
      swatch.style.display = "inline-block";
      swatch.style.height = "10px";
      swatch.style.width = "18px";
      const label = document.createElement("span");
      label.textContent = entry.label;
      row.appendChild(swatch);
      row.appendChild(label);
      legendControl.appendChild(row);
    }}
    map.controls[google.maps.ControlPosition.LEFT_BOTTOM].push(legendControl);
  }}

  const control = document.getElementById("{map_id}_layers");
  if (control && namedLayers.length) {{
    control.hidden = false;
    for (const entry of namedLayers) {{
      const label = document.createElement("label");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = true;
      checkbox.addEventListener("change", () => {{
        entry.layerVisible = checkbox.checked;
        entry.applyVisibility();
      }});
      label.appendChild(checkbox);
      label.appendChild(document.createTextNode(" " + entry.name));
      control.appendChild(label);
    }}
    map.controls[google.maps.ControlPosition.TOP_RIGHT].push(control);
  }}
}};
</script>
<script>
(function() {{
  if (window.google && google.maps && google.maps.importLibrary) {{
    window.{callback}();
    return;
  }}
  if (document.querySelector("script[data-fgm-google='{callback}']")) return;
  const script = document.createElement("script");
  script.async = true;
  script.dataset.fgmGoogle = "{callback}";
  script.src = "https://maps.googleapis.com/maps/api/js?key=" + encodeURIComponent({api_key}) + "&loading=async&callback={callback}";
  document.head.appendChild(script);
}})();
</script>"""
