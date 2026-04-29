import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import or_, select

from app import database
from app.config import Settings
from app.models import Article, Source, Subscribe, Subscriber
from app.services.mailer import send_verification_code

settings = Settings()
router = APIRouter()


# ── 辅助函数 ──────────────────────────────────────────────

async def get_all_sources() -> list[Source]:
    async with database.async_session() as session:
        result = await session.execute(
            select(Source)
            .where(Source.is_active == True)
            .order_by(Source.category, Source.name)
        )
        return result.scalars().all()


async def get_articles_page(
    source_id: int | None = None, page: int = 1, per_page: int = 20
):
    async with database.async_session() as session:
        q = (
            select(Article)
            .order_by(Article.publish_date.desc().nullslast(), Article.created_at.desc())
        )
        if source_id:
            q = q.where(Article.source_id == source_id)
        offset = (page - 1) * per_page
        result = await session.execute(q.offset(offset).limit(per_page))
        articles = result.scalars().all()
        source_map = {s.id: s.name for s in await get_all_sources()}
        return articles, source_map


def render(request: Request, name: str, **kw):
    return HTMLResponse(
        request.state.jinja.get_template(name).render(request=request, **kw)
    )


# ── 页面路由 ──────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    source_id: int | None = Query(default=None),
    page: int = Query(default=1),
):
    articles, source_map = await get_articles_page(
        source_id if source_id and source_id > 0 else None, page
    )
    sources = await get_all_sources()
    return render(
        request, "index.html",
        articles=articles, source_map=source_map,
        sources=sources, current_source=source_id, page=page,
    )


@router.get("/sources", response_class=HTMLResponse)
async def sources_page(request: Request):
    return render(request, "sources.html", sources=await get_all_sources())


# ── 订阅三步流程 ──────────────────────────────────────────

@router.get("/subscribe", response_class=HTMLResponse)
async def subscribe_page(
    request: Request,
    step: str = Query(default="1"),
    email: str = Query(default=""),
):
    return render(
        request, "subscribe.html",
        step=step, email=email, error="",
        crawl_interval=settings.crawl_interval,
        sources=await get_all_sources(),
    )


@router.post("/subscribe")
async def subscribe_start(
    request: Request,
    student_id: str = Form(...),
    email: str = Form(...),
):
    """步骤 1：提交学号 + 邮箱，发送验证码"""
    async with database.async_session() as session:
        # 检查学号是否已被其他已认证用户绑定
        existing = await session.execute(
            select(Subscriber).where(
                Subscriber.is_active == True,
                Subscriber.student_id == student_id,
            )
        )
        if existing.scalar_one_or_none():
            return render(
                request, "subscribe.html",
                step="1", email="", error="该学号已被其他邮箱绑定",
                sources=await get_all_sources(),
            )

        # 查找或创建订阅者记录（此时不绑学号，等验证通过再绑）
        existing = await session.execute(
            select(Subscriber).where(Subscriber.email == email)
        )
        subscriber = existing.scalar_one_or_none()
        if subscriber:
            subscriber.is_active = True
        else:
            subscriber = Subscriber(email=email, is_verified=False)
            session.add(subscriber)

        # 暂存待绑定的学号
        subscriber.pending_student_id = student_id

        # 生成验证码
        code = f"{random.randint(0, 999999):06d}"
        subscriber.verification_code = code
        subscriber.verification_code_expires_at = datetime.now() + timedelta(minutes=5)
        await session.commit()

    # 发送验证码邮件
    ok = await send_verification_code(settings, email, code)
    if not ok:
        return render(
            request, "subscribe.html",
            step="1", email="", error="验证码发送失败，请检查邮箱地址或稍后重试",
            sources=await get_all_sources(),
        )

    return RedirectResponse(
        url=f"/subscribe?step=verify&email={email}", status_code=303
    )


@router.post("/subscribe/resend")
async def subscribe_resend(request: Request, email: str = Form(...)):
    """重新发送验证码"""
    async with database.async_session() as session:
        result = await session.execute(
            select(Subscriber).where(Subscriber.email == email)
        )
        subscriber = result.scalar_one_or_none()
        if not subscriber:
            return render(
                request, "subscribe.html",
                step="1", email="", error="请先提交学号和邮箱",
                sources=await get_all_sources(),
            )

        code = f"{random.randint(0, 999999):06d}"
        subscriber.verification_code = code
        subscriber.verification_code_expires_at = datetime.now() + timedelta(minutes=5)
        await session.commit()

    ok = await send_verification_code(settings, email, code)
    if not ok:
        return render(
            request, "subscribe.html",
            step="verify", email=email, error="验证码发送失败，请稍后重试",
            sources=await get_all_sources(),
        )

    return RedirectResponse(
        url=f"/subscribe?step=verify&email={email}", status_code=303
    )


@router.post("/subscribe/verify")
async def subscribe_verify(
    request: Request,
    email: str = Form(...),
    code: str = Form(...),
):
    """步骤 2：验证验证码"""
    async with database.async_session() as session:
        result = await session.execute(
            select(Subscriber).where(Subscriber.email == email)
        )
        subscriber = result.scalar_one_or_none()
        if not subscriber:
            return render(
                request, "subscribe.html",
                step="1", email="", error="请先提交学号和邮箱",
                sources=await get_all_sources(),
            )

        now = datetime.now()
        if subscriber.verification_code != code:
            return render(
                request, "subscribe.html",
                step="verify", email=email, error="验证码错误",
                sources=await get_all_sources(),
            )
        if subscriber.verification_code_expires_at and now > subscriber.verification_code_expires_at:
            return render(
                request, "subscribe.html",
                step="verify", email=email, error="验证码已过期，请重新发送",
                sources=await get_all_sources(),
            )

        # 验证通过，确认学号未被其他人占用
        taken = await session.execute(
            select(Subscriber).where(
                Subscriber.student_id == subscriber.pending_student_id,
                Subscriber.id != subscriber.id,
                Subscriber.is_active == True,
            )
        )
        if taken.scalar_one_or_none():
            return render(
                request, "subscribe.html",
                step="verify", email=email, error="该学号已被其他邮箱绑定，请更换学号",
                sources=await get_all_sources(),
            )

        # 绑定学号
        subscriber.student_id = subscriber.pending_student_id
        subscriber.pending_student_id = None
        subscriber.is_verified = True
        subscriber.verification_code = None
        subscriber.verification_code_expires_at = None
        await session.commit()

    return RedirectResponse(
        url=f"/subscribe?step=sources&email={email}", status_code=303
    )


@router.post("/subscribe/sources")
async def subscribe_sources(
    request: Request,
    email: str = Form(...),
    source_ids: list[int] = Form(default=[]),
):
    """步骤 3：选择关注的数据源"""
    async with database.async_session() as session:
        result = await session.execute(
            select(Subscriber).where(Subscriber.email == email)
        )
        subscriber = result.scalar_one_or_none()
        if not subscriber or not subscriber.is_verified:
            return render(
                request, "subscribe.html",
                step="1", email="", error="请先完成邮箱验证",
                sources=await get_all_sources(),
            )

        # 清除旧订阅，写入新的
        existing_subs = (
            await session.execute(
                select(Subscribe).where(Subscribe.subscriber_id == subscriber.id)
            )
        ).scalars().all()
        for sub in existing_subs:
            await session.delete(sub)
        await session.flush()

        for sid in source_ids:
            session.add(Subscribe(subscriber_id=subscriber.id, source_id=sid))

        await session.commit()

    return RedirectResponse(url="/subscribe?success=1", status_code=303)


# ── 退订 ──────────────────────────────────────────────────

@router.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe_page(request: Request, token: str = Query(...)):
    async with database.async_session() as session:
        result = await session.execute(
            select(Subscriber).where(Subscriber.unsubscribe_token == token)
        )
        subscriber = result.scalar_one_or_none()
        if subscriber:
            subscriber.is_active = False
            await session.commit()
            return render(request, "unsubscribe.html", found=True)
    return render(request, "unsubscribe.html", found=False)


# ── 订阅管理 ──────────────────────────────────────────────

@router.get("/subscribe/manage", response_class=HTMLResponse)
async def manage_subscription_page(request: Request, token: str = Query(...)):
    async with database.async_session() as session:
        result = await session.execute(
            select(Subscriber).where(Subscriber.unsubscribe_token == token)
        )
        subscriber = result.scalar_one_or_none()
        if not subscriber or not subscriber.is_active:
            return render(request, "manage_subscription.html", subscriber=None, src="")

        # 获取所有数据源和已订阅的 ID
        sources = await get_all_sources()
        sub_result = await session.execute(
            select(Subscribe.source_id).where(Subscribe.subscriber_id == subscriber.id)
        )
        subscribed_ids = {row[0] for row in sub_result.all()}

    return render(
        request, "manage_subscription.html",
        subscriber=subscriber, sources=sources,
        subscribed_ids=subscribed_ids, token=token, done=False,
    )


@router.post("/subscribe/manage")
async def manage_subscription_action(
    request: Request,
    token: str = Form(...),
    source_ids: list[int] = Form(default=[]),
):
    async with database.async_session() as session:
        result = await session.execute(
            select(Subscriber).where(Subscriber.unsubscribe_token == token)
        )
        subscriber = result.scalar_one_or_none()
        if not subscriber:
            return render(request, "manage_subscription.html", subscriber=None)

        existing = (
            await session.execute(
                select(Subscribe).where(Subscribe.subscriber_id == subscriber.id)
            )
        ).scalars().all()
        for sub in existing:
            await session.delete(sub)

        for sid in source_ids:
            session.add(Subscribe(subscriber_id=subscriber.id, source_id=sid))

        await session.commit()

    return RedirectResponse(
        url=f"/subscribe/manage?token={token}&done=1", status_code=303
    )
