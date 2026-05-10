from __future__ import annotations

import sys
import types

import gmaprium
import pytest

from gmaprium import Map, st_gmaprium
from gmaprium.streamlit import _default_component_value, _height_to_pixels, _stable_map_dom_id


def test_height_to_pixels() -> None:
    assert _height_to_pixels("600px") == 600
    assert _height_to_pixels("80%") == 500
    assert _height_to_pixels("badpx") == 500


def test_default_component_value() -> None:
    assert _default_component_value(["all_drawings", "last_active_drawing", "unknown"]) == {
        "all_drawings": [],
        "last_active_drawing": None,
    }
    assert _default_component_value([]) == {}


def test_stable_map_dom_id() -> None:
    assert _stable_map_dom_id("map") == _stable_map_dom_id("map")
    assert _stable_map_dom_id(None) == _stable_map_dom_id(None)
    assert _stable_map_dom_id("map").startswith("fgm_map_")
    assert _stable_map_dom_id("123 map").startswith("fgm_map_123_map_")


def test_st_gmaprium_requires_streamlit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "streamlit", None)
    monkeypatch.delitem(sys.modules, "streamlit.components.v1", raising=False)

    with pytest.raises(RuntimeError, match="streamlit is required"):
        st_gmaprium(Map([35, 139], api_key="key"))


def test_st_gmaprium_calls_declared_component(monkeypatch: pytest.MonkeyPatch) -> None:
    declarations = []
    calls = []

    def declare_component(name: str, **kwargs: object) -> object:
        declarations.append((name, kwargs))

        def component(**component_kwargs: object) -> dict[str, object]:
            calls.append(component_kwargs)
            return {"all_drawings": [], "last_active_drawing": None}

        return component

    streamlit_module = types.ModuleType("streamlit")
    components_module = types.ModuleType("streamlit.components")
    v1_module = types.ModuleType("streamlit.components.v1")
    v1_module.declare_component = declare_component  # type: ignore[attr-defined]
    components_module.v1 = v1_module  # type: ignore[attr-defined]
    streamlit_module.components = components_module  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "streamlit", streamlit_module)
    monkeypatch.setitem(sys.modules, "streamlit.components", components_module)
    monkeypatch.setitem(sys.modules, "streamlit.components.v1", v1_module)

    result = st_gmaprium(
        Map([35, 139], api_key="key", height="640px"),
        scrolling=True,
        returned_objects=["all_drawings"],
        key="map",
    )

    assert result == {"all_drawings": [], "last_active_drawing": None}
    assert declarations
    assert declarations[0][0] == "st_gmaprium"
    assert declarations[0][1]["path"].endswith("frontend")
    assert calls
    assert calls[0]["html"].startswith("<!doctype html>")
    assert "fgm_map_" in calls[0]["html"]
    assert calls[0]["height"] == 640
    assert calls[0]["scrolling"] is True
    assert calls[0]["returned_objects"] == ["all_drawings"]
    assert calls[0]["default"] == {"all_drawings": []}
    assert calls[0]["key"] == "map"


def test_st_google_map_is_removed() -> None:
    assert not hasattr(gmaprium, "st_google_map")
