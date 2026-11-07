"""Konstanten für den optionalen Cloud-Zugang (inoffizielle API des flow-Webportals)."""
from __future__ import annotations

from datetime import timedelta

FLOW_LOGIN_URL = "https://e3dc.e3dc.com/auth-saml/service-providers/hager/login?app=hager"
AUTH_BASE_URL = "https://e3dc.e3dc.com"
INSTALLATIONS_BASE_URL = "https://installations.e3dc.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
)

TOKEN_REFRESH_MARGIN = timedelta(minutes=2)
CLOUD_SCAN_INTERVAL = timedelta(seconds=60)
# So lange braucht eine Änderung über die Cloud bis zum Gerät und zurück
CLOUD_COOLDOWN = timedelta(seconds=30)

# Felder der Anlagen-Konfiguration (PUT /installations/{id}/config)
CFG_BATTERY_BEFORE_CAR = "emsBatteryBeforeCarMode"
CFG_BATTERY_TO_CAR_SOLAR = "emsBatteryToCarMode"
CFG_BATTERY_TO_CAR_BOOST = "emsWallboxEnforcePowerAssignment"

# Notstromreserve: Feld in der Speicher-Konfiguration
# (PUT /installations/{id}/device-links/{storageLinkId}/config/storage), in Wh
CFG_EMERGENCY_RESERVE = "emergencyPowerCapacityReserve"
# Kapazität je Batteriemodul (batDcbCount × 3000 Wh)
BATTERY_MODULE_WH = 3000
# Das Entladelimit (Bis Ladezustand) muss immer mindestens so viel Prozent
# ÜBER der Notstromreserve liegen (und darf nie darunter)
DISCHARGE_RESERVE_MARGIN_PCT = 10

# Ladestrategien der Wallbox (sprachfreie Schlüssel -> Übersetzung in translations/*.json)
STRATEGY_SOLAR_ONLY = "solar_only"
STRATEGY_SOLAR_MINIMUM = "solar_minimum"
STRATEGY_SOLAR_DELAYED = "solar_delayed"
STRATEGY_IMMEDIATE = "immediate"
CHARGING_STRATEGIES = [
    STRATEGY_SOLAR_ONLY,
    STRATEGY_SOLAR_MINIMUM,
    STRATEGY_SOLAR_DELAYED,
    STRATEGY_IMMEDIATE,
]

# Standardwerte, die das Portal setzt, wenn noch kein Wochenprofil existiert
DEFAULT_MIN_ENERGY_KWH = "7"
DEFAULT_DELAYED_DAYTIME_S = "21600"  # 06:00 Uhr

# Diese Parameter schickt das Portal beim Speichern einer Wallbox mit
EVSE_PARAMETER_KEYS = (
    "protection",
    "minCurrent",
    "phasesManagement",
    "phaseMapping",
    "ledIntensity",
    "activated",
    "authenticationMode",
    "fallbackMaxCurrent",
    "minCurrentSunMode",
    "priority",
    "chargeInFallbackModeAllowed",
    "lockCable",
    "useMidMeter",
    "pulseWeight",
    "sunMode",
)
EVSE_SUBTYPE_KEYS = (
    "ocppActivation",
    "ocppServerAddress",
    "ocppId",
    "ocppAuthType",
    "deviceReference",
    "wbType",
)
