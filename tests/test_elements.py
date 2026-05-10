from __future__ import annotations

import builtins
import json
from pathlib import Path

import pytest

from gmaprium import Choropleth, Circle, Draw, GeoJson, GoogleMapsError, HeatMap, LayerControl, Map, Marker, Polygon, Polyline


def _sample_choropleth_geojson() -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"id": "a"}, "geometry": None},
            {"type": "Feature", "properties": {"id": "b"}, "geometry": None},
            {"type": "Feature", "properties": {"id": "c"}, "geometry": None},
        ],
    }


def test_map_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)

    with pytest.raises(GoogleMapsError, match="API key"):
        Map([35.0, 139.0]).render_html()


def test_map_rejects_unknown_map_type() -> None:
    with pytest.raises(ValueError, match="Unsupported map_type"):
        Map([35.0, 139.0], map_type="unknown")


def test_map_uses_environment_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "env-key")

    html = Map([35.0, 139.0], zoom_start=12).render_fragment()

    assert "env-key" in html
    assert "<!doctype html>" not in html
    assert "google.maps.importLibrary" in html


def test_render_html_wraps_fragment() -> None:
    html = Map([35.0, 139.0], api_key="test-key").render_html()

    assert html.startswith("<!doctype html>")
    assert "<body>" in html
    assert "test-key" in html


def test_map_fullscreen_control_option() -> None:
    disabled = Map([35.0, 139.0], api_key="test-key", fullscreen_control=False).render_fragment()
    enabled = Map([35.0, 139.0], api_key="test-key", fullscreen_control=True).render_fragment()
    default = Map([35.0, 139.0], api_key="test-key").render_fragment()

    assert '"fullscreenControl":false' in disabled
    assert '"fullscreenControl":true' in enabled
    assert "fullscreenControl" not in default


def test_map_fullscreen_control_argument_overrides_raw_options() -> None:
    html = Map(
        [35.0, 139.0],
        api_key="test-key",
        fullscreen_control=True,
        options={"fullscreenControl": False},
    ).render_fragment()

    assert '"fullscreenControl":true' in html
    assert '"fullscreenControl":false' not in html


def test_map_street_view_control_option() -> None:
    disabled = Map([35.0, 139.0], api_key="test-key", street_view_control=False).render_fragment()
    enabled = Map([35.0, 139.0], api_key="test-key", street_view_control=True).render_fragment()
    default = Map([35.0, 139.0], api_key="test-key").render_fragment()

    assert '"streetViewControl":false' in disabled
    assert '"streetViewControl":true' in enabled
    assert "streetViewControl" not in default


def test_map_street_view_control_argument_overrides_raw_options() -> None:
    html = Map(
        [35.0, 139.0],
        api_key="test-key",
        street_view_control=True,
        options={"streetViewControl": False},
    ).render_fragment()

    assert '"streetViewControl":true' in html
    assert '"streetViewControl":false' not in html


def test_repr_html_returns_fragment_for_notebooks() -> None:
    html = Map([35.0, 139.0], api_key="test-key", height="420px")._repr_html_()

    assert html.startswith("<div ")
    assert "height:420px" in html
    assert "srcdoc=" not in html
    assert "fgm_" in html


def test_marker_render_uses_advanced_marker_with_demo_map_id() -> None:
    m = Map([35.0, 139.0], api_key="test-key")
    Marker([35.0, 139.0], icon="marker.png").add_to(m)

    html = m.render_fragment()

    assert "new AdvancedMarkerElement" in html
    assert "new google.maps.Marker" not in html
    assert 'marker.addListener("gmp-click"' in html
    assert 'marker.addListener("click"' not in html
    assert '"mapId":"DEMO_MAP_ID"' in html


def test_save_writes_html(tmp_path: Path) -> None:
    output = tmp_path / "map.html"

    Map([35.0, 139.0], api_key="test-key").save(output)

    assert output.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_marker_spec() -> None:
    spec = Marker([35.0, 139.0], popup="Hello", tooltip="Tokyo", draggable=True, name="A").to_spec()

    assert spec["type"] == "marker"
    assert spec["position"] == {"lat": 35.0, "lng": 139.0}
    assert spec["popup"] == "Hello"
    assert spec["tooltip"] == "Tokyo"
    assert spec["draggable"] is True
    assert spec["name"] == "A"


def test_shape_specs() -> None:
    assert Polyline([[1, 2], [3, 4]], color="#000", weight=2).to_spec()["path"] == [
        {"lat": 1.0, "lng": 2.0},
        {"lat": 3.0, "lng": 4.0},
    ]
    assert Polygon([[1, 2], [3, 4], [5, 6]]).to_spec()["paths"][0] == {"lat": 1.0, "lng": 2.0}
    assert Circle([1, 2], 100).to_spec()["center"] == {"lat": 1.0, "lng": 2.0}


def test_add_to_and_add_child_return_child() -> None:
    m = Map([35.0, 139.0], api_key="test-key")
    marker = Marker([35.0, 139.0])

    assert marker.add_to(m) is marker
    assert m.add_child(Polyline([[1, 2], [3, 4]])) is m.children[-1]


def test_geojson_accepts_dict_path_geo_interface_and_to_json(tmp_path: Path) -> None:
    geojson = {"type": "FeatureCollection", "features": []}
    path = tmp_path / "data.json"
    path.write_text(json.dumps(geojson), encoding="utf-8")

    class GeoInterface:
        __geo_interface__ = geojson

    class ToJson:
        def to_json(self) -> str:
            return json.dumps(geojson)

    assert GeoJson(geojson).to_spec()["data"] == geojson
    assert GeoJson(path).to_spec()["data"] == geojson
    assert GeoJson(GeoInterface()).to_spec()["data"] == geojson
    assert GeoJson(ToJson()).to_spec()["data"] == geojson


def test_geojson_style_function_receives_sample_feature() -> None:
    geojson = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"color": "#f00"}, "geometry": None}],
    }

    spec = GeoJson(geojson, style_function=lambda feature: {"fillColor": feature["properties"]["color"]}).to_spec()

    assert spec["style"] == {"fillColor": "#f00"}


def test_choropleth_styles_geojson_with_joined_data() -> None:
    geojson = _sample_choropleth_geojson()

    spec = Choropleth(
        geojson,
        data={"a": 10, "b": 20, "c": float("nan")},
        key_on="feature.properties.id",
        bins=[0, 15, 30],
        fill_color="YlOrRd",
        nan_fill_color="#999999",
        fill_opacity=0.7,
        nan_fill_opacity=0.2,
        line_color="#333333",
        line_weight=2,
        line_opacity=0.8,
        name="Choropleth",
        legend_name="Values",
        highlight=True,
    ).to_spec()

    features = spec["data"]["features"]

    assert spec["type"] == "choropleth"
    assert spec["name"] == "Choropleth"
    assert features[0]["properties"]["__gmaprium_choropleth_style"] == {
        "strokeWeight": 2,
        "strokeOpacity": 0.8,
        "strokeColor": "#333333",
        "fillOpacity": 0.7,
        "fillColor": "#ffffcc",
    }
    assert features[1]["properties"]["__gmaprium_choropleth_style"]["fillColor"] == "#800026"
    assert features[2]["properties"]["__gmaprium_choropleth_style"]["fillColor"] == "#999999"
    assert features[2]["properties"]["__gmaprium_choropleth_style"]["fillOpacity"] == 0.2
    assert spec["highlightStyle"] == {"strokeWeight": 4, "fillOpacity": 0.8999999999999999}
    assert spec["legend"] == {
        "caption": "Values",
        "entries": [
            {"color": "#ffffcc", "label": "0 - 15"},
            {"color": "#800026", "label": "15 - 30"},
        ],
    }


def test_choropleth_accepts_list_series_and_dataframe_like_data() -> None:
    geojson = _sample_choropleth_geojson()

    class SeriesLike:
        def to_dict(self) -> dict[str, int]:
            return {"a": 1, "b": 2}

    class FrameColumn:
        def __init__(self, values: dict[str, int]) -> None:
            self.values = values

        def to_dict(self) -> dict[str, int]:
            return self.values

    class FrameIndexed:
        def __init__(self, values: dict[str, int]) -> None:
            self.values = values

        def __getitem__(self, column: str) -> FrameColumn:
            assert column == "value"
            return FrameColumn(self.values)

    class FrameLike:
        def set_index(self, column: str) -> FrameIndexed:
            assert column == "id"
            return FrameIndexed({"a": 1, "b": 2})

    list_spec = Choropleth(geojson, data=[("a", 1), ("b", 2)], key_on="feature.properties.id").to_spec()
    series_spec = Choropleth(geojson, data=SeriesLike(), key_on="feature.properties.id").to_spec()
    frame_spec = Choropleth(geojson, data=FrameLike(), columns=["id", "value"], key_on="feature.properties.id").to_spec()

    assert list_spec["data"]["features"][0]["properties"]["__gmaprium_choropleth_style"]["fillOpacity"] == 0.6
    assert series_spec["data"]["features"][0]["properties"]["__gmaprium_choropleth_style"]["fillOpacity"] == 0.6
    assert frame_spec["data"]["features"][0]["properties"]["__gmaprium_choropleth_style"]["fillOpacity"] == 0.6


def test_choropleth_default_style_without_data() -> None:
    spec = Choropleth(_sample_choropleth_geojson(), fill_color="#123456", fill_opacity=0.4).to_spec()

    assert spec["legend"] is None
    assert spec["data"]["features"][0]["properties"]["__gmaprium_choropleth_style"]["fillColor"] == "#123456"
    assert spec["data"]["features"][0]["properties"]["__gmaprium_choropleth_style"]["fillOpacity"] == 0.4


def test_choropleth_validates_key_bins_topojson_and_jenks(monkeypatch: pytest.MonkeyPatch) -> None:
    geojson = _sample_choropleth_geojson()

    original_import = builtins.__import__

    def import_without_jenkspy(name: str, *args: object, **kwargs: object) -> object:
        if name == "jenkspy":
            raise ImportError("No module named jenkspy")
        return original_import(name, *args, **kwargs)

    with pytest.raises(ValueError, match="key_on"):
        Choropleth(geojson, data={"a": 1}, key_on="feature.properties.missing").to_spec()

    with pytest.raises(ValueError, match="provided bins"):
        Choropleth(geojson, data={"a": 100}, key_on="feature.properties.id", bins=[0, 10]).to_spec()

    with pytest.raises(NotImplementedError, match="topojson"):
        Choropleth(geojson, topojson="objects.states")

    monkeypatch.setattr(builtins, "__import__", import_without_jenkspy)
    with pytest.raises(RuntimeError, match="jenkspy"):
        Choropleth(geojson, data={"a": 1}, key_on="feature.properties.id", use_jenks=True).to_spec()


def test_draw_spec_defaults_and_options() -> None:
    spec = Draw(
        export=True,
        filename="drawn.geojson",
        position="bottomright",
        show_geometry_on_click=False,
        draw_options={"circle": False, "strokeColor": "#000"},
        edit_options={"poly": {"allowIntersection": False}},
        on={"click": "handler"},
    ).to_spec()

    assert spec == {
        "type": "draw",
        "export": True,
        "filename": "drawn.geojson",
        "position": "bottomright",
        "showGeometryOnClick": False,
        "drawOptions": {"circle": False, "strokeColor": "#000"},
        "editOptions": {"poly": {"allowIntersection": False}},
        "events": ["click"],
    }


def test_draw_rejects_unsupported_options() -> None:
    with pytest.raises(ValueError, match="Unsupported Draw position"):
        Draw(position="middle")

    with pytest.raises(NotImplementedError, match="feature_group"):
        Draw(feature_group=object())


def test_render_includes_draw_control_assets() -> None:
    m = Map([35.0, 139.0], api_key="test-key")
    Draw(
        export=True,
        filename="features.geojson",
        position="topleft",
        draw_options={"marker": True, "polyline": False, "polygon": True, "rectangle": False, "circle": False},
    ).add_to(m)

    html = m.render_fragment()

    assert '"type":"draw"' in html
    assert '"export":true' in html
    assert '"filename":"features.geojson"' in html
    assert '"marker":true' in html
    assert '"polyline":false' in html
    assert '"polygon":true' in html
    assert '"rectangle":false' in html
    assert '"circle":false' in html
    assert '"mapId":"DEMO_MAP_ID"' in html
    assert "setupDrawControl(spec)" in html
    assert "dataset.fgmDrawControl" in html
    assert "drawControlPosition(spec.position)" in html
    assert "google.maps.ControlPosition.TOP_LEFT" in html
    assert 'button.dataset.fgmDrawMode = nextMode' in html
    assert 'separator.dataset.fgmDrawSeparator = "true"' in html
    assert 'button.dataset.fgmDrawAction = label.toLowerCase()' in html
    assert 'button.style.background = "#fff"' in html
    assert 'button.style.border = "1px solid #dadce0"' in html
    assert 'button.style.color = "#202124"' in html
    assert 'button.style.background = selected ? "#1a73e8" : "#fff"' in html
    assert 'button.style.borderColor = selected ? "#1a73e8" : "#dadce0"' in html
    assert 'if (enabled("marker")) addButton("Marker", "marker")' in html
    assert 'if (enabled("polyline")) addButton("Line", "polyline")' in html
    assert 'if (enabled("polygon")) addButton("Polygon", "polygon")' in html
    assert 'if (enabled("rectangle")) addButton("Rectangle", "rectangle")' in html
    assert 'if (enabled("circle")) addButton("Circle", "circle")' in html
    assert "finishButton = addActionButton(\"Finish\", () => finishPath())" in html
    assert "function updateFinishButton()" in html
    assert 'mode === "polyline" && draftPath.length >= 2' in html
    assert 'mode === "polygon" && draftPath.length >= 3' in html
    assert "function updatePathPreview(latLng)" in html
    assert "const previewPath = [...draftPath, latLng]" in html
    assert "updatePathPreview(event.latLng)" in html
    assert "draftOverlay.setPath(draftPath)" in html
    assert "draftOverlay.setPaths(draftPath)" in html
    assert "new Polygon({ map, paths: draftPath, clickable: false" in html
    assert "new Polyline({ map, path: draftPath, clickable: false" in html
    assert "finishButton.disabled = !canFinish" in html
    assert 'finishButton.style.background = canFinish ? "#1a73e8" : "#f1f3f4"' in html
    assert 'finishButton.style.borderColor = canFinish ? "#1a73e8" : "#dadce0"' in html
    assert 'finishButton.style.opacity = canFinish ? "1" : "0.65"' in html
    assert "function updateDrawnActionButtons()" in html
    assert "const hasDrawnItems = drawnItems.length > 0" in html
    assert "clearButton.disabled = !hasDrawnItems" in html
    assert 'clearButton.style.background = hasDrawnItems ? "#fce8e6" : "#f1f3f4"' in html
    assert 'exportLink.setAttribute("aria-disabled", hasDrawnItems ? "false" : "true")' in html
    assert 'exportLink.style.background = hasDrawnItems ? "#e6f4ea" : "#f1f3f4"' in html
    assert "if (!drawnItems.length)" in html
    assert "event.preventDefault()" in html
    assert 'clearButton = addActionButton("Clear", () => clearDrawnItems(), { background: "#fce8e6"' in html
    assert 'exportLink.style.background = "#e6f4ea"' in html
    assert 'exportLink.style.color = "#137333"' in html
    assert "clickable: false" in html
    assert "draftOverlay.setOptions({ clickable: spec.showGeometryOnClick })" in html
    assert "new AdvancedMarkerElement" in html
    assert "new Polyline" in html
    assert "new Polygon" in html
    assert "new Rectangle" in html
    assert "new Circle" in html
    assert "toFeatureCollection()" in html
    assert 'exportLink.dataset.fgmDrawExport = "true"' in html
    assert "radiusMeters" in html
    assert "gmaprium-draw-created" in html
    assert "gmaprium-draw-updated" in html
    assert "function drawState(lastFeature)" in html
    assert "all_drawings: drawnItems.map(toFeature)" in html
    assert "last_active_drawing: lastFeature" in html
    assert "dispatchDrawState(feature)" in html
    assert "dispatchDrawState(null)" in html
    assert "alert(JSON.stringify(toFeature(item)))" in html
    assert 'const clickEvent = type === "marker" ? "gmp-click" : "click"' in html
    assert "latLngCoordinates(item.overlay.position)" in html
    assert "FeatureCollection" in html


def test_render_includes_choropleth_assets_and_legend() -> None:
    m = Map([35.0, 139.0], api_key="test-key")
    Choropleth(
        _sample_choropleth_geojson(),
        data={"a": 1, "b": 2},
        key_on="feature.properties.id",
        name="Areas",
        legend_name="Area values",
        highlight=True,
    ).add_to(m)
    LayerControl().add_to(m)

    html = m.render_fragment()

    assert '"type":"choropleth"' in html
    assert "__gmaprium_choropleth_style" in html
    assert 'feature.getProperty("__gmaprium_choropleth_style")' in html
    assert 'layer.addListener("mouseover"' in html
    assert 'layer.addListener("mouseout"' in html
    assert "overrideStyle(event.feature, spec.highlightStyle)" in html
    assert "legendControl.dataset.fgmChoroplethLegend" in html
    assert "LEFT_BOTTOM" in html
    assert "Area values" in html
    assert "Areas" in html
    assert "entry.layerVisible = checkbox.checked" in html


def test_heatmap_accepts_supported_point_formats() -> None:
    spec = HeatMap(
        [[35, 139], [36, 140, 2], {"location": [37, 141], "weight": 3}],
        radius=25,
        blur=15,
        min_opacity=0.05,
        max_zoom=18,
        max_value=3,
        gradient={0.4: "blue", 0.65: "lime", 1.0: "red"},
    ).to_spec()

    assert spec["type"] == "heatmap"
    assert spec["data"] == [
        {"position": [139.0, 35.0], "weight": 1.0},
        {"position": [140.0, 36.0], "weight": 2.0},
        {"position": [141.0, 37.0], "weight": 3.0},
    ]
    assert spec["options"]["radiusPixels"] == 25
    assert spec["options"]["blurPixels"] == 15
    assert spec["options"]["minOpacity"] == 0.05
    assert spec["options"]["maxZoom"] == 18
    assert spec["options"]["max"] == 3
    assert spec["options"]["gradient"] == {0.4: "blue", 0.65: "lime", 1.0: "red"}
    assert spec["options"]["scaleRadiusWithZoom"] is False


def test_heatmap_default_gradient_matches_simpleheat() -> None:
    spec = HeatMap([[35, 139]]).to_spec()

    assert spec["options"]["radiusPixels"] == 25
    assert spec["options"]["blurPixels"] == 15
    assert spec["options"]["minOpacity"] == 0.05
    assert spec["options"]["maxZoom"] == 18
    assert spec["options"]["max"] == 1.0
    assert spec["options"]["gradient"] == {0.4: "blue", 0.6: "cyan", 0.7: "lime", 0.8: "yellow", 1.0: "red"}


def test_render_includes_optional_heatmap_and_layer_control_assets() -> None:
    m = Map([35.0, 139.0], api_key="test-key")
    HeatMap([[35, 139]], name="Heat").add_to(m)
    LayerControl().add_to(m)

    html = m.render_fragment()

    assert "deck.gl" not in html
    assert "CanvasHeatmapOverlay" in html
    assert "google.maps.OverlayView" in html
    assert "fromLatLngToDivPixel" in html
    assert "fromLatLngToContainerPixel" not in html
    assert "dataset.fgmHeatmap" in html
    assert 'style="position:relative;width:100%;height:100%;"' in html
    assert ":fullscreen" in html
    assert "height:100vh!important" in html
    assert "width:100vw!important" in html
    assert ":-webkit-full-screen" in html
    assert ".gm-style" in html
    assert "this.getPanes().overlayLayer.appendChild(this.canvas)" in html
    assert "this.canvas.parentElement !== panes.overlayLayer" in html
    assert "panes.overlayLayer.appendChild(this.canvas)" in html
    assert "floatPane.appendChild(this.canvas)" not in html
    assert "projection.fromLatLngToDivPixel(map.getCenter())" in html
    assert "centerPixel.x - width / 2" in html
    assert "centerPixel.y - height / 2" in html
    assert "if (this.canvas.width !== width) this.canvas.width = width" in html
    assert "if (this.canvas.height !== height) this.canvas.height = height" in html
    assert "getDrawViewport(mapDiv)" in html
    assert "document.fullscreenElement || document.webkitFullscreenElement" in html
    assert "window.visualViewport" in html
    assert "window.innerHeight" in html
    assert "mapDiv.clientHeight" in html
    assert "console.log" not in html
    assert "drawScheduled" in html
    assert "delayedDrawScheduled" in html
    assert "delayedDrawTimers" in html
    assert "requestAnimationFrame" in html
    assert '"bounds_changed", () => this.scheduleDraw()' in html
    assert '"zoom_changed", () => this.scheduleDraw()' in html
    assert "new ResizeObserver(() => this.scheduleDraw(true))" in html
    assert "getExpandedGeoBounds(projection, topLeft, width, height, drawRadius)" in html
    assert "fromDivPixelToLatLng" in html
    assert "!this.containsLatLng(geoBounds, lat, lng)" in html
    assert "let hasCells = false" in html
    assert "if (!hasCells) return" in html
    assert "mapBounds.getNorthEast().lat()" not in html
    assert "mapBounds.getSouthWest().lng()" not in html
    assert "divPixel.x - topLeft.x" in html
    assert "divPixel.y - topLeft.y" in html
    assert "mapDiv.appendChild(this.canvas)" not in html
    assert 'this.canvas.style.zIndex = "5"' in html
    assert "ResizeObserver" in html
    assert 'window.addEventListener("resize", this.handleResize)' in html
    assert 'document.addEventListener("fullscreenchange", this.handleResize)' in html
    assert "for (const delay of [100, 300, 700])" in html
    assert "this.resizeObserver.disconnect()" in html
    assert "window.clearTimeout(timer)" in html
    assert 'window.removeEventListener("resize", this.handleResize)' in html
    assert 'document.removeEventListener("fullscreenchange", this.handleResize)' in html
    assert "cellSize = drawRadius / 2" in html
    assert "this.options.maxZoom ?? 18" in html
    assert "maxZoom - zoom" in html
    assert "blurPixels" in html
    assert "getCircle(radius, blur)" in html
    assert "getGradient()" in html
    assert "colorize(image.data" in html
    assert "putImageData(image, 0, 0)" in html
    assert "devicePixelRatio" not in html
    assert "setTransform" not in html
    assert '"idle", () => this.scheduleDraw()' in html
    assert "layer.setMap(visible ? map : null)" in html
    assert "const panorama = map.getStreetView()" in html
    assert 'panorama.addListener("visible_changed"' in html
    assert "streetViewVisible = panorama.getVisible()" in html
    assert "hideInStreetView: Boolean(options.hideInStreetView)" in html
    assert "this.layerVisible && !(this.hideInStreetView && streetViewVisible)" in html
    assert "hideInStreetView: true" in html
    assert "entry.layerVisible = checkbox.checked" in html
    assert "entry.applyVisibility()" in html
    assert "map.controls[google.maps.ControlPosition.TOP_RIGHT].push(control)" in html
    assert "data-fgm-google" in html
    assert "_layers" in html
