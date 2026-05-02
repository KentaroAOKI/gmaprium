from __future__ import annotations

import json
from pathlib import Path

import pytest

from gmaprium import Circle, GeoJson, GoogleMapsError, HeatMap, LayerControl, Map, Marker, Polygon, Polyline


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
    assert "fromLatLngToContainerPixel" in html
    assert "dataset.fgmHeatmap" in html
    assert 'this.canvas.style.zIndex = "5"' in html
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
    assert '"idle", () => this.draw()' in html
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
