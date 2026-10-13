"""WiFiTIC MQTT realtime data manager."""
from __future__ import annotations
import json
from homeassistant.components import mqtt
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta
import logging

_LOGGER = logging.getLogger(__name__)

class WiFiTICMQTT:
    def __init__(self, hass, base_topic: str):
        self.hass = hass
        self.base_topic = base_topic.rstrip('/')
        self.data = {}
        self.online = None
        self._listeners = []
        self._unsubs = []
        self._retry_unsub = None
        self._starting = False

    async def async_start(self):
        """Subscribe if MQTT is available, otherwise retry without blocking REST."""
        if self._unsubs or self._starting:
            return
        if "mqtt" not in self.hass.data:
            self._schedule_retry()
            return
        self._starting = True
        try:
            self._unsubs.append(await mqtt.async_subscribe(
                self.hass, f"{self.base_topic}/teleinfo", self._teleinfo, 0
            ))
            self._unsubs.append(await mqtt.async_subscribe(
                self.hass, f"{self.base_topic}/online", self._online, 0
            ))
        except HomeAssistantError as err:
            for unsub in self._unsubs:
                unsub()
            self._unsubs.clear()
            _LOGGER.debug("MQTT not available yet: %s", err)
            self._schedule_retry()
        finally:
            self._starting = False
        if self._unsubs and self._retry_unsub is not None:
            self._retry_unsub()
            self._retry_unsub = None

    @callback
    def _schedule_retry(self):
        if self._retry_unsub is None:
            self._retry_unsub = async_track_time_interval(
                self.hass, self._retry_start, timedelta(seconds=30)
            )

    async def _retry_start(self, _now):
        await self.async_start()

    @callback
    def _teleinfo(self, msg):
        try: self.data = json.loads(msg.payload)
        except (ValueError, TypeError): return
        self._notify()

    @callback
    def _online(self, msg):
        self.online = str(msg.payload).lower() in ("1", "true", "online", "on")
        self._notify()

    @callback
    def add_listener(self, listener):
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener) if listener in self._listeners else None

    @callback
    def _notify(self):
        for listener in list(self._listeners): listener()

    async def async_stop(self):
        if self._retry_unsub is not None:
            self._retry_unsub()
            self._retry_unsub = None
        for unsub in self._unsubs: unsub()
        self._unsubs.clear()
