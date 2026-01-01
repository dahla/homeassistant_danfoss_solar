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
            # 1. Login Request
            login_url = f"http://{domain}/cgi-bin/handle_login.tcl"
            params = {"user": username, "pw": password, "submit": "Login", "sid": ""}
            
            async with self._session.get(login_url, params=params, headers=self.headers, timeout=10) as resp:
                login_html = await resp.text()
                
            # 2. Extract SID
            sid_match = SID_PATTERN.search(login_html)
            if not sid_match:
                _LOGGER.error("Failed to extract SID. Check credentials or domain.")
                return None
            
            sid = sid_match.group(1)

            # 3. Get Overview Data
            overview_url = f"http://{domain}/cgi-bin/overview.tcl"
            async with self._session.get(overview_url, params={"sid": sid}, headers=self.headers, timeout=10) as resp:
                overview_html = await resp.text()

            # 4. Extract Values
            data = {"power": 0, "daily_production": 0, "total_production": 0}

            p_match = POWER_PATTERN.search(overview_html)
            d_match = DAILY_PATTERN.search(overview_html)
            t_match = TOTAL_PATTERN.search(overview_html)

            if p_match: data["power"] = self._parse_value(p_match.group(1), p_match.group(2))
            if d_match: data["daily_production"] = self._parse_value(d_match.group(1), d_match.group(2))
            if t_match: data["total_production"] = self._parse_value(t_match.group(1), t_match.group(2))

            return data

        except Exception as err:
            _LOGGER.error("Error communicating with Danfoss Inverter: %s", err)
            raise err