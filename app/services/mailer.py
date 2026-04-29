from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP_SSL

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select

from app import database
from app.config import Settings
from app.models import Article, EmailLog, Source, Subscribe, Subscriber


env = Environment(loader=FileSystemLoader("templates"))


def render_mail_template(
    subscriber_name: str,
    articles: list[dict],
    manage_url: str,
    unsubscribe_url: str,
    base_url: str,
) -> str:
    template = env.get_template("email.html")
    return template.render(
        subscriber_name=subscriber_name,
        articles=articles,
        manage_url=manage_url,
        unsubscribe_url=unsubscribe_url,
        base_url=base_url,
    )


async def send_verification_code(
    settings: Settings, email: str, code: str
) -> bool:
    """发送邮箱验证码"""
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:20px;background:#f3f4f6;font-family:sans-serif;">
  <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:8px;padding:32px;">
    <h2 style="color:#4f46e5;font-size:18px;margin:0 0 16px;">NJTech News — 邮箱验证</h2>
    <p style="color:#6b7280;font-size:14px;">您的验证码为：</p>
    <p style="font-size:36px;font-weight:bold;color:#4f46e5;letter-spacing:8px;text-align:center;margin:12px 0;">{code}</p>
    <p style="color:#9ca3af;font-size:12px;">验证码 5 分钟内有效，请勿转发他人。</p>
  </div>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "NJTech News — 邮箱验证码"
    msg["From"] = f"{settings.sender_name} <{settings.sender_email}>"
    msg["To"] = email
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            smtp.login(settings.sender_email, settings.smtp_password)
            smtp.sendmail(settings.sender_email, [email], msg.as_string())
        return True
    except Exception:
        return False


async def send_digest_to_subscriber(
    settings: Settings, subscriber_id: int, article_ids: list[int]
) -> bool:
    """给单个订阅者发送摘要邮件"""
    async with database.async_session() as session:
        subscriber_result = await session.execute(
            select(Subscriber.email, Subscriber.unsubscribe_token).where(
                Subscriber.id == subscriber_id
            )
        )
        sub = subscriber_result.first()
        if not sub:
            return False

        email, token = sub[0], sub[1]

        # 获取文章详情
        if article_ids:
            articles_result = await session.execute(
                select(Article, Source.name).join(Source).where(
                    Article.id.in_(article_ids)
                ).order_by(Article.created_at.desc())
            )
            articles_data = []
            for a, src_name in articles_result:
                articles_data.append({
                    "title": a.title,
                    "url": a.url,
                    "source_name": src_name,
                    "publish_date": a.publish_date or "",
                })
        else:
            articles_data = []

        unsubscribe_url = f"{settings.base_url}/unsubscribe?token={token}"
        manage_url = f"{settings.base_url}/subscribe/manage?token={token}"
        html = render_mail_template(email, articles_data, manage_url, unsubscribe_url, settings.base_url)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = settings.mail_subject
        msg["From"] = f"{settings.sender_name} <{settings.sender_email}>"
        msg["To"] = email
        msg.attach(MIMEText(html, "html", "utf-8"))

        try:
            with SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
                smtp.login(settings.sender_email, settings.smtp_password)
                smtp.sendmail(settings.sender_email, [email], msg.as_string())

            for aid in article_ids:
                session.add(EmailLog(subscriber_id=subscriber_id, article_id=aid, status="success"))
            await session.commit()
            return True
        except Exception:
            session.add(
                EmailLog(subscriber_id=subscriber_id, article_id=None, status="fail")
            )
            await session.commit()
            return False


async def send_all_digests(settings: Settings) -> int:
    """给所有符合条件的订阅者发送摘要，返回成功数"""
    async with database.async_session() as session:
        subs_result = await session.execute(
            select(Subscriber.id, Subscriber.email).where(Subscriber.is_active == True)
        )
        subscribers = subs_result.all()

    success = 0
    for sid, _email in subscribers:
        # 获取该订阅者关注的源
        async with database.async_session() as session:
            sub_sources = await session.execute(
                select(Subscribe.source_id).where(Subscribe.subscriber_id == sid)
            )
            source_ids = [row[0] for row in sub_sources.all()]

        if not source_ids:
            continue

        # 获取这些源的最新文章（24小时内）
        async with database.async_session() as session:
            articles_result = await session.execute(
                select(Article.id)
                .where(Article.source_id.in_(source_ids))
                .order_by(Article.created_at.desc())
                .limit(10)
            )
            article_ids = [row[0] for row in articles_result.all()]

        if await send_digest_to_subscriber(settings, sid, article_ids):
            success += 1

    return success
