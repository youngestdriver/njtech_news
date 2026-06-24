from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import Settings
from app.services.mailer import send_all_digests
from app.services.scraper import scrape_all_sources

scheduler = AsyncIOScheduler()


async def scrape_and_push(settings: Settings):
    """爬取，有新增/修改/删除内容时才推送"""
    results = await scrape_all_sources()
    total_new = sum(r["new"] for r in results.values())
    total_modified = sum(r["modified"] for r in results.values())
    total_deleted = sum(r["deleted"] for r in results.values())
    if total_new > 0 or total_modified > 0 or total_deleted > 0:
        await send_all_digests(settings)


def start_scheduler(settings: Settings):
    interval = max(settings.crawl_interval, 60)
    scheduler.add_job(
        scrape_and_push, "interval", args=[settings],
        seconds=interval, id="sync_job", replace_existing=True,
    )
    scheduler.start()


async def stop_scheduler():
    scheduler.shutdown(wait=False)
