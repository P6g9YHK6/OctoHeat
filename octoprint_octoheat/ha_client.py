import logging
import requests
from typing import Optional

from octoprint_octoheat import const

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    def __init__(self, ha_url: str, ha_token: str, verify_ssl: bool = True):
        self.ha_url = ha_url.rstrip("/")
        self.verify_ssl = verify_ssl
        self.headers = {
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str) -> Optional[dict]:
        url = f"{self.ha_url}{path}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10, verify=self.verify_ssl)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"HA GET {url} failed: {e}")
            return None

    def _post(self, path: str, json: Optional[dict] = None) -> bool:
        url = f"{self.ha_url}{path}"
        try:
            response = requests.post(url, headers=self.headers, json=json, timeout=10, verify=self.verify_ssl)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"HA POST {url} failed: {e}")
            return False

    def get_sensor_state(self, entity_id: str) -> Optional[float]:
        data = self._get(f"/api/states/{entity_id}")
        if data is None:
            return None
        state = data.get("state")
        if state is None:
            return None
        try:
            return float(state)
        except ValueError:
            logger.warning(f"HA sensor {entity_id} state is not a number: {state}")
            return None

    def turn_on_switch(self, entity_id: str) -> bool:
        return self._post(
            "/api/services/switch/turn_on",
            {"entity_id": entity_id}
        )

    def turn_off_switch(self, entity_id: str) -> bool:
        return self._post(
            "/api/services/switch/turn_off",
            {"entity_id": entity_id}
        )

    def test_connection(self) -> bool:
        data = self._get("/api/")
        return data is not None