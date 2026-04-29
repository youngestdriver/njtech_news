from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app import database
from app.config import Settings
from app.models import Source
from app.routers import pages
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.scraper import scrape_all_sources

settings = Settings()
templates = Jinja2Templates(directory="templates")


async def load_sources_from_yaml(path: str = "sources.yaml"):
    """从 YAML 文件加载数据源到数据库（幂等：按 URL 去重）"""
    if not Path(path).exists():
        return
    with open(path) as f:
        sources_data = yaml.safe_load(f)
    if not sources_data:
        return

    async with database.async_session() as session:
        for src in sources_data:
            existing = await session.execute(
                select(Source).where(Source.url == src["url"])
            )
            row = existing.scalar_one_or_none()
            if row:
                # Update selectors in case YAML changed
                for field in (
                    "selector_container", "selector_item",
                    "selector_title", "selector_link", "selector_date",
                ):
                    if field in src:
                        setattr(row, field, src[field])
                row.is_active = src.get("is_active", True)
                row.name = src.get("name", row.name)
                row.category = src.get("category", row.category)
            else:
                session.add(Source(**src))
        await session.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await database.init_db(settings)
    await load_sources_from_yaml()
    await scrape_all_sources()
    start_scheduler(settings)
    yield
    await stop_scheduler()


app = FastAPI(title="NJTech News", lifespan=lifespan)


@app.middleware("http")
async def add_jinja_access(request: Request, call_next):
    request.state.jinja = templates
    response = await call_next(request)
    return response


app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(pages.router)
