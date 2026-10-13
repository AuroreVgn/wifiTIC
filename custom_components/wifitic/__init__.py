from __future__ import annotations
from datetime import date
import voluptuous as vol
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import config_validation as cv
from .api import WiFiTICApi
from .coordinator import WiFiTICCoordinator
from .mqtt import WiFiTICMQTT
from .history import preview_history, merge_native_consumption_history
from .const import DOMAIN, PLATFORMS, CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC, DATA_API, DATA_COORDINATOR, DATA_MQTT

async def async_setup(hass, config):
    async def preview(call):
        """Preview historical REST data without requiring hass.data to contain the entry."""
        configured = hass.config_entries.async_entries(DOMAIN)
        requested = call.data.get("config_entry_id")
        if requested:
            entry = next((item for item in configured if item.entry_id == requested), None)
            if entry is None:
                raise ValueError(
                    f"WiFiTIC config entry {requested} not found. "
                    f"Configured entries: {[item.entry_id for item in configured]}"
                )
        elif len(configured) == 1:
            entry = configured[0]
        elif not configured:
            raise ValueError("No WiFiTIC config entry found")
        else:
            raise ValueError("Multiple WiFiTIC entries found; specify config_entry_id")

        # Build a dedicated REST client from the config entry. This service must
        # not depend on internal hass.data layout or a running MQTT coordinator.
        api = WiFiTICApi(
            async_get_clientsession(hass),
            entry.data[CONF_HOST],
            entry.data.get(CONF_USERNAME) or None,
            entry.data.get(CONF_PASSWORD) or None,
        )
        return await preview_history(
            hass, api, entry.entry_id,
            date.fromisoformat(call.data["start_date"]),
            date.fromisoformat(call.data["end_date"]),
        )

    if not hass.services.has_service(DOMAIN, SERVICE_PREVIEW):
        hass.services.async_register(
            DOMAIN,
            SERVICE_PREVIEW,
            preview,
            schema=vol.Schema({
                vol.Optional("config_entry_id"): cv.string,
                vol.Required("start_date"): cv.string,
                vol.Required("end_date"): cv.string,
            }),
            supports_response=True,
        )
    async def merge_energy(call):
        configured = hass.config_entries.async_entries(DOMAIN)
        requested = call.data.get("config_entry_id")
        if requested:
            entry = next((item for item in configured if item.entry_id == requested), None)
            if entry is None:
                raise ValueError("WiFiTIC config entry not found")
        elif len(configured) == 1:
            entry = configured[0]
        else:
            raise ValueError("Specify config_entry_id for WiFiTIC")
        api = WiFiTICApi(async_get_clientsession(hass), entry.data[CONF_HOST],
                         entry.data.get(CONF_USERNAME) or None,
                         entry.data.get(CONF_PASSWORD) or None)
        return await merge_native_consumption_history(
            hass, api, entry.entry_id,
            date.fromisoformat(call.data["start_date"]),
            date.fromisoformat(call.data["end_date"]),
            call.data.get("confirm_write", False),
            call.data.get("include_injection", True),
            call.data.get("include_consumption", True),
        )

    if not hass.services.has_service(DOMAIN, "merge_native_energy_history"):
        hass.services.async_register(
            DOMAIN, "merge_native_energy_history", merge_energy,
            schema=vol.Schema({
                vol.Optional("config_entry_id"): cv.string,
                vol.Required("start_date"): cv.string,
                vol.Required("end_date"): cv.string,
                vol.Optional("include_injection", default=True): cv.boolean,
                vol.Optional("include_consumption", default=True): cv.boolean,
                vol.Optional("confirm_write", default=False): cv.boolean,
            }), supports_response=True)
    return True

async def async_setup_entry(hass, entry):
    api=WiFiTICApi(async_get_clientsession(hass),entry.data[CONF_HOST],entry.data.get(CONF_USERNAME) or None,entry.data.get(CONF_PASSWORD) or None)
    coordinator=WiFiTICCoordinator(hass,api); await coordinator.async_config_entry_first_refresh()
    mqtt=WiFiTICMQTT(hass,entry.data.get(CONF_MQTT_TOPIC,DEFAULT_MQTT_TOPIC))
    await mqtt.async_start()
    hass.data.setdefault(DOMAIN,{})[entry.entry_id]={DATA_API:api,DATA_COORDINATOR:coordinator,DATA_MQTT:mqtt}
    await hass.config_entries.async_forward_entry_setups(entry,PLATFORMS)
    return True

async def async_unload_entry(hass,entry):
    ok=await hass.config_entries.async_unload_platforms(entry,PLATFORMS)
    if ok:
        await hass.data[DOMAIN][entry.entry_id][DATA_MQTT].async_stop(); hass.data[DOMAIN].pop(entry.entry_id)
    return ok
