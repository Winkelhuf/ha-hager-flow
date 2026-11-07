"""Number-Entitäten (nur mit aktiviertem Cloud-Zugang)."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, UnitOfEnergy
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .cloud.api import min_discharge_soc, reserve_percent
from .cloud.const import (
    CFG_BATTERY_BEFORE_CAR,
    CFG_BATTERY_TO_CAR_BOOST,
    CFG_BATTERY_TO_CAR_SOLAR,
    DISCHARGE_RESERVE_MARGIN_PCT,
)
from .cloud.coordinator import HagerFlowCloudCoordinator
from .cloud.entity import HagerFlowCloudEntity, emc_device_info, wallbox_device_info
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
    reserve_added = False

    @callback
    def _add_entities() -> None:
        nonlocal reserve_added
        if not cloud.data:
            return

        # Notstromreserve einmal anlegen, sobald der Speicher-Link einen Wert liefert
        if not reserve_added and cloud.data.storage_link_id is not None and cloud.data.reserve_wh is not None:
            reserve_added = True
            async_add_entities([HagerFlowEmergencyReserveNumber(cloud, entry.entry_id)])

        # "Bis Ladezustand" je Wallbox, sobald die Wallbox-Konfiguration den Wert liefert
        new = [
            wb
            for evse_id, wb in cloud.data.wallboxes.items()
            if evse_id not in known and wb.discharge_soc is not None
        ]
        if new:
            known.update(wb.evse_id for wb in new)
            async_add_entities(
                HagerFlowDischargeSocNumber(
                    cloud, entry.entry_id, wb.evse_id, wallbox_device_info(entry.entry_id, wb, modbus_wallboxes)
                )
                for wb in new
            )

    _add_entities()
    entry.async_on_unload(cloud.async_add_listener(_add_entities))


class HagerFlowEmergencyReserveNumber(HagerFlowCloudEntity, NumberEntity):
    """Notstromreserve (Wh) – Energie, die der Speicher für den Notstromfall zurückhält.

    Gekoppelt an das Entladelimit: wird die Reserve erhöht, zieht das Limit bei Bedarf nach,
    damit es nie unter die Reserve fällt (siehe DISCHARGE_RESERVE_MARGIN_PCT)."""

    _attr_native_min_value = 0
    _attr_native_step = 100
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:home-battery-outline"

    def __init__(self, coordinator: HagerFlowCloudCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id, "notstromreserve", emc_device_info(entry_id))

    @property
    def native_max_value(self) -> float:
        # Höchstens die ganze Batteriekapazität; ohne bekannte Kapazität ein großzügiger Wert
        cap = self.coordinator.data.capacity_wh if self.coordinator.data else None
        return float(cap) if cap else 100000.0

    @property
    def native_value(self) -> float | None:
        return self._value(self.coordinator.data.reserve_wh if self.coordinator.data else None)

    @property
    def extra_state_attributes(self) -> dict[str, float | int | None]:
        data = self.coordinator.data
        if not data:
            return {}
        pct = reserve_percent(data.reserve_wh, data.capacity_wh)
        return {
            "batteriekapazitaet_wh": data.capacity_wh,
            "batteriemodule": data.battery_count,
            "reserve_prozent": round(pct, 1) if pct is not None else None,
            "mindest_entladelimit_prozent": min_discharge_soc(data.reserve_wh, data.capacity_wh),
        }

    async def async_set_native_value(self, value: float) -> None:
        await self._async_write(lambda: self._async_apply(int(value)), int(value))

    async def _async_apply(self, reserve_wh: int) -> None:
        data = self.coordinator.data
        await self.coordinator.api.async_set_emergency_reserve(
            data.storage_link_id, data.storage_config, data.storage_name, reserve_wh
        )
        # Entladelimit nachziehen, damit es nie unter die (neue) Reserve fällt
        await self._async_enforce_limit(reserve_wh)

    async def _async_enforce_limit(self, reserve_wh: int) -> None:
        data = self.coordinator.data
        config = data.config
        discharge_on = not config.get(CFG_BATTERY_BEFORE_CAR, False) and (
            config.get(CFG_BATTERY_TO_CAR_SOLAR, False) or config.get(CFG_BATTERY_TO_CAR_BOOST, False)
        )
        if not discharge_on:
            return
        floor = min_discharge_soc(reserve_wh, data.capacity_wh)
        for wallbox in data.wallboxes.values():
            if wallbox.discharge_soc is not None and wallbox.discharge_soc < floor:
                # loading-priorisation ist systemweit – ein Schreibvorgang genügt
                await self.coordinator.api.async_set_discharge_soc(data.emc_serial, config, floor)
                break


class HagerFlowDischargeSocNumber(HagerFlowCloudEntity, NumberEntity):
    """Entladegrenze "Bis Ladezustand" (%) – bis zu diesem Ladezustand wird der Speicher
    ins Auto entladen. Die Untergrenze ergibt sich aus der Notstromreserve plus Marge."""

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
        return not c.get(CFG_BATTERY_BEFORE_CAR, False) and (
            c.get(CFG_BATTERY_TO_CAR_SOLAR, False) or c.get(CFG_BATTERY_TO_CAR_BOOST, False)
        )

    @property
    def native_min_value(self) -> float:
        """Dynamische Untergrenze: Reserve-% + Marge (nie unter die Notstromreserve)."""
        data = self.coordinator.data
        if not data:
            return float(DISCHARGE_RESERVE_MARGIN_PCT)
        return float(min_discharge_soc(data.reserve_wh, data.capacity_wh))

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

    @property
    def extra_state_attributes(self) -> dict[str, float | int | None]:
        data = self.coordinator.data
        if not data:
            return {}
        return {
            "notstromreserve_wh": data.reserve_wh,
            "untergrenze_prozent": min_discharge_soc(data.reserve_wh, data.capacity_wh),
        }

    async def async_set_native_value(self, value: float) -> None:
        data = self.coordinator.data
        # Nie unter die Reserve-Untergrenze – notfalls hochziehen
        floor = min_discharge_soc(data.reserve_wh, data.capacity_wh)
        target = max(int(value), floor)
        await self._async_write(
            lambda: self.coordinator.api.async_set_discharge_soc(data.emc_serial, self._config, target),
            target,
        )
