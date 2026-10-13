from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity import EntityCategory
from .entity import WiFiTICEntity
from .const import DATA_MQTT

async def async_setup_entry(hass, entry, async_add_entities):
    mqtt=hass.data["wifitic"][entry.entry_id][DATA_MQTT]
    async_add_entities([Relay(entry,mqtt,i) for i in range(1,9)])

class Relay(WiFiTICEntity, BinarySensorEntity):
    _attr_entity_registry_enabled_default=False
    _attr_entity_category=EntityCategory.DIAGNOSTIC
    def __init__(self,entry,mqtt,index):
        super().__init__(entry,mqtt); self.index=index; self._attr_name=f"Relais {index}"; self._attr_unique_id=f"{entry.entry_id}_relay_{index}"
    @property
    def is_on(self): return self._mqtt.data.get("consumption",{}).get("relay",{}).get(f"r{self.index}")
    async def async_added_to_hass(self): self.async_on_remove(self._mqtt.add_listener(self.async_write_ha_state))
