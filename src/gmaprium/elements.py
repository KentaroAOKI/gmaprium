"""Folium-style map elements for Google Maps output."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, Sequence


Location = Sequence[float]
_MAP_TYPES = {"roadmap", "satellite", "hybrid", "terrain"}
_DEMO_MAP_ID = "DEMO_MAP_ID"


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
        needs_marker = any(spec["type"] == "marker" for spec in specs)
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
  const {{ Map, InfoWindow, Polyline, Polygon, Circle }} = await google.maps.importLibrary("maps");
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
