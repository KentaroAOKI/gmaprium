"""Utilities for adding Google Maps tile layers to Folium maps."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlencode

GoogleMapType = Literal["roadmap", "satellite", "terrain", "hybrid"]

_GOOGLE_TILE_ENDPOINT = "https://mt1.google.com/vt/lyrs={layer}&x={x}&y={y}&z={z}"
_MAP_TYPE_TO_LAYER: dict[GoogleMapType, str] = {
    "roadmap": "m",
    "satellite": "s",
    "terrain": "p",
    "hybrid": "y",
}


def google_tiles_url(map_type: GoogleMapType = "roadmap", api_key: str | None = None) -> str:
    """Return a Google Maps tile URL template for Folium."""
    layer = _MAP_TYPE_TO_LAYER.get(map_type)
    if layer is None:
        supported = ", ".join(sorted(_MAP_TYPE_TO_LAYER))
        raise ValueError(f"Unsupported map_type {map_type!r}. Expected one of: {supported}.")

    url = _GOOGLE_TILE_ENDPOINT.format(layer=layer, x="{x}", y="{y}", z="{z}")
    if api_key:
        url = f"{url}&{urlencode({'key': api_key})}"
    return url


def add_google_tiles(
    map_obj: object,
    *,
    api_key: str | None = None,
    map_type: GoogleMapType = "roadmap",
    name: str | None = None,
    attr: str = "Google",
    overlay: bool = False,
    control: bool = True,
    show: bool = True,
) -> object:
    """Add a Google Maps tile layer to a Folium map and return the layer."""
    try:
        import folium
    except ImportError as exc:  # pragma: no cover - dependency metadata should install folium
        raise RuntimeError("folium is required to add Google Maps tiles.") from exc

    layer = folium.TileLayer(
        tiles=google_tiles_url(map_type=map_type, api_key=api_key),
        name=name or f"Google {map_type.title()}",
        attr=attr,
        overlay=overlay,
        control=control,
        show=show,
    )
    layer.add_to(map_obj)
    return layer
