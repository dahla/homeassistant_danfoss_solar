"""Danfoss Solar API Client."""
import logging
import re
import asyncio

_LOGGER = logging.getLogger(__name__)

# Regex patterns to extract data
SID_PATTERN = re.compile(r"sid=(\d+)")
POWER_PATTERN = re.compile(r'id="curr_power".*?>\s*([\d.]+)\s*([kM]?W)')
DAILY_PATTERN = re.compile(r'id="prod_today".*?>\s*([\d.]+)\s*([kM]?Wh)')
TOTAL_PATTERN = re.compile(r'id="total_yield".*?>\s*([\d.]+)\s*([kM]?Wh)')

class DanfossSolarAPI:
    """Handle communication with Danfoss Solar."""

    def __init__(self, session):
        """
        Initialize the API client.
        :param session: an aiohttp.ClientSession object
        """
        self._session = session
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HomeAssistant-Danfoss/1.0"
        }
        # Cache to prevent "holes" in data which cause spikes in the Energy Dashboard
        self._last_data = {"power": 0, "daily_production": 0, "total_production": 0}

    def _parse_value(self, value_str, unit_str):
        """Convert scraped strings to float and normalize to base unit (W or Wh)."""
        try:
            val = float(value_str)
            unit_str = unit_str.upper()
            
            if "M" in unit_str:
                return int(val * 1000000)
            if "K" in unit_str:
                return int(val * 1000)
            return int(val)
        except (ValueError, TypeError):
            return 0

    async def get_inverter_data(self, domain, username, password):
        """Fetch data from the inverter web interface."""
        try:
            _LOGGER.debug("Attempting to log in to Danfoss Inverter at %s", domain)
            
            # 1. Login Request
            login_url = f"http://{domain}/cgi-bin/handle_login.tcl"
            params = {"user": username, "pw": password, "submit": "Login", "sid": ""}
            
            async with self._session.get(login_url, params=params, headers=self.headers, timeout=10) as resp:
                login_html = await resp.text()
                
            # 2. Extract SID
            sid_match = SID_PATTERN.search(login_html)
            if not sid_match:
                _LOGGER.warning("Failed to extract SID. Inverter might be offline or busy. Returning last known production values.")
                return self._get_offline_data()

            sid = sid_match.group(1)
            _LOGGER.debug("Login successful, obtained SID: %s", sid)

            # 3. Get Overview Data
            overview_url = f"http://{domain}/cgi-bin/overview.tcl"
            async with self._session.get(overview_url, params={"sid": sid}, headers=self.headers, timeout=10) as resp:
                overview_html = await resp.text()

            # 4. Extract Values
            p_match = POWER_PATTERN.search(overview_html)
            d_match = DAILY_PATTERN.search(overview_html)
            t_match = TOTAL_PATTERN.search(overview_html)

            # Only process if we found matches, otherwise fall back to cache
            if d_match and t_match:
                new_data = {
                    "power": self._parse_value(p_match.group(1), p_match.group(2)) if p_match else 0,
                    "daily_production": self._parse_value(d_match.group(1), d_match.group(2)),
                    "total_production": self._parse_value(t_match.group(1), t_match.group(2))
                }
                # Update the cache with successful fetch
                self._last_data = new_data
                _LOGGER.debug("Successfully updated inverter data: %s", new_data)
            else:
                _LOGGER.warning("HTML parsed but production values not found. Using cached data.")

            # 5. Logout (Clean up session)
            try:
                logout_url = f"http://{domain}/cgi-bin/logout.tcl"
                await self._session.get(logout_url, params={"sid": sid}, headers=self.headers, timeout=5)
            except Exception:
                pass # Logout failure is non-critical

            return self._last_data

        except (asyncio.TimeoutError, Exception) as err:
            _LOGGER.error("Communication error with Danfoss Inverter (%s). Providing fallback data to prevent dashboard spikes.", repr(err))
            return self._get_offline_data()

    def _get_offline_data(self):
        """Returns the last known production totals but sets current power to 0."""
        offline_data = self._last_data.copy()
        offline_data["power"] = 0
        return offline_data