from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.event import async_track_time_change
from homeassistant.core import callback
from typing import Callable, Any
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfEnergy, UnitOfPower
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .entity import WiFiTICEntity
from .const import DATA_MQTT, DATA_COORDINATOR

@dataclass(frozen=True)
class Desc:
    key: str; name: str; fn: Callable[[dict], Any]; unit: str | None = None; device_class: SensorDeviceClass | None = None; state_class: SensorStateClass | None = None; category: EntityCategory | None = None

def path(*parts):
    def get(data):
        cur=data
        try:
            for p in parts: cur=cur[p]
            return cur
        except (KeyError, IndexError, TypeError): return None
    return get

# The Linky/WiFiTIC firmware reports contract code 11 for EDF Zen Flex.
# REST is consulted for the contract only; live values remain MQTT-only.
CONTRACT_NAMES = {0: "Non défini", 1: "Base", 2: "Heures pleines / Heures creuses", 3: "EJP", 4: "Tempo", 5: "Production", 6: "Zen", 7: "Zen+", 8: "Super-creuses", 9: "Week-end", 10: "Beaux jours", 11: "Zen Flex", 255: "Contrat personnalisé"}

def contract_name(data):
    counter = data.get("counter") if isinstance(data, dict) else None
    if not isinstance(counter, dict):
        counter = {}
    code = counter.get("contract")
    for key in ("customContrat", "contractName", "contrat", "contractLabel"):
        label = counter.get(key) or data.get(key)
        if isinstance(label, str) and label.strip():
            return label.strip()
    try:
        return CONTRACT_NAMES.get(int(code), f"Contrat inconnu ({code})") if code is not None else None
    except (TypeError, ValueError):
        return str(code) if code is not None else None

def tariff_icon(period):
    if not isinstance(period, str):
        return "mdi:calendar-clock"
    p = period.casefold()
    if "creuse" in p or "hc" == p.strip():
        return "mdi:moon-waning-crescent"
    if "pleine" in p or "hp" == p.strip():
        return "mdi:white-balance-sunny"
    return "mdi:calendar-clock"

MQTT_ONLY_KEYS = frozenset({"apparent_power", "estimated_import_power", "current", "voltage", "injected_power", "production_index", "consumption_today", "production_today", "tariff_period", "supplier_today", "supplier_tomorrow"})

DESCS = [
 Desc("apparent_power","Puissance apparente soutirée",path("consumption","phases",0,"app"),"VA",SensorDeviceClass.APPARENT_POWER,SensorStateClass.MEASUREMENT),
 Desc("estimated_import_power","Puissance soutirée du réseau (estimée)",lambda data: round(value * 0.95) if (value := path("consumption","phases",0,"app")(data)) is not None else None,UnitOfPower.WATT,SensorDeviceClass.POWER,SensorStateClass.MEASUREMENT),
 Desc("current","Intensité instantanée",path("consumption","phases",0,"iinst"),UnitOfElectricCurrent.AMPERE,SensorDeviceClass.CURRENT,SensorStateClass.MEASUREMENT),
 Desc("voltage","Tension réseau",path("counter","phases",0,"voltage"),UnitOfElectricPotential.VOLT,SensorDeviceClass.VOLTAGE,SensorStateClass.MEASUREMENT),
 Desc("injected_power","Puissance injectée sur le réseau",path("production","pprod"),UnitOfPower.WATT,SensorDeviceClass.POWER,SensorStateClass.MEASUREMENT),
 Desc("production_index","Index énergie injectée au réseau",path("production","counter"),UnitOfEnergy.WATT_HOUR,SensorDeviceClass.ENERGY,SensorStateClass.TOTAL_INCREASING),
 Desc("tariff_period","Période tarifaire",path("consumption","runningPeriod")),
 Desc("tic_state","État de la téléinformation",path("counter","state")),
 Desc("subscribed_power","Puissance souscrite au contrat",path("counter","psous"),"kVA"),
 Desc("cutoff_power","Seuil de coupure Linky",path("counter","pcoup"),"kVA"),
 Desc("supplier_today","Profil tarifaire fournisseur aujourd’hui",path("consumption","currentDaySupplier")),
 Desc("supplier_tomorrow","Profil tarifaire fournisseur demain",path("consumption","nextDaySupplier")),
]

async def async_setup_entry(hass, entry, async_add_entities):
    store=hass.data["wifitic"][entry.entry_id]; mqtt=store[DATA_MQTT]; coord=store[DATA_COORDINATOR]
    entities=[MQTTSensor(entry,mqtt,coord,d) for d in DESCS]
    periods=(coord.data or {}).get("periods",{}).get("periods",[])
    count=max(4, len(periods), len(mqtt.data.get("consumption",{}).get("counters",[])))
    for i in range(count): entities.append(IndexSensor(entry,mqtt,coord,i,periods[i] if i < len(periods) else f"Index {i+1}"))
    entities += [MQTTDailySensor(entry,mqtt,"consumption_today","Énergie soutirée aujourd'hui",consumption_total), MQTTDailySensor(entry,mqtt,"production_today","Énergie injectée aujourd'hui",path("production", "counter"))]
    entities += [ContractRESTSensor(entry,mqtt,coord)]
    entities += [RESTSensor(entry,mqtt,coord,"crc_ok","Trames TIC valides",lambda d:d.get("debug",{}).get("crcOk"),True), RESTSensor(entry,mqtt,coord,"crc_error","Erreurs de transmission TIC (CRC)",lambda d:d.get("debug",{}).get("crcError"),True)]
    async_add_entities(entities)

class MQTTSensor(WiFiTICEntity, SensorEntity):
    def __init__(self,entry,mqtt,coord,desc):
        WiFiTICEntity.__init__(self,entry,mqtt); self.coord=coord; self.d=desc; self._attr_unique_id=f"{entry.entry_id}_{desc.key}"; self._attr_name=desc.name; self._attr_native_unit_of_measurement=desc.unit; self._attr_device_class=desc.device_class; self._attr_state_class=desc.state_class
    @property
    def available(self):
        if self.d.key in MQTT_ONLY_KEYS or self.d.key.startswith("index_"):
            return self._mqtt.online is not False and self.d.fn(self._mqtt.data) is not None
        return self.coord.last_update_success and (self.d.fn(self._mqtt.data) is not None or self.d.fn((self.coord.data or {}).get("teleinfo") or {}) is not None)

    @property
    def native_value(self):
        value = self.d.fn(self._mqtt.data)
        if value is not None or self.d.key in MQTT_ONLY_KEYS or self.d.key.startswith("index_"):
            return value
        return self.d.fn((self.coord.data or {}).get("teleinfo") or {})
    @property
    def icon(self):
        if self.d.key == "tariff_period":
            return tariff_icon(self.native_value)
        if self.d.key in ("supplier_today", "supplier_tomorrow"):
            return "mdi:calendar-today" if self.d.key == "supplier_today" else "mdi:calendar-arrow-right"
        icons = {
            "apparent_power": "mdi:flash-outline",
            "estimated_import_power": "mdi:transmission-tower-import",
            "injected_power": "mdi:transmission-tower-export",
            "production_index": "mdi:counter",
            "current": "mdi:current-ac",
            "voltage": "mdi:sine-wave",
            "tic_state": "mdi:check-network-outline",
            "subscribed_power": "mdi:home-lightning-bolt-outline",
            "cutoff_power": "mdi:alert-outline",
        }
        return icons.get(self.d.key)

    @property
    def extra_state_attributes(self):
        if self.d.key in ("supplier_today", "supplier_tomorrow"):
            value = self.native_value
            return {"raw_supplier_code": value, "linky_tic_field": "NJOURF" if self.d.key == "supplier_today" else "NJOURF+1", "interpretation": f"Profil {value}" if value is not None else "Profil indisponible"}
        if self.d.key == "estimated_import_power":
            return {"estimated_power_factor": 0.95, "estimated": True}
        return None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self._mqtt.add_listener(self.async_write_ha_state))
        self.async_on_remove(self.coord.async_add_listener(self.async_write_ha_state))

class IndexSensor(MQTTSensor):
    def __init__(self, entry, mqtt, coord, index, name):
        # Retain stable unique IDs even when the display name is adapted.
        self._original_period_name = name
        d = Desc(f"index_{index+1}", f"Index énergie soutirée – {name}",
                 path("consumption", "counters", index, "value"),
                 UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY,
                 SensorStateClass.TOTAL_INCREASING)
        super().__init__(entry, mqtt, coord, d)

    @property
    def name(self):
        label = self._original_period_name
        contract = path("counter", "contract")(self._mqtt.data)
        if str(contract) == "11" and isinstance(label, str):
            label = label.replace("pointe", "sobriété").replace("Pointe", "Sobriété")
        return f"Index énergie soutirée – {label}"

    @property
    def icon(self):
        return tariff_icon(self.name)

class RESTSensor(CoordinatorEntity, WiFiTICEntity, SensorEntity):
    def __init__(self,entry,mqtt,coord,key,name,fn,diagnostic=False):
        CoordinatorEntity.__init__(self,coord); WiFiTICEntity.__init__(self,entry,mqtt); self.fn=fn; self._attr_unique_id=f"{entry.entry_id}_{key}"; self._attr_name=name
        if key.endswith("today"): self._attr_native_unit_of_measurement=UnitOfEnergy.WATT_HOUR; self._attr_device_class=SensorDeviceClass.ENERGY; self._attr_state_class=SensorStateClass.TOTAL
        if diagnostic: self._attr_entity_category=EntityCategory.DIAGNOSTIC; self._attr_entity_registry_enabled_default=False
    @property
    def available(self):
        return self.coordinator.last_update_success
    @property
    def native_value(self): return self.fn(self.coordinator.data or {})


class ContractRESTSensor(RESTSensor):
    """Contract label from REST teleinfo; firmware code 11 is Zen Flex."""
    def __init__(self, entry, mqtt, coord):
        super().__init__(entry, mqtt, coord, "contract_name", "Contrat électrique", lambda d: contract_name(d.get("teleinfo") or {}))

    @property
    def icon(self):
        return "mdi:file-document-outline"

    @property
    def extra_state_attributes(self):
        data = (self.coordinator.data or {}).get("teleinfo") or {}
        return {"contract_code": path("counter", "contract")(data)}


def consumption_total(data: dict):
    """Total of all four tariff indexes, in Wh; never assume missing indexes are zero."""
    counters = path("consumption", "counters")(data)
    if not isinstance(counters, list) or len(counters) < 4:
        return None
    try:
        return sum(int(item["value"]) for item in counters)
    except (TypeError, ValueError, KeyError):
        return None


class MQTTDailySensor(WiFiTICEntity, RestoreEntity, SensorEntity):
    """Daily MQTT counter delta, restored across HA restarts.

    At midnight the running total resets but the last counter baseline is retained.
    When HA was stopped across midnight, the first reading becomes the new
    baseline to avoid attributing yesterday's consumption to today.
    """

    def __init__(self, entry, mqtt, key, name, index_fn):
        WiFiTICEntity.__init__(self, entry, mqtt)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._index_fn = index_fn
        self._total = 0
        self._last_index = None
        self._day = date.today().isoformat()
        self._has_sample = False

    @property
    def icon(self):
        return "mdi:transmission-tower-import" if self._attr_unique_id.endswith("_consumption_today") else "mdi:transmission-tower-export"

    @property
    def native_value(self):
        return self._total if self._has_sample else None

    @property
    def available(self):
        return self._mqtt.online is not False and self._has_sample

    @property
    def extra_state_attributes(self):
        return {"counter_baseline_wh": self._last_index, "counter_day": self._day}

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        old = await self.async_get_last_state()
        if old is not None:
            attrs = old.attributes
            try:
                baseline = attrs.get("counter_baseline_wh")
                self._last_index = int(baseline) if baseline is not None else None
                previous_day = attrs.get("counter_day")
                if previous_day == date.today().isoformat() and old.state not in (
                    "unknown", "unavailable"
                ):
                    self._total = max(0, int(float(old.state)))
                    self._has_sample = self._last_index is not None
                else:
                    self._day = date.today().isoformat()
                    self._total = 0
                    self._has_sample = False
            except (ValueError, TypeError):
                self._last_index = None
        self.async_on_remove(self._mqtt.add_listener(self._on_mqtt))
        self.async_on_remove(async_track_time_change(
            self.hass, self._on_midnight, hour=0, minute=0, second=0
        ))
        self._on_mqtt()

    @callback
    def _on_midnight(self, _now):
        self._day = date.today().isoformat()
        self._total = 0
        # Retain last index so the first MQTT message after midnight counts.
        self.async_write_ha_state()

    @callback
    def _on_mqtt(self):
        value = self._index_fn(self._mqtt.data)
        if value is None:
            return
        try:
            index = int(value)
        except (TypeError, ValueError):
            return
        today = date.today().isoformat()
        if self._day != today:
            # No midnight callback (e.g. HA was stopped): avoid carrying
            # unobserved consumption from the previous day into today.
            self._day = today
            self._total = 0
            self._last_index = index
        elif self._last_index is not None and index >= self._last_index:
            self._total += index - self._last_index
        self._last_index = index
        self._has_sample = True
        self.async_write_ha_state()
