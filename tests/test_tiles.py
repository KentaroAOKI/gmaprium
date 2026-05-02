from __future__ import annotations

import pytest

from gmaprium import google_tiles_url


def test_google_tiles_url_defaults_to_roadmap() -> None:
    assert google_tiles_url() == "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"


@pytest.mark.parametrize(
    ("map_type", "layer"),
    [
        ("roadmap", "m"),
        ("satellite", "s"),
        ("terrain", "p"),
        ("hybrid", "y"),
    ],
)
def test_google_tiles_url_supports_google_map_types(map_type: str, layer: str) -> None:
    assert google_tiles_url(map_type=map_type) == f"https://mt1.google.com/vt/lyrs={layer}&x={{x}}&y={{y}}&z={{z}}"


def test_google_tiles_url_appends_encoded_api_key() -> None:
    assert google_tiles_url(api_key="key with spaces").endswith("&key=key+with+spaces")


def test_google_tiles_url_rejects_unknown_map_type() -> None:
    with pytest.raises(ValueError, match="Unsupported map_type"):
        google_tiles_url(map_type="unknown")  # type: ignore[arg-type]
