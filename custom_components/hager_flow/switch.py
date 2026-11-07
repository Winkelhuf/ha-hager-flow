"""Schalter-Plattform für die Hager flow Integration."""
from __future__ import annotations

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.exceptions import ServiceValidationError

from .cloud.const import CFG_BATTERY_BEFORE_CAR, CFG_BATTERY_TO_CAR_BOOST, CFG_BATTERY_TO_CAR_SOLAR
from .cloud.entity import HagerFlowCloudEntity, emc_device_info
from .const import DOMAIN
from .entity.base import HagerFlowEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richte die Schalter-Plattform dynamisch für alle Wallboxen ein."""
    coordinator = entry.runtime_data.coordinator
    entities = []

    if coordinator.discovered_wallboxes:
        for slave, wb_name in coordinator.discovered_wallboxes.items():
            entities.append(HagerFlowWallboxBoostSwitch(coordinator, slave, wb_name, entry.entry_id))

    # Optionaler Cloud-Zugang: Einstellungen, die per Modbus nicht beschreibbar sind
    cloud = entry.runtime_data.cloud
    if cloud is not None:
        entities.extend(
            HagerFlowCloudConfigSwitch(cloud, entry.entry_id, key, field, icon)
            for key, field, icon in CLOUD_CONFIG_SWITCHES
        )

    async_add_entities(entities)


# (translation_key, Feld in /installations/{id}/config, Icon)
CLOUD_CONFIG_SWITCHES: tuple[tuple[str, str, str], ...] = (
    ("speicher_fuers_auto_solar", CFG_BATTERY_TO_CAR_SOLAR, "mdi:home-battery"),
    ("speicher_fuers_auto_boost", CFG_BATTERY_TO_CAR_BOOST, "mdi:battery-arrow-up"),
)


class HagerFlowCloudConfigSwitch(HagerFlowCloudEntity, SwitchEntity):
    """Ein Ja/Nein-Feld der Anlagen-Konfiguration in der Cloud (Speichermanagement).

    Speicher fürs Auto ist nur bei Ladepriorität "Ladestation zuerst" zulässig –
    bei "Batterie zuerst" lehnt das System die Änderung ab. Dann ist der Schalter
    nicht verfügbar (ausgegraut).
    """

    def __init__(self, coordinator, entry_id: str, key: str, field: str, icon: str) -> None:
        super().__init__(coordinator, entry_id, key, emc_device_info(entry_id))
        self._field = field
        self._attr_icon = icon

    @property
    def _config(self) -> dict[str, Any]:
        return self.coordinator.data.config if self.coordinator.data else {}

    @property
    def _battery_first(self) -> bool:
        return bool(self._config.get(CFG_BATTERY_BEFORE_CAR, False))

    @property
    def available(self) -> bool:
        return super().available and bool(self._config) and not self._battery_first

    @property
    def is_on(self) -> bool | None:
        value = self._config.get(self._field)
        return self._value(None if value is None else bool(value))

    async def _async_set(self, value: bool) -> None:
        if self._battery_first:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="cloud_needs_car_first")
        config = self._config
        await self._async_write(
            lambda: self.coordinator.api.async_set_config(config, {self._field: value}), value
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set(False)

class HagerFlowWallboxBoostSwitch(HagerFlowEntity, SwitchEntity):
    """Schalter zur Steuerung des Boostmodus einer Witty Wallbox mit Benutzer-Feedback."""

    def __init__(self, coordinator, slave_id: int, wb_name: str, entry_id: str) -> None:
        """Initialisiere den Schalter."""
        from homeassistant.helpers.entity import EntityDescription
        
        self.slave_id = slave_id
        self.wb_name = wb_name
        self._key = f"wb_{slave_id}_boostmodus"
        
        # Interner Speicher für den Trägheitsschutz
        self._optimistic_state: bool | None = None
        self._cooldown_until: datetime | None = None
        
        desc = EntityDescription(
            key=self._key,
            icon="mdi:rocket-launch",
        )
        super().__init__(coordinator, desc, entry_id)
        
        self._attr_device_info = DeviceInfo(
            identifiers={("hager_flow", f"hager_flow_wb_{slave_id}_{entry_id}")},
            name=wb_name,
            manufacturer="Hager",
            model="Witty Wallbox",
        )

    @property
    def is_on(self) -> bool | None:
        """Gibt den Zustand zurück – nutzt bei Cloud-Trägheit den gemerkten Klick-Zustand."""
        if self._cooldown_until and datetime.now() < self._cooldown_until:
            if self._optimistic_state is not None:
                return self._optimistic_state

        # Nach Ablauf des Cooldowns gelten wieder die echten Modbus-Registerdaten
        raw_value = self.coordinator.data.get(self._key)
        if raw_value is None:
            return False
        return int(raw_value) == 1

    def _raise_if_cooling_down(self) -> None:
        """Wirft die übersetzte Fehlermeldung (exceptions.boost_cooldown), solange der Cooldown läuft."""
        if self._cooldown_until and datetime.now() < self._cooldown_until:
            restzeit = int((self._cooldown_until - datetime.now()).total_seconds())
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="boost_cooldown",
                translation_placeholders={"seconds": str(restzeit)},
            )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Schalte den Boostmodus ein (zeigt Fehlermeldung, wenn gesperrt)."""
        self._raise_if_cooling_down()

        self._optimistic_state = True
        self._cooldown_until = datetime.now() + timedelta(seconds=30)
        self.async_write_ha_state()
        await self._write_boost_state(1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Schalte den Boostmodus aus (zeigt Fehlermeldung, wenn gesperrt)."""
        self._raise_if_cooling_down()

        self._optimistic_state = False
        self._cooldown_until = datetime.now() + timedelta(seconds=30)
        self.async_write_ha_state()
        await self._write_boost_state(0)

    async def _write_boost_state(self, state_value: int) -> None:
        """Sendet den Schreibbefehl an die Wallbox."""
        coordinator = self.coordinator
        slave = self.slave_id
        
        def write_logic():
            _LOGGER.info("Sende Boostmodus-Befehl an Wallbox (Slave %s, Register 4631): %s", slave, state_value)
            result = coordinator.client.write_register(4631, state_value, device_id=slave)
            if result is None or result.isError():
                raise Exception(f"Schreibbefehl von Wallbox (Slave {slave}) verweigert")
                
        try:
            await coordinator.hass.async_add_executor_job(write_logic)
            await asyncio.sleep(2)
            await coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Fehler beim Schalten des Boostmodus: %s", err)
            self._cooldown_until = None
            await coordinator.async_request_refresh()