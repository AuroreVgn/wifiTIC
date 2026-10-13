from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory
from .entity import WiFiTICEntity
from .const import DATA_MQTT, DATA_COORDINATOR
async def async_setup_entry(hass,entry,async_add_entities):
    s=hass.data["wifitic"][entry.entry_id]; async_add_entities([Refresh(entry,s[DATA_MQTT],s[DATA_COORDINATOR])])
class Refresh(WiFiTICEntity,ButtonEntity):
    _attr_name="Actualiser les données REST"; _attr_entity_category=EntityCategory.CONFIG
    def __init__(self,e,m,c): super().__init__(e,m); self.c=c; self._attr_unique_id=f"{e.entry_id}_refresh"
    async def async_press(self): await self.c.async_request_refresh()
