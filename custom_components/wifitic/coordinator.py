"""REST coordinator for WiFiTIC."""
from __future__ import annotations
import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import WiFiTICApi, WiFiTICApiError
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

class WiFiTICCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api: WiFiTICApi):
        super().__init__(hass, logger=_LOGGER, name=DOMAIN, update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL))
        self.api = api

    async def _async_update_data(self):
        try:
            teleinfo = await self.api.teleinfo()
        except WiFiTICApiError as err:
            raise UpdateFailed(f"Unable to fetch /rest/teleinfo: {err}") from err
        data = {"teleinfo": teleinfo}
        for key, method in (
            ("day", self.api.teleinfo_day),
            ("periods", self.api.periods),
            ("debug", self.api.teleinfo_debug),
            ("config", self.api.configuration),
            ("mqtt", self.api.mqtt_configuration),
        ):
            try:
                data[key] = await method()
            except WiFiTICApiError as err:
                _LOGGER.warning("WiFiTIC REST endpoint %s unavailable: %s", key, err)
                data[key] = (self.data or {}).get(key, {})
        return data
