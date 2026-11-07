"""Tests für die Payload-Logik des Cloud-Zugangs.

Die erwarteten Werte stammen aus einem Mitschnitt des flow-Webportals (docs/cloud-api.md).
"""

from __future__ import annotations

import copy

import pytest

from custom_components.hager_flow.cloud.api import (
    build_evse_payload,
    normalize_record_table,
    strategy_from_parameters,
)
from custom_components.hager_flow.cloud.const import (
    CHARGING_STRATEGIES,
    STRATEGY_IMMEDIATE,
    STRATEGY_SOLAR_DELAYED,
    STRATEGY_SOLAR_MINIMUM,
    STRATEGY_SOLAR_ONLY,
)

# Wallbox wie sie GET .../device-links/{emc}/sub unter "controlled" liefert (gekürzt)
EVSE = {
    "id": 1000184646,
    "deviceLinkId": 201708,
    "media": "ModbusTCP",
    "deviceName": "MG-Scheune",
    "pairingState": "paired",
    "type": "Evse",
    "parameters": {
        "protection": 25,
        "minCurrent": 8,
        "phasesManagement": "3PhBlocked",
        "phaseMapping": "312",
        "ledIntensity": 30,
        "activated": False,
        "authenticationMode": "freeAccess",
        "fallbackMaxCurrent": 16,
        "minCurrentSunMode": 80,
        "priority": 100,
        "chargeInFallbackModeAllowed": True,
        "lockCable": False,
        "useMidMeter": True,
        "pulseWeight": 5,
        "sunMode": {"holdingTimeInMin": 3, "activated": True, "chargingStrategy": "Disabled", "parameterList": []},
        "someReadOnlyField": "nicht mitschicken",
    },
    "evseSubTypeParameters": {
        "ocppActivation": False,
        "ocppServerAddress": "wss://",
        "ocppId": "abc",
        "ocppAuthType": "No",
        "deviceReference": "",
        "wbType": "6",
        "extra": "nicht mitschicken",
    },
}


def _with_sun_mode(**sun_mode) -> dict:
    evse = copy.deepcopy(EVSE)
    evse["parameters"]["sunMode"].update(sun_mode)
    return evse


def test_record_table_columns_to_rows() -> None:
    payload = {"id": [201708, 201709], "deviceType": ["emc", "storage"], "deviceId": ["322337012186", "x"]}
    assert normalize_record_table(payload) == [
        {"id": 201708, "deviceType": "emc", "deviceId": "322337012186"},
        {"id": 201709, "deviceType": "storage", "deviceId": "x"},
    ]


def test_record_table_passes_lists_through() -> None:
    assert normalize_record_table([{"id": 1}, "x"]) == [{"id": 1}]
    assert normalize_record_table(None) == []


@pytest.mark.parametrize(
    ("sun_mode", "expected"),
    [
        ({"activated": True, "chargingStrategy": "Disabled"}, STRATEGY_SOLAR_ONLY),
        ({"activated": True, "chargingStrategy": "Immediate"}, STRATEGY_SOLAR_MINIMUM),
        ({"activated": True, "chargingStrategy": "Delayed"}, STRATEGY_SOLAR_DELAYED),
        ({"activated": False, "chargingStrategy": "Disabled"}, STRATEGY_IMMEDIATE),
    ],
)
def test_strategy_from_parameters(sun_mode: dict, expected: str) -> None:
    assert strategy_from_parameters(_with_sun_mode(**sun_mode)["parameters"]) == expected


def test_strategy_unknown() -> None:
    assert strategy_from_parameters({}) is None


@pytest.mark.parametrize("strategy", CHARGING_STRATEGIES)
def test_payload_roundtrip(strategy: str) -> None:
    """Was wir schreiben, lesen wir als dieselbe Strategie zurück."""
    payload = build_evse_payload(EVSE, strategy)
    assert strategy_from_parameters(payload["parameters"]) == strategy


def test_payload_matches_portal_solar_minimum() -> None:
    payload = build_evse_payload(EVSE, STRATEGY_SOLAR_MINIMUM)
    assert payload["deviceName"] == "MG-Scheune"
    assert payload["parameters"]["sunMode"] == {
        "holdingTimeInMin": 3,
        "activated": True,
        "chargingStrategy": "Immediate",
        "parameterList": [{"minEnergy": "7"}] * 7,
    }
    assert "someReadOnlyField" not in payload["parameters"]
    assert payload["evseSubTypeParameters"] == {
        "ocppActivation": False,
        "ocppServerAddress": "wss://",
        "ocppId": "abc",
        "ocppAuthType": "No",
        "deviceReference": "",
        "wbType": "6",
    }


def test_payload_matches_portal_delayed_and_keeps_profile() -> None:
    evse = _with_sun_mode(parameterList=[{"minEnergy": "12"}] * 7)
    sun_mode = build_evse_payload(evse, STRATEGY_SOLAR_DELAYED)["parameters"]["sunMode"]
    assert sun_mode["chargingStrategy"] == "Delayed"
    assert sun_mode["parameterList"] == [{"daytime": "21600", "minEnergy": "12"}] * 7


@pytest.mark.parametrize(
    ("strategy", "activated"), [(STRATEGY_SOLAR_ONLY, True), (STRATEGY_IMMEDIATE, False)]
)
def test_payload_disabled_strategies_send_empty_list(strategy: str, activated: bool) -> None:
    evse = _with_sun_mode(chargingStrategy="Immediate", parameterList=[{"minEnergy": "7"}] * 7)
    sun_mode = build_evse_payload(evse, strategy)["parameters"]["sunMode"]
    assert sun_mode["activated"] is activated
    assert sun_mode["chargingStrategy"] == "Disabled"
    assert sun_mode["parameterList"] == []


def test_payload_does_not_mutate_input() -> None:
    before = copy.deepcopy(EVSE)
    build_evse_payload(EVSE, STRATEGY_SOLAR_DELAYED)
    assert EVSE == before


def test_payload_rejects_unknown_strategy() -> None:
    with pytest.raises(ValueError):
        build_evse_payload(EVSE, "turbo")
