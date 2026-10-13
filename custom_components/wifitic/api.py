"""Local REST API client for CARTELECTRONIC WiFiTIC."""
from __future__ import annotations

from typing import Any
from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout, BasicAuth

class WiFiTICApiError(Exception):
    """Base API error."""

class WiFiTICAuthError(WiFiTICApiError):
    """Authentication error."""

class WiFiTICApi:
    def __init__(self, session: ClientSession, host: str, username: str | None = None, password: str | None = None) -> None:
        self._session = session
        self.host = host.strip().replace("http://", "").replace("https://", "").rstrip("/")
        self._base = f"http://{self.host}"
        self._auth = BasicAuth(username, password or "") if username else None
        self._timeout = ClientTimeout(total=10)

    async def _get(self, path: str) -> dict[str, Any]:
        try:
            async with self._session.get(self._base + path, auth=self._auth, timeout=self._timeout) as response:
                if response.status == 401:
                    raise WiFiTICAuthError("Authentication required or invalid credentials")
                response.raise_for_status()
                return await response.json(content_type=None)
        except WiFiTICAuthError:
            raise
        except (ClientError, ClientResponseError, TimeoutError, ValueError) as err:
            raise WiFiTICApiError(str(err)) from err

    async def teleinfo(self): return await self._get("/rest/teleinfo")
    async def teleinfo_day(self): return await self._get("/rest/teleinfo/jour")
    async def periods(self): return await self._get("/rest/teleinfo/periods")
    async def configuration(self): return await self._get("/rest/configuration")
    async def mqtt_configuration(self): return await self._get("/rest/configuration/MQTT")
    async def teleinfo_debug(self): return await self._get("/rest/debug/teleinfo")
    async def history_year(self, year: int): return await self._get(f"/rest/data/{year}")
    async def history_day(self, year: int, day: int): return await self._get(f"/rest/data/{year}/{day}")
