import asyncio
import aiohttp
from custom_components.danfoss_solar.api import DanfossSolarAPI

async def main():
    # --- CONFIGURATION ---
    DOMAIN = "<your_inverter_domain_or_ip>" 
    USER = "<your_username>"
    PASS = "<your_password>"
    # ---------------------

    async with aiohttp.ClientSession() as session:
        # Initialize the API with our local session
        api = DanfossSolarAPI(session)
        
        print(f"Connecting to {DOMAIN}...")
        try:
            result = await api.get_inverter_data(DOMAIN, USER, PASS)
            print("\nSuccess! Data retrieved:")
            print(f"Power:            {result['power']} W")
            print(f"Daily Production: {result['daily_production']} Wh")
            print(f"Total Production: {result['total_production']} Wh")
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    asyncio.run(main())