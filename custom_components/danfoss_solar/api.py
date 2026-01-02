"""Danfoss Solar API Client."""
import logging
import re
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)

# Regex patterns to extract data
SID_PATTERN = re.compile(r"sid=(\d+)")
POWER_PATTERN = re.compile(r'id="curr_power".*?>\s*([\d.]+)\s*([kM]?W)')
DAILY_PATTERN = re.compile(r'id="prod_today".*?>\s*([\d.]+)\s*([kM]?Wh)')
TOTAL_PATTERN = re.compile(r'id="total_yield".*?>\s*([\d.]+)\s*([kM]?Wh)')

class DanfossSolarAPI:
    """Handle communication with Danfoss Solar."""

    def __init__(self, session, log_interval=15):
        """
        Initialize the API client.
        :param session: an aiohttp.ClientSession object
        :param log_interval: minutes to wait before logging a connection error (default 15)
        """
        self._session = session
        self._log_interval = log_interval
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HomeAssistant-Danfoss/1.0"
        }
        
        # Cache to prevent "holes" in data
        self._last_data = {
            "power": 0, 
            "daily_production": 0, 
            "total_production": 0,
            "last_updated": "Never"
        }
        
        # Timing trackers
        self._last_success_time = datetime.min
        self._last_log_time = datetime.min

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
        now = datetime.now()
        
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
                self._handle_error("Failed to extract SID (Login error/Offline)", now)
                return self._get_offline_data()

            sid = sid_match.group(1)

            # 3. Get Overview Data
            overview_url = f"http://{domain}/cgi-bin/overview.tcl"
            async with self._session.get(overview_url, params={"sid": sid}, headers=self.headers, timeout=10) as resp:
                overview_html = await resp.text()

            # 4. Extract Values
            p_match = POWER_PATTERN.search(overview_html)
            d_match = DAILY_PATTERN.search(overview_html)
            t_match = TOTAL_PATTERN.search(overview_html)

            if d_match and t_match:
                self._last_data = {
                    "power": self._parse_value(p_match.group(1), p_match.group(2)) if p_match else 0,
                    "daily_production": self._parse_value(d_match.group(1), d_match.group(2)),
                    "total_production": self._parse_value(t_match.group(1), t_match.group(2)),
                    "last_updated": now.strftime("%Y-%m-%d %H:%M:%S")
                }
                self._last_success_time = now
                _LOGGER.debug("Successfully updated inverter data.")
            else:
                self._handle_error("HTML parsed but data fields were empty", now)

            # 5. Logout
            try:
                logout_url = f"http://{domain}/cgi-bin/logout.tcl"
                await self._session.get(logout_url, params={"sid": sid}, headers=self.headers, timeout=5)
            except Exception:
                pass

            return self._last_data

        except Exception as err:
            self._handle_error(f"Connection error: {repr(err)}", now)
            return self._get_offline_data()

    def _handle_error(self, message, now):
        """Logic to suppress log spam unless offline for > defined interval."""
        # 1. If we've never had a success, log immediately so user knows setup failed
        if self._last_success_time == datetime.min:
            _LOGGER.error("Initial connection failed: %s", message)
            self._last_log_time = now
            return

        time_since_success = now - self._last_success_time
        time_since_log = now - self._last_log_time
        threshold = timedelta(minutes=self._log_interval)

        # 2. Only log if we've passed the threshold AND the cooldown interval
        if time_since_success > threshold and time_since_log > threshold:
            _LOGGER.error(
                "Inverter offline for %s minutes. Last success: %s. Error: %s",
                int(time_since_success.total_seconds() / 60),
                self._last_data["last_updated"],
                message
            )
            # Reset log timer to the current time to start a new cooldown period
            self._last_log_time = now
        else:
            _LOGGER.debug("Inverter connection glitch (suppressed): %s", message)

    def _get_offline_data(self):
        """Returns last known production but sets power to 0."""
        offline_data = self._last_data.copy()
        offline_data["power"] = 0
        return offline_data