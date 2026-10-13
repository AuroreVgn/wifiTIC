from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

class WiFiTICEntity:
    _attr_has_entity_name = True
    def __init__(self, entry, mqtt):
        self._entry = entry
        self._mqtt = mqtt
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="WiFiTIC",
            manufacturer="CARTELECTRONIC",
            model="WiFiTIC",
            configuration_url=f"http://{entry.data['host']}",
        )
    @property
    def available(self):
        return self._mqtt.online is not False
