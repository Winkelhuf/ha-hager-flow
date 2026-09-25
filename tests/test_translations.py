"""
Konsistenz-Tests für die Übersetzungen.

Sie laufen ohne laufendes Home Assistant und schlagen fehl, wenn
- eine Sprache Schlüssel oder Platzhalter gegenüber Englisch verliert,
- Code und JSON auseinanderlaufen (neuer Sensor ohne Namen, neuer ENUM-Zustand ohne Text),
- ein Übersetzungs-Key gegen die Home-Assistant-Regeln verstößt.

Eine neue Sprache besteht die Tests, sobald ``translations/<sprache>.json`` alle
Schlüssel von ``en.json`` enthält.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from custom_components.hager_flow.entity.base import translation_key_for
from custom_components.hager_flow.sensor.descriptions import (
    ENTITY_DESCRIPTIONS,
    METER_SENSOR_TEMPLATES,
    SG_READY_SENSOR_TEMPLATES,
    WALLBOX_SENSOR_TEMPLATES,
)
from custom_components.hager_flow.sensor.energy import ENERGY_ENTITY_DESCRIPTIONS, METER_ENERGY_TEMPLATES
from custom_components.hager_flow.sensor.entity import BIT_OF_STATE_SENSOR, STATE_MAPS

COMPONENT = Path(__file__).parent.parent / "custom_components" / "hager_flow"
TRANSLATIONS = COMPONENT / "translations"

# Regel von hassfest für translation_keys (Unterstriche sind erlaubt)
KEY_RE = re.compile(r"^(?!.+[_-]{2})(?![_-])[a-z0-9-_]+(?<![_-])$")
PLACEHOLDER_RE = re.compile(r"\{[a-z_]+\}")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten(data: dict, prefix: str = "") -> dict[str, str]:
    flat: dict[str, str] = {}
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten(value, path))
        else:
            flat[path] = value
    return flat


EN = _load(TRANSLATIONS / "en.json")
EN_FLAT = _flatten(EN)
LANGUAGE_FILES = sorted(p for p in TRANSLATIONS.glob("*.json") if p.stem != "en")


def _code_sensor_keys() -> set[str]:
    """Alle Übersetzungs-Keys, die der Code für Sensoren erzeugt."""
    keys = {translation_key_for(d.key) for d in ENTITY_DESCRIPTIONS}
    keys |= {translation_key_for(d.key) for d in ENERGY_ENTITY_DESCRIPTIONS}
    keys |= {translation_key_for(f"meter_30_{t['key_suffix']}") for t in METER_ENERGY_TEMPLATES}
    for prefix, templates in (
        ("meter_30_", METER_SENSOR_TEMPLATES),
        ("wb_1_", WALLBOX_SENSOR_TEMPLATES),
        ("sg_50_", SG_READY_SENSOR_TEMPLATES),
    ):
        keys |= {translation_key_for(f"{prefix}{t['key_suffix']}") for t in templates}
    return keys


def test_strings_json_is_the_english_source() -> None:
    """strings.json und translations/en.json sind identisch."""
    assert _load(COMPONENT / "strings.json") == EN


def test_there_are_translations_besides_english() -> None:
    """Mindestens Deutsch muss vorhanden sein."""
    assert LANGUAGE_FILES


@pytest.mark.parametrize("path", LANGUAGE_FILES, ids=lambda p: p.stem)
def test_language_has_exactly_the_english_keys(path: Path) -> None:
    """Keine fehlenden und keine überzähligen Schlüssel gegenüber Englisch."""
    flat = _flatten(_load(path))

    assert not set(EN_FLAT) - set(flat), f"fehlt in {path.name}: {sorted(set(EN_FLAT) - set(flat))}"
    assert not set(flat) - set(EN_FLAT), f"überzählig in {path.name}: {sorted(set(flat) - set(EN_FLAT))}"


@pytest.mark.parametrize("path", LANGUAGE_FILES, ids=lambda p: p.stem)
def test_placeholders_match_english(path: Path) -> None:
    """{seconds} & Co. müssen in jeder Sprache identisch vorkommen."""
    for key, text in _flatten(_load(path)).items():
        assert sorted(PLACEHOLDER_RE.findall(text)) == sorted(PLACEHOLDER_RE.findall(EN_FLAT[key])), key


@pytest.mark.parametrize("path", [TRANSLATIONS / "en.json", *LANGUAGE_FILES], ids=lambda p: p.stem)
def test_no_empty_texts(path: Path) -> None:
    """Leere Texte würden in Home Assistant nur den Gerätenamen anzeigen."""
    for key, text in _flatten(_load(path)).items():
        assert text.strip(), f"{path.name}: {key} ist leer"


def test_every_sensor_in_code_has_a_name() -> None:
    """Jeder Sensor-Key aus dem Code hat einen Namen in den Übersetzungen."""
    sensors = EN["entity"]["sensor"]
    for key in _code_sensor_keys():
        assert KEY_RE.match(key), f"ungültiger translation_key: {key}"
        assert sensors.get(key, {}).get("name"), f"Name fehlt für Sensor '{key}'"


def test_no_orphan_sensor_translations() -> None:
    """Übersetzungen ohne Sensor im Code sind Altlasten."""
    assert not set(EN["entity"]["sensor"]) - _code_sensor_keys()


def test_every_enum_state_has_a_text() -> None:
    """Jeder ENUM-Zustand im Code hat einen Text – und umgekehrt."""
    sensors = EN["entity"]["sensor"]
    for key, states in STATE_MAPS.items():
        assert set(sensors[key]["state"]) == set(states.values()), key
        assert all(KEY_RE.match(state) for state in states.values()), key
    assert set(BIT_OF_STATE_SENSOR) <= set(STATE_MAPS)


def test_switch_and_exception_translations_exist() -> None:
    """Boost-Schalter und Cooldown-Fehlermeldung sind übersetzt."""
    assert EN["entity"]["switch"]["boostmodus"]["name"]
    assert "{seconds}" in EN["exceptions"]["boost_cooldown"]["message"]
