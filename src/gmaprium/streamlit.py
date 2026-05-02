"""Streamlit integration helpers."""

from __future__ import annotations

from typing import Any

from .elements import Map


def st_google_map(
    map_obj: Map,
    *,
    height: int | None = None,
    width: int | None = None,
    scrolling: bool = False,
    **kwargs: Any,
) -> Any:
    """Render a gmaprium map in Streamlit."""
    try:
        import streamlit.components.v1 as components
    except ImportError as exc:
        raise RuntimeError('streamlit is required. Install with: pip install "gmaprium[streamlit]"') from exc

    component_height = height or _height_to_pixels(map_obj.height)
    return components.html(
        map_obj.render_html(),
        height=component_height,
        width=width,
        scrolling=scrolling,
        **kwargs,
    )


def _height_to_pixels(value: str) -> int:
    if value.endswith("px"):
        try:
            return int(value[:-2])
        except ValueError:
            return 500
    return 500
