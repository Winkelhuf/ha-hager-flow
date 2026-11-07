"""Client für die inoffizielle Cloud-API des Hager flow Webportals.

Endpunkte und Payloads sind in docs/cloud-api.md dokumentiert.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable
import copy
from dataclasses import dataclass, field
import json
import logging
import time
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .auth import CloudTokens, async_login, token_expiry
from .const import (
    AUTH_BASE_URL,
    CFG_BATTERY_BEFORE_CAR,
    DEFAULT_DELAYED_DAYTIME_S,
    DEFAULT_MIN_ENERGY_KWH,
    EVSE_PARAMETER_KEYS,
    EVSE_SUBTYPE_KEYS,
    INSTALLATIONS_BASE_URL,
    STRATEGY_IMMEDIATE,
    STRATEGY_SOLAR_DELAYED,
    STRATEGY_SOLAR_MINIMUM,
    STRATEGY_SOLAR_ONLY,
    TOKEN_REFRESH_MARGIN,
    USER_AGENT,
)
from .errors import HagerCloudAuthError, HagerCloudConnectionError, HagerCloudError

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = ClientTimeout(total=30)


# --------------------------------------------------------------------------- #
# Reine Hilfsfunktionen (ohne Netzwerk, testbar)
# --------------------------------------------------------------------------- #
def normalize_record_table(payload: Any) -> list[dict[str, Any]]:
    """Die API liefert Listen spaltenweise ({"id": [1, 2], "name": [..]}) – in Zeilen umwandeln."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    lengths = [len(v) for v in payload.values() if isinstance(v, list)]
    if not lengths:
        return [payload]
    return [
        {k: (v[i] if i < len(v) else None) if isinstance(v, list) else v for k, v in payload.items()}
        for i in range(max(lengths))
    ]


def strategy_from_parameters(parameters: dict[str, Any]) -> str | None:
    """Ladestrategie aus den EVSE-Parametern ableiten (siehe docs/cloud-api.md)."""
    sun_mode = parameters.get("sunMode")
    if not isinstance(sun_mode, dict):
        return None
    if not sun_mode.get("activated"):
        return STRATEGY_IMMEDIATE
    strategy = str(sun_mode.get("chargingStrategy") or "").casefold()
    if strategy == "immediate":
        return STRATEGY_SOLAR_MINIMUM
    if strategy == "delayed":
        return STRATEGY_SOLAR_DELAYED
    if strategy == "disabled":
        return STRATEGY_SOLAR_ONLY
    return None


def _week_profile(current: Any, with_daytime: bool) -> list[dict[str, str]]:
    """Wochenprofil (7 Einträge) – vorhandene Werte übernehmen, sonst Portal-Standard."""
    rows = current if isinstance(current, list) else []
    profile = []
    for day in range(7):
        row = rows[day] if day < len(rows) and isinstance(rows[day], dict) else {}
        entry = {"minEnergy": str(row.get("minEnergy") or DEFAULT_MIN_ENERGY_KWH)}
        if with_daytime:
            entry = {"daytime": str(row.get("daytime") or DEFAULT_DELAYED_DAYTIME_S), **entry}
        profile.append(entry)
    return profile


def build_evse_payload(evse: dict[str, Any], strategy: str) -> dict[str, Any]:
    """PUT-Body für eine Wallbox mit neuer Ladestrategie – wie ihn das Portal schickt."""
    params = evse.get("parameters") or {}
    payload_params = {k: copy.deepcopy(params[k]) for k in EVSE_PARAMETER_KEYS if k in params}
    sun_mode = dict(payload_params.get("sunMode") or {})

    if strategy == STRATEGY_IMMEDIATE:
        sun_mode.update(activated=False, chargingStrategy="Disabled", parameterList=[])
    elif strategy == STRATEGY_SOLAR_ONLY:
        sun_mode.update(activated=True, chargingStrategy="Disabled", parameterList=[])
    elif strategy == STRATEGY_SOLAR_MINIMUM:
        sun_mode.update(
            activated=True,
            chargingStrategy="Immediate",
            parameterList=_week_profile(sun_mode.get("parameterList"), with_daytime=False),
        )
    elif strategy == STRATEGY_SOLAR_DELAYED:
        sun_mode.update(
            activated=True,
            chargingStrategy="Delayed",
            parameterList=_week_profile(sun_mode.get("parameterList"), with_daytime=True),
        )
    else:
        raise ValueError(f"Unbekannte Ladestrategie: {strategy}")
    payload_params["sunMode"] = sun_mode

    payload: dict[str, Any] = {"deviceName": evse.get("deviceName") or "", "parameters": payload_params}
    subtype = evse.get("evseSubTypeParameters")
    if isinstance(subtype, dict):
        payload["evseSubTypeParameters"] = {k: subtype[k] for k in EVSE_SUBTYPE_KEYS if k in subtype}
    return payload


# --------------------------------------------------------------------------- #
# Datenmodell
# --------------------------------------------------------------------------- #
def wallbox_index(evse: dict[str, Any]) -> int:
    """Wallbox-Index für den E3/DC-Endpunkt (/wallboxes/{sn}/{index}/configuration)."""
    value = evse.get("index")
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def wallbox_config_path(emc_serial: str, index: int) -> str:
    """Pfad der Wallbox-Konfiguration auf e3dc.e3dc.com (hält u. a. das Feld ``soc``)."""
    return f"{AUTH_BASE_URL}/wallboxes/{emc_serial}/{index}/configuration"


@dataclass(slots=True)
class CloudWallbox:
    """Eine Wallbox (EVSE) aus der Cloud."""

    evse_id: int
    name: str
    raw: dict[str, Any]
    # Entladegrenze "Bis Ladezustand" (%) aus der E3/DC-Wallbox-Konfiguration; None = nicht gelesen
    discharge_soc: int | None = None

    @property
    def strategy(self) -> str | None:
        return strategy_from_parameters(self.raw.get("parameters") or {})

    @property
    def index(self) -> int:
        return wallbox_index(self.raw)


@dataclass(slots=True)
class CloudSnapshot:
    """Stand der Cloud-Daten bei einem Abruf."""

    config: dict[str, Any]
    emc_link_id: int | None
    emc_serial: str | None
    wallboxes: dict[int, CloudWallbox] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #
class HagerFlowCloudApi:
    """Hält die Tokens frisch und kapselt alle Cloud-Aufrufe."""

    def __init__(
        self,
        session: ClientSession,
        email: str,
        password: str,
        installation_id: int | None = None,
        tokens: CloudTokens | None = None,
        on_tokens: Callable[[CloudTokens], None] | None = None,
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self.installation_id = installation_id
        self._tokens = tokens
        self._on_tokens = on_tokens
        self._lock = asyncio.Lock()

    # ---- Tokens -------------------------------------------------------------
    def _set_tokens(self, tokens: CloudTokens) -> None:
        self._tokens = tokens
        if self._on_tokens:
            self._on_tokens(tokens)

    def _token_valid(self) -> bool:
        exp = token_expiry(self._tokens.access_token if self._tokens else None)
        return exp is not None and exp - TOKEN_REFRESH_MARGIN.total_seconds() > time.time()

    async def _access_token(self, force: bool = False) -> str:
        async with self._lock:
            if not force and self._token_valid():
                return self._tokens.access_token
            if self._tokens and self._tokens.reauth_token:
                try:
                    async with self._session.post(
                        f"{AUTH_BASE_URL}/auth-saml/re-auth",
                        json={"reAuthToken": self._tokens.reauth_token},
                        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
                        timeout=_TIMEOUT,
                    ) as resp:
                        data = await resp.json(content_type=None) if resp.status == 200 else None
                except (ClientError, asyncio.TimeoutError, ValueError):
                    data = None
                if isinstance(data, dict) and data.get("token"):
                    self._set_tokens(
                        CloudTokens(str(data["token"]), str(data.get("reAuthToken") or self._tokens.reauth_token))
                    )
                    return self._tokens.access_token
            _LOGGER.debug("Re-Auth nicht möglich – neue Anmeldung mit E-Mail/Passwort")
            self._set_tokens(await async_login(self._email, self._password))
            return self._tokens.access_token

    async def _request(self, method: str, url: str, payload: dict[str, Any] | None = None, _retry: bool = True) -> Any:
        token = await self._access_token()
        headers = {"Accept": "application/json", "Authorization": f"Bearer {token}", "User-Agent": USER_AGENT}
        try:
            async with self._session.request(method, url, json=payload, headers=headers, timeout=_TIMEOUT) as resp:
                if resp.status == 401 and _retry:
                    await self._access_token(force=True)
                    return await self._request(method, url, payload, _retry=False)
                if resp.status in (401, 403):
                    raise HagerCloudAuthError(f"Zugriff verweigert ({resp.status}) auf {url}")
                text = await resp.text()
                if resp.status >= 400:
                    raise HagerCloudError(f"HTTP {resp.status} von {url}: {text[:200]}")
                return json.loads(text) if text else None
        except (ClientError, asyncio.TimeoutError) as err:
            raise HagerCloudConnectionError(f"Cloud nicht erreichbar: {url}") from err
        except ValueError as err:
            raise HagerCloudError(f"Unerwartete Antwort von {url}") from err

    def _inst_url(self, suffix: str = "") -> str:
        if self.installation_id is None:
            raise HagerCloudError("Keine Anlage ausgewählt")
        return f"{INSTALLATIONS_BASE_URL}/installations/{self.installation_id}{suffix}"

    # ---- Lesen --------------------------------------------------------------
    async def async_login(self) -> None:
        """Erzwingt eine frische Anmeldung (Prüfung der Zugangsdaten)."""
        self._set_tokens(await async_login(self._email, self._password))

    async def async_get_installations(self) -> list[dict[str, Any]]:
        """Anlagen des Kontos. Installateur-Konten bekommen ohne Parameter teils 400/403 –
        dann dieselbe Abfrage wie das Portal verwenden."""
        base = f"{INSTALLATIONS_BASE_URL}/installations"
        try:
            rows = normalize_record_table(await self._request("GET", base))
            if rows:
                return rows
        except HagerCloudError as err:
            if isinstance(err, HagerCloudConnectionError):
                raise
            _LOGGER.debug("Anlagenliste ohne Parameter abgelehnt (%s) – Portal-Variante", err)
        return normalize_record_table(
            await self._request("GET", f"{base}?connect=installationHistory&limit=50&offset=0&sort=-createdAt")
        )

    async def async_get_emc_link(self, installation_id: int | None = None) -> dict[str, Any] | None:
        """Device-Link des EMC (enthält die Seriennummer als deviceId)."""
        inst = installation_id if installation_id is not None else self.installation_id
        links = normalize_record_table(
            await self._request("GET", f"{INSTALLATIONS_BASE_URL}/installations/{inst}/device-links")
        )
        active = [l for l in links if str(l.get("deviceType")).casefold() == "emc" and not l.get("stopAt")]
        return active[0] if active else None

    async def async_get_snapshot(self) -> CloudSnapshot:
        config = await self._request("GET", self._inst_url("/config")) or {}
        emc = await self.async_get_emc_link()
        wallboxes: dict[int, CloudWallbox] = {}
        serial = str(emc.get("deviceId")) if emc else None
        if emc:
            sub = await self._request("GET", self._inst_url(f"/device-links/{emc['id']}/sub")) or {}
            for evse in sub.get("controlled") or []:
                if isinstance(evse, dict) and str(evse.get("type")).casefold() == "evse":
                    wb = CloudWallbox(int(evse["id"]), str(evse.get("deviceName") or ""), evse)
                    wb.discharge_soc = await self._async_read_discharge_soc(serial, wb.index)
                    wallboxes[int(evse["id"])] = wb
        return CloudSnapshot(
            config=config,
            emc_link_id=int(emc["id"]) if emc else None,
            emc_serial=str(emc.get("deviceId")) if emc else None,
            wallboxes=wallboxes,
        )

    async def _async_read_discharge_soc(self, emc_serial: str | None, index: int) -> int | None:
        """Entladegrenze ``soc`` aus der Wallbox-Konfiguration lesen.

        Dieser Endpunkt liegt auf e3dc.e3dc.com und ist nicht bei jeder Anlage
        verfügbar – schlägt er fehl, bleibt die Entität nur unavailable.
        """
        if not emc_serial:
            return None
        try:
            config = await self._request("GET", wallbox_config_path(emc_serial, index))
        except HagerCloudError as err:
            _LOGGER.debug("Wallbox-Konfiguration (soc) nicht lesbar: %s", err)
            return None
        if isinstance(config, dict) and isinstance(config.get("soc"), (int, float)):
            return int(config["soc"])
        return None

    async def async_get_wallbox_configuration(self, emc_serial: str, index: int) -> dict[str, Any]:
        return await self._request("GET", wallbox_config_path(emc_serial, index)) or {}

    # ---- Schreiben ----------------------------------------------------------
    async def async_sync(self) -> None:
        """Überträgt die geänderte Konfiguration an das Gerät (wie das Portal nach jedem Speichern)."""
        await self._request("POST", self._inst_url("/config/sync"))

    async def async_set_config(self, current: dict[str, Any], changes: dict[str, Any]) -> None:
        """Ändert Felder der Anlagen-Konfiguration; emsBatteryBeforeCarMode schickt das Portal immer mit."""
        body = {CFG_BATTERY_BEFORE_CAR: bool(current.get(CFG_BATTERY_BEFORE_CAR, False)), **changes}
        await self._request("PUT", self._inst_url("/config"), body)
        await self.async_sync()

    async def async_set_charging_strategy(self, emc_link_id: int, wallbox: CloudWallbox, strategy: str) -> None:
        await self._request(
            "PUT",
            self._inst_url(f"/device-links/{emc_link_id}/sub/controlled/{wallbox.evse_id}"),
            build_evse_payload(wallbox.raw, strategy),
        )
        await self.async_sync()

    async def async_set_discharge_soc(self, emc_serial: str, wallbox: CloudWallbox, soc: int) -> None:
        """Entladegrenze "Bis Ladezustand" (%) setzen – Teil-PUT wie beim Boost (chargeFull)."""
        await self._request(
            "PUT", wallbox_config_path(emc_serial, wallbox.index), {"soc": max(0, min(100, int(soc)))}
        )
