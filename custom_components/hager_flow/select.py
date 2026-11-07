"""Auswahl-Entitäten (nur mit aktiviertem Cloud-Zugang)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .cloud.const import CFG_BATTERY_BEFORE_CAR, CHARGING_STRATEGIES
from .cloud.coordinator import HagerFlowCloudCoordinator
from .cloud.entity import HagerFlowCloudEntity, emc_device_info, wallbox_device_info
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

    async_add_entities([HagerFlowChargingPrioritySelect(cloud, entry.entry_id)])

    modbus_wallboxes = entry.runtime_data.coordinator.discovered_wallboxes
    known: set[int] = set()

    @callback
    def _add_new_wallboxes() -> None:
        if not cloud.data:
            return
        new = [wb for evse_id, wb in cloud.data.wallboxes.items() if evse_id not in known]
        if not new:
            return
        known.update(wb.evse_id for wb in new)
        async_add_entities(
            HagerFlowChargingStrategySelect(
                cloud, entry.entry_id, wb.evse_id, wallbox_device_info(entry.entry_id, wb, modbus_wallboxes)
            )
            for wb in new
        )

    _add_new_wallboxes()
    entry.async_on_unload(cloud.async_add_listener(_add_new_wallboxes))


class HagerFlowChargingPrioritySelect(HagerFlowCloudEntity, SelectEntity):
    """Solar-Priorität: Auto oder Batterie zuerst (emsBatteryBeforeCarMode)."""

    _attr_options = [PRIORITY_CAR_FIRST, PRIORITY_BATTERY_FIRST]
    _attr_icon = "mdi:swap-vertical-bold"

    def __init__(self, coordinator: HagerFlowCloudCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id, "ladeprioritaet", emc_device_info(entry_id))

    @property
    def current_option(self) -> str | None:
        value = (self.coordinator.data.config if self.coordinator.data else {}).get(CFG_BATTERY_BEFORE_CAR)
        actual = None if value is None else (PRIORITY_BATTERY_FIRST if value else PRIORITY_CAR_FIRST)
        return self._value(actual)

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

    def __init__(self, coordinator: HagerFlowCloudCoordinator, entry_id: str, evse_id: int, device_info) -> None:
        super().__init__(coordinator, entry_id, "ladestrategie", device_info)
        self._evse_id = evse_id
        self._attr_unique_id = f"{entry_id}_cloud_ladestrategie_{evse_id}"

    @property
    def _wallbox(self):
        return self.coordinator.data.wallboxes.get(self._evse_id) if self.coordinator.data else None

    @property
    def available(self) -> bool:
        return super().available and self._wallbox is not None

    @property
    def current_option(self) -> str | None:
        return self._value(self._wallbox.strategy if self._wallbox else None)

    async def async_select_option(self, option: str) -> None:
        wallbox, link_id = self._wallbox, self.coordinator.data.emc_link_id
        await self._async_write(
            lambda: self.coordinator.api.async_set_charging_strategy(link_id, wallbox, option),
            option,
        )
