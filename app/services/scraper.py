import asyncio
import hashlib
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag
from sqlalchemy import select

from app import database
from app.config import Settings
from app.models import Article, Source

NOISE_TITLES = {
    "首页", "上页", "下页", "尾页", "末页", "上一页", "下一页", "更多",
    "学校主页", "网站首页", "English", "旧版回顾",
    # Common navigation labels on NJTech school sites
    "学院新闻", "学工动态", "通知公告", "科研信息", "院务公告", "学生事务",
    "媒体化学", "学习园地", "学院概况", "党群工作", "师资队伍", "人才培养",
    "科学研究", "招生就业", "学生工作", "校友工作", "人才招聘", "党建工作",
    "团学工作", "学术交流", "国际合作", "社会服务",
}

DATE_PATTERN = re.compile(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})')


def _normalize_date(raw: str) -> str:
    m = DATE_PATTERN.search(raw)
    if not m:
        return raw
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def _extract_date(text: str) -> str:
    return _normalize_date(text)


def _is_nav_url(href: str) -> bool:
    """Check if a URL looks like a navigation/category page, not an article."""
    if not href:
        return True
    # Article URLs typically have /info/ or article.jsp paths
    if '/info/' in href or 'article.jsp' in href:
        return False
    # Short navigation URLs like xyxw.htm, tzgg.htm without a path
    if href.endswith('.htm') and '/' not in href.replace('../', '').replace('./', ''):
        return True
    return False


def _is_noise(title: str) -> bool:
    title = title.strip()
    if not title or len(title) < 4 or title.isdigit():
        return True
    if title in NOISE_TITLES:
        return True
    return False


def _find_items(container: Tag, source: Source) -> list[Tag]:
    """Find list items within the container, using selector_item if configured."""
    if source.selector_item:
        items = container.select(source.selector_item)
        if items:
            return items

    # Auto-detect: look for a list wrapper then its children
    for wrapper_tag in ['ul', 'ol', 'tbody', 'table']:
        wrapper = container.find(wrapper_tag, recursive=True)
        if wrapper:
            if wrapper_tag in ('ul', 'ol'):
                items = wrapper.find_all('li', recursive=False)
            elif wrapper_tag == 'tbody':
                items = wrapper.find_all('tr', recursive=False)
            else:
                items = wrapper.find_all('tr', recursive=False)
            if items:
                return items

    # Fallback: direct a tags with href pointing to article pages
    return container.find_all('a', href=True, recursive=True)


def _find_smart_table(soup: BeautifulSoup, source: Source) -> Tag | None:
    """When container selector is 'table', find the table with article links.

    Uses the source's link selector to locate the right table, then falls back
    to counting article-like links in each table.
    """
    # Strategy 1: use the configured link selector to locate the parent table
    if source.selector_link:
        sample = soup.select_one(source.selector_link)
        if sample:
            parent = sample.find_parent('table')
            if parent is not None:
                return parent

    # Strategy 2: count non-noise links per table and pick the best one
    tables = soup.find_all('table')
    best_table = None
    best_count = 0
    for table in tables:
        links = table.find_all('a', href=True)
        article_links = [
            a for a in links
            if not _is_noise(a.get_text(strip=True))
            and a.get('href', '').strip() not in ('#', '/')
        ]
        count = len(article_links)
        if count > best_count:
            best_count = count
            best_table = table
    return best_table


def _extract_from_item(item: Tag, source: Source) -> tuple[str, str, str]:
    """Extract title, href, and date string from a single item element."""
    # --- Find the link element ---
    link_el = None
    if source.selector_link:
        candidates = item.select(source.selector_link)
        if candidates:
            link_el = candidates[0]
    if not link_el:
        link_el = item.find('a', href=True)
    if not link_el and item.name == 'a' and item.get('href'):
        link_el = item

    if not link_el:
        return ("", "", "")

    href = (link_el.get('href') or '').strip()

    # --- Find the title text ---
    title = ""
    if source.selector_title:
        candidates = item.select(source.selector_title)
        if candidates:
            title = candidates[0].get_text(strip=True)
    if not title:
        title = link_el.get_text(strip=True)
    if not title:
        title = item.get_text(strip=True)

    # --- Find the date ---
    date_str = ""
    if source.selector_date:
        candidates = item.select(source.selector_date)
        if candidates:
            date_str = candidates[0].get_text(strip=True)
    if not date_str:
        date_str = _extract_date(item.get_text())

    return (title, href, date_str)


async def fetch_and_parse_source(source: Source) -> dict[str, int]:
    """Fetch and parse a single source, returning {new, modified, deleted} counts."""
    settings = Settings()
    new_count = 0
    modified_count = 0
    visible_urls: set[str] = set()

    async with database.async_session() as session:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(source.url, headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36"
                    )
                })
                resp.raise_for_status()
        except Exception:
            return {"new": 0, "modified": 0, "deleted": 0}

        soup = BeautifulSoup(resp.text, "html.parser")

        # --- Locate the container ---
        container: Tag | None = None
        if source.selector_container == 'table':
            container = _find_smart_table(soup, source)
        else:
            container = soup.select_one(source.selector_container)

        if not container:
            return {"new": 0, "modified": 0, "deleted": 0}

        items = _find_items(container, source)

        for item in items:
            title, href, date_str = _extract_from_item(item, source)

            if _is_noise(title):
                continue
            if _is_nav_url(href):
                continue

            if href and not href.startswith('http'):
                href = urljoin(source.url, href)

            if not href or href == source.url:
                continue

            visible_urls.add(href)

            existing_result = await session.execute(
                select(Article).where(Article.url == href)
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                # --- Modification detection ---
                new_title_clean = title.strip()
                old_title_clean = (existing.title or "").strip()
                if new_title_clean and old_title_clean and new_title_clean != old_title_clean:
                    existing.previous_title = existing.title
                    existing.title = title[:500]
                    existing.is_modified = True
                    existing.modified_at = datetime.now()
                    existing.content_hash = hashlib.sha256(title.encode()).hexdigest()
                    modified_count += 1
                continue

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

    # --- Deletion detection (fresh session) ---
    deleted_count = 0
    if visible_urls:
        cutoff = datetime.now() - timedelta(days=settings.deletion_lookback_days)

        async with database.async_session() as del_session:
            candidates_result = await del_session.execute(
                select(Article).where(
                    Article.source_id == source.id,
                    Article.created_at >= cutoff,
                    Article.is_deleted == False,
                    Article.url.notin_(visible_urls)
                )
            )
            candidates = candidates_result.scalars().all()

            if candidates:
                semaphore = asyncio.Semaphore(5)

                async def _verify_deletion(article: Article) -> bool:
                    async with semaphore:
                        try:
                            async with httpx.AsyncClient(timeout=15) as client:
                                resp = await client.head(article.url, headers={
                                    "User-Agent": (
                                        "Mozilla/5.0 (compatible; NjtechNews/1.0)"
                                    )
                                })
                                if resp.status_code >= 400:
                                    return True
                                resp2 = await client.get(article.url, headers={
                                    "User-Agent": (
                                        "Mozilla/5.0 (compatible; NjtechNews/1.0)"
                                    )
                                })
                                return resp2.status_code >= 400
                        except Exception:
                            return True

                tasks = [_verify_deletion(a) for a in candidates]
                results = await asyncio.gather(*tasks)

                now = datetime.now()
                for article, is_gone in zip(candidates, results):
                    if is_gone:
                        article.is_deleted = True
                        article.deleted_at = now
                        deleted_count += 1

                await del_session.commit()

    return {"new": new_count, "modified": modified_count, "deleted": deleted_count}


async def scrape_all_sources() -> dict[str, dict[str, int]]:
    """Scrape all active sources, returning {source_name: {new, modified, deleted}}."""
    async with database.async_session() as session:
        result = await session.execute(
            select(Source).where(Source.is_active == True)
        )
        sources = result.scalars().all()

    results = {}
    for source in sources:
        counts = await fetch_and_parse_source(source)
        results[source.name] = counts
    return results


async def get_recent_articles(
    source_id: int | None = None, page: int = 1, per_page: int = 20
) -> list[Article]:
    """Get recent articles with optional source filter and pagination."""
    async with database.async_session() as session:
        q = (
            select(Article)
            .where(Article.is_deleted == False)
            .order_by(Article.created_at.desc())
        )
        if source_id:
            q = q.where(Article.source_id == source_id)
        q = q.offset((page - 1) * per_page).limit(per_page)
        result = await session.execute(q)
        return result.scalars().all()
