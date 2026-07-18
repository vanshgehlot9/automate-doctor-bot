import asyncio
from app.services.scheduler_service import scheduler_service

async def main():
    print("Sending checkins...")
    await scheduler_service.send_mood_checkins()
    print("Done")

asyncio.run(main())
