"""Number-Entitäten (nur mit aktiviertem Cloud-Zugang)."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .cloud.const import CFG_BATTERY_BEFORE_CAR, CFG_BATTERY_TO_CAR_BOOST, CFG_BATTERY_TO_CAR_SOLAR
from .cloud.coordinator import HagerFlowCloudCoordinator
from .cloud.entity import HagerFlowCloudEntity, wallbox_device_info
from .data import HagerFlowConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HagerFlowConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richtet die Cloud-Number-Entitäten ein, falls der Cloud-Zugang aktiv ist."""
    cloud = entry.runtime_data.cloud
    if cloud is None:
        return

    modbus_wallboxes = entry.runtime_data.coordinator.discovered_wallboxes
    known: set[int] = set()

    @callback
    def _add_new_wallboxes() -> None:
        if not cloud.data:
            return
        # "Bis Ladezustand" nur anlegen, wenn die Wallbox-Konfiguration den Wert liefert
        new = [
            wb
            for evse_id, wb in cloud.data.wallboxes.items()
            if evse_id not in known and wb.discharge_soc is not None
        ]
        if not new:
            return
        known.update(wb.evse_id for wb in new)
        async_add_entities(
            HagerFlowDischargeSocNumber(
                cloud, entry.entry_id, wb.evse_id, wallbox_device_info(entry.entry_id, wb, modbus_wallboxes)
            )
            for wb in new
        )

    _add_new_wallboxes()
    entry.async_on_unload(cloud.async_add_listener(_add_new_wallboxes))


class HagerFlowDischargeSocNumber(HagerFlowCloudEntity, NumberEntity):
    """Entladegrenze "Bis Ladezustand" (%) – bis zu diesem Ladezustand wird der Speicher
    ins Auto entladen (0 % = keine Grenze)."""

    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:battery-arrow-down"

    def __init__(self, coordinator: HagerFlowCloudCoordinator, entry_id: str, evse_id: int, device_info) -> None:
        super().__init__(coordinator, entry_id, "entladen_bis_ladezustand", device_info)
        self._evse_id = evse_id
        self._attr_unique_id = f"{entry_id}_cloud_entladen_bis_ladezustand_{evse_id}"

    @property
    def _wallbox(self):
        return self.coordinator.data.wallboxes.get(self._evse_id) if self.coordinator.data else None

    @property
    def _config(self) -> dict:
        return self.coordinator.data.config if self.coordinator.data else {}

    @property
    def _discharge_enabled(self) -> bool:
        """Entladegrenze gilt nur, wenn der Speicher überhaupt ins Auto entladen darf –
        also nicht bei "Batterie zuerst" und mit mindestens einem aktiven Entlademodus."""
        c = self._config
        return (
            not c.get(CFG_BATTERY_BEFORE_CAR, False)
            and (c.get(CFG_BATTERY_TO_CAR_SOLAR, False) or c.get(CFG_BATTERY_TO_CAR_BOOST, False))
        )

    @property
    def available(self) -> bool:
        wb = self._wallbox
        return (
            super().available
            and wb is not None
            and wb.discharge_soc is not None
            and self._discharge_enabled
        )

    @property
    def native_value(self) -> float | None:
        wb = self._wallbox
        return self._value(wb.discharge_soc if wb else None)

    async def async_set_native_value(self, value: float) -> None:
        serial, config = self.coordinator.data.emc_serial, self._config
        await self._async_write(
            lambda: self.coordinator.api.async_set_discharge_soc(serial, config, int(value)),
            int(value),
        )
