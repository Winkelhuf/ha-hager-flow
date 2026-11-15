"""Auswahl-Entitäten (nur mit aktiviertem Cloud-Zugang)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .cloud.const import CFG_BATTERY_BEFORE_CAR, CHARGING_STRATEGIES
from .cloud.coordinator import HagerFlowCloudCoordinator
from .cloud.entity import HagerFlowCloudEntity, emc_device_info, modbus_wallbox_device_info
from .data import HagerFlowConfigEntry

# Ladepriorität: sprachfreie Schlüssel wie beim Modbus-Sensor power_prioritaet_ziel
PRIORITY_CAR_FIRST = "car_first"
PRIORITY_BATTERY_FIRST = "battery_first"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HagerFlowConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richtet die Cloud-Auswahlfelder ein, falls der Cloud-Zugang aktiv ist."""
    cloud = entry.runtime_data.cloud
    if cloud is None:
        return

    entities: list[SelectEntity] = [HagerFlowChargingPrioritySelect(cloud, entry.entry_id)]
    # Ladestrategie je Modbus-erkannter Wallbox fest anlegen – immer sichtbar und
    # robust gegen Cloud-Ausfälle; wird aktiv, sobald die passende Cloud-Wallbox (per
    # Name) vorliegt.
    for slave, wb_name in entry.runtime_data.coordinator.discovered_wallboxes.items():
        entities.append(HagerFlowChargingStrategySelect(cloud, entry.entry_id, slave, wb_name))
    async_add_entities(entities)


class HagerFlowChargingPrioritySelect(HagerFlowCloudEntity, SelectEntity):
    """Solar-Priorität: Auto oder Batterie zuerst (emsBatteryBeforeCarMode)."""

    _attr_options = [PRIORITY_CAR_FIRST, PRIORITY_BATTERY_FIRST]
    _attr_icon = "mdi:swap-vertical-bold"

    def __init__(self, coordinator: HagerFlowCloudCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id, "ladeprioritaet", emc_device_info(entry_id))

    @property
    def current_option(self) -> str | None:
        return self._value(self._read_actual())

    def _read_actual(self) -> str | None:
        value = (self.coordinator.data.config if self.coordinator.data else {}).get(CFG_BATTERY_BEFORE_CAR)
        return None if value is None else (PRIORITY_BATTERY_FIRST if value else PRIORITY_CAR_FIRST)

    async def async_select_option(self, option: str) -> None:
        config = self.coordinator.data.config
        await self._async_write(
            lambda: self.coordinator.api.async_set_config(
                config, {CFG_BATTERY_BEFORE_CAR: option == PRIORITY_BATTERY_FIRST}
            ),
            option,
        )


class HagerFlowChargingStrategySelect(HagerFlowCloudEntity, SelectEntity):
    """Ladestrategie einer Wallbox (PV-Überschuss, Mindestladung, Zieltermin, Sofortladen)."""

    _attr_options = CHARGING_STRATEGIES
    _attr_icon = "mdi:ev-station"

    def __init__(self, coordinator: HagerFlowCloudCoordinator, entry_id: str, slave: int, wb_name: str) -> None:
        super().__init__(coordinator, entry_id, "ladestrategie", modbus_wallbox_device_info(entry_id, slave, wb_name))
        self._slave = slave
        self._wb_name = wb_name
        self._attr_unique_id = f"{entry_id}_cloud_ladestrategie_{slave}"

    @property
    def _wallbox(self):
        """Die Cloud-Wallbox zu dieser Modbus-Wallbox (per Namensabgleich)."""
        data = self.coordinator.data
        if not data:
            return None
        wanted = (self._wb_name or "").strip().casefold()
        for wb in data.wallboxes.values():
            if (wb.name or "").strip().casefold() == wanted:
                return wb
        return None

    @property
    def available(self) -> bool:
        return super().available and self._wallbox is not None

    @property
    def current_option(self) -> str | None:
        return self._value(self._wallbox.strategy if self._wallbox else None)

    def _read_actual(self) -> str | None:
        return self._wallbox.strategy if self._wallbox else None

    async def async_select_option(self, option: str) -> None:
        wallbox, link_id = self._wallbox, self.coordinator.data.emc_link_id
        await self._async_write(
            lambda: self.coordinator.api.async_set_charging_strategy(link_id, wallbox, option),
            option,
        )
