import hashlib
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select

from app import database
from app.models import Article, Source


async def fetch_and_parse_source(source: Source) -> int:
    """爬取单个数据源，返回新入库文章数"""
    async with database.async_session() as session:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(source.url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                resp.raise_for_status()
        except Exception:
            return 0

        soup = BeautifulSoup(resp.text, "html.parser")
        container = soup.select_one(source.selector_container)
        if not container:
            return 0

        title_els = container.select(source.selector_title)
        link_els = container.select(source.selector_link)
        date_els = container.select(source.selector_date)

        new_count = 0
        for i, title_el in enumerate(title_els):
            title = title_el.get_text(strip=True)
            if not title:
                continue

            # 过滤分页/导航噪音
            if len(title) < 4 or title.isdigit():
                continue
            if title in ("首页", "上页", "下页", "尾页", "末页", "上一页", "下一页", "更多"):
                continue

            href = ""
            if i < len(link_els):
                href = link_els[i].get("href", "")
            else:
                a_tag = title_el.find("a")
                if a_tag:
                    href = a_tag.get("href", "")

            if href and not href.startswith("http"):
                href = urljoin(source.url, href)

            if not href:
                continue

            # 去重
            existing = await session.execute(
                select(Article).where(Article.url == href)
            )
            if existing.scalar_one_or_none():
                continue

            date_str = ""
            if i < len(date_els):
                date_str = date_els[i].get_text(strip=True)

            article = Article(
                title=title[:500],
                url=href,
                source_id=source.id,
                publish_date=date_str[:50] if date_str else None,
                content_hash=hashlib.sha256(title.encode()).hexdigest(),
            )
            session.add(article)
            new_count += 1

        await session.commit()
        return new_count


async def scrape_all_sources() -> dict[str, int]:
    """爬取所有活跃数据源"""
    async with database.async_session() as session:
        result = await session.execute(
            select(Source).where(Source.is_active == True)
        )
        sources = result.scalars().all()

    results = {}
    for source in sources:
        count = await fetch_and_parse_source(source)
        results[source.name] = count
    return results


async def get_recent_articles(
    source_id: int | None = None, page: int = 1, per_page: int = 20
) -> list[Article]:
    """获取最近公告"""
    async with database.async_session() as session:
        q = select(Article).order_by(Article.created_at.desc())
        if source_id:
            q = q.where(Article.source_id == source_id)
        q = q.offset((page - 1) * per_page).limit(per_page)
        result = await session.execute(q)
        return result.scalars().all()
