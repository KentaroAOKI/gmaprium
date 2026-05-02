from __future__ import annotations

import sys
import types

import pytest

from gmaprium import Map, st_google_map
from gmaprium.streamlit import _height_to_pixels


def test_height_to_pixels() -> None:
    assert _height_to_pixels("600px") == 600
    assert _height_to_pixels("80%") == 500
    assert _height_to_pixels("badpx") == 500


def test_st_google_map_requires_streamlit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "streamlit", None)
    monkeypatch.delitem(sys.modules, "streamlit.components.v1", raising=False)

    with pytest.raises(RuntimeError, match="streamlit is required"):
        st_google_map(Map([35, 139], api_key="key"))


def test_st_google_map_calls_components_html(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def html(content: str, **kwargs: object) -> str:
        calls.append((content, kwargs))
        return "component"

    streamlit_module = types.ModuleType("streamlit")
    components_module = types.ModuleType("streamlit.components")
    v1_module = types.ModuleType("streamlit.components.v1")
    v1_module.html = html  # type: ignore[attr-defined]
    components_module.v1 = v1_module  # type: ignore[attr-defined]
    streamlit_module.components = components_module  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "streamlit", streamlit_module)
    monkeypatch.setitem(sys.modules, "streamlit.components", components_module)
    monkeypatch.setitem(sys.modules, "streamlit.components.v1", v1_module)

    result = st_google_map(Map([35, 139], api_key="key", height="640px"), scrolling=True)

    assert result == "component"
    assert calls
    assert calls[0][0].startswith("<!doctype html>")
    assert calls[0][1]["height"] == 640
    assert calls[0][1]["scrolling"] is True
