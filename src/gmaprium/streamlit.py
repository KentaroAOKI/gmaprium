"""Streamlit integration helpers."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Sequence

from .elements import Map


_FRONTEND_DIR = Path(__file__).with_name("frontend")
_DEFAULT_RETURNED_OBJECTS = ["all_drawings", "last_active_drawing"]


def st_gmaprium(
    map_obj: Map,
    *,
    height: int | None = None,
    width: int | None = None,
    scrolling: bool = False,
    returned_objects: Sequence[str] | None = None,
    key: str | None = None,
    default: Any | None = None,
    **kwargs: Any,
) -> Any:
    """Render a gmaprium map in Streamlit and return interaction state."""
    component = _declare_component()
    component_height = height or _height_to_pixels(map_obj.height)
    selected_objects = list(_DEFAULT_RETURNED_OBJECTS if returned_objects is None else returned_objects)
    component_default = _default_component_value(selected_objects) if default is None else default
    map_obj._id = _stable_map_dom_id(key)

    return component(
        html=map_obj.render_html(),
        height=component_height,
        width=width,
        scrolling=scrolling,
        returned_objects=selected_objects,
        default=component_default,
        key=key,
        **kwargs,
    )


def _declare_component() -> Any:
    try:
        import streamlit.components.v1 as components
    except ImportError as exc:
        raise RuntimeError('streamlit is required. Install with: pip install "gmaprium[streamlit]"') from exc

    return components.declare_component("st_gmaprium", path=str(_FRONTEND_DIR))


def _stable_map_dom_id(key: str | None) -> str:
    base = str(key or "default")
    slug = re.sub(r"[^0-9A-Za-z_]+", "_", base).strip("_") or "default"
    if slug[0].isdigit():
        slug = f"map_{slug}"
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:8]
    return f"fgm_{slug}_{digest}"


def _default_component_value(returned_objects: Sequence[str]) -> dict[str, Any]:
    values = {
        "all_drawings": [],
        "last_active_drawing": None,
    }
    return {name: values[name] for name in returned_objects if name in values}


def _height_to_pixels(value: str) -> int:
    if value.endswith("px"):
        try:
            return int(value[:-2])
        except ValueError:
            return 500
    return 500
