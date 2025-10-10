from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.future import select
from datetime import datetime, timezone
from app.database import AsyncSessionLocal
from app.models.content import Content, ContentStatus
import logging

scheduler = AsyncIOScheduler()

logger = logging.getLogger(__name__)

async def publish_scheduled_content(content_id: int):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Content).where(Content.id == content_id))
        content = result.scalars().first()

        if content and content.status == ContentStatus.DRAFT:
            content.status = ContentStatus.PUBLISHED
            content.publish_date = datetime.now(timezone.utc)
            content.updated_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info(f"[Scheduler] Content ID {content_id} published at scheduled  time.")

def schedule_content(content_id: int, publish_time: datetime):
    scheduler.add_job(
        publish_scheduled_content,
        trigger=DateTrigger(run_date=publish_time),
        args=[content_id],
        id=f"publish_{content_id}",
        replace_existing=True
    )
    logger.info(f"[Scheduler] Job scheduled for content ID {content_id} at {publish_time}")