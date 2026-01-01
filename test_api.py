import asyncio
import aiohttp
import os
from dotenv import load_dotenv
from custom_components.danfoss_solar.api import DanfossSolarAPI

# Load variables from .env file
load_dotenv()

async def main():
    # Retrieve settings from environment variables
    domain = os.getenv("DANFOSS_DOMAIN")
    username = os.getenv("DANFOSS_USERNAME")
    password = os.getenv("DANFOSS_PASSWORD")

    # Basic validation to ensure .env is set up
    if not all([domain, username, password]):
        print("❌ Error: Missing configuration. Ensure DANFOSS_DOMAIN, "
              "DANFOSS_USERNAME, and DANFOSS_PASSWORD are set in your .env file.")
        return

    async with aiohttp.ClientSession() as session:
        # Initialize the API with our local session
        api = DanfossSolarAPI(session)
        
        print(f"--- Testing Danfoss API Connection ---")
        print(f"Target: {domain}")
        print(f"User:   {username}")
        print(f"Password:   {password}")
        
        try:
            result = await api.get_inverter_data(domain, username, password)
            
            if result:
                print("\n✅ Success! Data retrieved:")
                print(f"Power:            {result['power']} W")
                print(f"Daily Production: {result['daily_production']} Wh")
                print(f"Total Production: {result['total_production']} Wh")
            else:
                print("\n⚠️ Failed: API returned no data (likely login failure).")
                
        except Exception as e:
            print(f"\n❌ Execution Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())