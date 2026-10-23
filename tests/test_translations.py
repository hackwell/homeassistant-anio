"""Every entity translation key has a name in all translation files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.anio import (
    binary_sensor,
    button,
    device_tracker,
    notify,
    select,
    sensor,
    switch,
)
from custom_components.anio.const import RING_PROFILES

COMPONENT_DIR = Path(__file__).parent.parent / "custom_components" / "anio"
TRANSLATION_FILES = [
    COMPONENT_DIR / "strings.json",
    COMPONENT_DIR / "translations" / "en.json",
    COMPONENT_DIR / "translations" / "de.json",
]
PLATFORMS = {
    "binary_sensor": binary_sensor,
    "button": button,
    "device_tracker": device_tracker,
    "notify": notify,
    "select": select,
    "sensor": sensor,
    "switch": switch,
}


def _translation_keys() -> list[tuple[str, str]]:
    """Collect (platform, translation_key) of all entity classes."""
    keys = []
    for platform, module in PLATFORMS.items():
        for obj in vars(module).values():
            if not isinstance(obj, type) or obj.__module__ != module.__name__:
                continue
            # Home Assistant turns _attr_translation_key into a property and
            # keeps the class value under "__attr_translation_key"
            key = obj.__dict__.get("__attr_translation_key")
            if isinstance(key, str):
                keys.append((platform, key))
    return keys


def test_all_entities_have_translation_keys() -> None:
    """Test every platform defines translated entities."""
    platforms = {platform for platform, _ in _translation_keys()}
    assert platforms == set(PLATFORMS)
    assert len(_translation_keys()) == 15


@pytest.mark.parametrize("path", TRANSLATION_FILES, ids=lambda p: p.name)
def test_every_key_is_translated(path: Path) -> None:
    """Test each translation key has a name in each file."""
    entity = json.loads(path.read_text(encoding="utf-8"))["entity"]
    for platform, key in _translation_keys():
        assert entity[platform][key]["name"], f"{path.name}: {platform}.{key}"


@pytest.mark.parametrize("path", TRANSLATION_FILES, ids=lambda p: p.name)
def test_ring_profiles_translated(path: Path) -> None:
    """Test every ring profile option has a translation."""
    states = json.loads(path.read_text(encoding="utf-8"))["entity"]["select"][
        "ring_profile"
    ]["state"]
    assert set(states) == set(RING_PROFILES)


def test_geofence_name_has_placeholder() -> None:
    """Test the geofence name keeps the {geofence_name} placeholder."""
    for path in TRANSLATION_FILES:
        name = json.loads(path.read_text(encoding="utf-8"))["entity"]["binary_sensor"][
            "geofence"
        ]["name"]
        assert "{geofence_name}" in name, path.name
