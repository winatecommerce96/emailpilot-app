
import asyncio
from app.services.klaviyo_data_service import KlaviyoDataService

if __name__ == "__main__":
    service = KlaviyoDataService()
    asyncio.run(service.run_daily_sync())
