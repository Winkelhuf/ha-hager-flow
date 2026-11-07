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


# --------------------------------------------------------------------------- #
# Login-Hilfen
# --------------------------------------------------------------------------- #
from custom_components.hager_flow.cloud.auth import (  # noqa: E402
    _auto_post_form,
    _html_redirect,
    describe_page,
)


def test_html_redirect_location_replace() -> None:
    body = '<script>window.location.replace("https://e3dc.e3dc.com/x?token=a&amp;reAuthToken=b")</script>'
    assert _html_redirect(body) == "https://e3dc.e3dc.com/x?token=a&reAuthToken=b"


def test_html_redirect_location_href() -> None:
    assert _html_redirect("<script>location.href = '/next'</script>") == "/next"


def test_saml_form_without_method_is_posted() -> None:
    body = '<form action="https://e3dc.e3dc.com/acs"><input type="hidden" name="SAMLResponse" value="abc"></form>'
    assert _auto_post_form(body) == ("https://e3dc.e3dc.com/acs", {"SAMLResponse": "abc"})


def test_describe_page_hides_query_and_secrets() -> None:
    secret = "eyJ" + "a" * 60
    body = (
        "<html><head><title>Fehler</title><script>var t='x';</script></head><body>"
        f"<p>Cookie nicht gefunden {secret}</p>"
        '<form method="post" action="/realms/customer/login-actions/x?session_code=SECRET">'
        '<input name="username"></form>'
        f'<a href="https://flow.hager.com/cb?token={secret}">weiter</a></body></html>'
    )
    text = describe_page("https://auth.hagerenergy.com/realms/customer/broker/after-post-broker-login?code=SECRET", body)
    assert "Fehler" in text and "Cookie nicht gefunden" in text
    assert "POST auth.hagerenergy.com/realms/customer/login-actions/x" in text
    assert "flow.hager.com/cb" in text and "username" in text
    assert "SECRET" not in text and secret not in text


from custom_components.hager_flow.cloud.auth import _saml_post_from_script  # noqa: E402
import base64 as _b64  # noqa: E402

_XML = '<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" ID="x"><ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#"/></samlp:Response>'


def test_saml_from_kc_context_json() -> None:
    """Keycloak-Theme mit kcContext-JSON (XML als JSON-String, Produktiv- und Lab-URL)."""
    xml_json = _XML.replace("<", "\\u003c").replace('"', '\\"')
    body = (
        "<html><body><div id=root></div><script>window.kcContext = {"
        '"pageId":"saml-post-form.ftl",'
        '"clients":["https://e3dc.labprod1be.lab.e3dc.com/auth-saml/service-providers/hager/assert"],'
        '"samlPost":{"url":"https://e3dc.e3dc.com/auth-saml/service-providers/hager/assert",'
        f'"SAMLResponse":"{xml_json}","relayState":"rs-1"}}'
        "};</script><script src=/x.js></script></body></html>"
    )
    url, fields = _saml_post_from_script(body)
    assert url == "https://e3dc.e3dc.com/auth-saml/service-providers/hager/assert"
    assert _b64.b64decode(fields["SAMLResponse"]).decode() == _XML
    assert fields["RelayState"] == "rs-1"


def test_saml_from_js_base64_single_quotes_prefers_prod_host() -> None:
    encoded = _b64.b64encode(_XML.encode()).decode()
    body = (
        "<script>var data = { SAMLResponse: '" + encoded + "' };"
        "var a='https://e3dc.labprod1be.lab.e3dc.com/auth-saml/service-providers/hager/assert';"
        "var b='https://e3dc.e3dc.com/auth-saml/service-providers/hager/assert';</script>"
    )
    url, fields = _saml_post_from_script(body)
    assert url == "https://e3dc.e3dc.com/auth-saml/service-providers/hager/assert"
    assert fields == {"SAMLResponse": encoded}


def test_saml_absent() -> None:
    assert _saml_post_from_script("<script>var x = 1;</script>") is None


# --------------------------------------------------------------------------- #
# Wallbox-Entladegrenze "Bis Ladezustand" (soc)
# --------------------------------------------------------------------------- #
from custom_components.hager_flow.cloud.api import (  # noqa: E402
    CloudWallbox,
    wallbox_config_path,
    wallbox_index,
)
from custom_components.hager_flow.cloud.const import AUTH_BASE_URL  # noqa: E402


def test_wallbox_index_from_evse() -> None:
    assert wallbox_index({"index": 0}) == 0
    assert wallbox_index({"index": "2"}) == 2
    assert wallbox_index({}) == 0
    assert wallbox_index({"index": None}) == 0


def test_wallbox_config_path() -> None:
    assert (
        wallbox_config_path("322337012186", 0)
        == f"{AUTH_BASE_URL}/wallboxes/322337012186/0/configuration"
    )


def test_cloud_wallbox_index_property() -> None:
    wb = CloudWallbox(1000184646, "MG-Scheune", {"index": 1}, discharge_soc=60)
    assert wb.index == 1
    assert wb.discharge_soc == 60
