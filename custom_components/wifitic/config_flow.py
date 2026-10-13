from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import WiFiTICApi, WiFiTICApiError, WiFiTICAuthError
from .const import DOMAIN, CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC

class WiFiTICConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input:
            api = WiFiTICApi(async_get_clientsession(self.hass), user_input[CONF_HOST], user_input.get(CONF_USERNAME), user_input.get(CONF_PASSWORD))
            try:
                info = await api.teleinfo()
            except WiFiTICAuthError: errors["base"] = "invalid_auth"
            except WiFiTICApiError: errors["base"] = "cannot_connect"
            else:
                meter = info.get("counter", {}).get("id") or user_input[CONF_HOST]
                await self.async_set_unique_id(f"wifitic_{meter}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="WiFiTIC", data=user_input)
        schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Optional(CONF_USERNAME, default=""): str,
            vol.Optional(CONF_PASSWORD, default=""): str,
            vol.Required(CONF_MQTT_TOPIC, default=DEFAULT_MQTT_TOPIC): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
