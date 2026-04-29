import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="学院")
    selector_container: Mapped[str] = mapped_column(String(500), nullable=False)
    selector_title: Mapped[str] = mapped_column(String(500), nullable=False)
    selector_link: Mapped[str] = mapped_column(String(500), nullable=False)
    selector_date: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    articles: Mapped[list["Article"]] = relationship(back_populates="source")
    subscribers: Mapped[list["Subscribe"]] = relationship(back_populates="source")


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    publish_date: Mapped[str | None] = mapped_column(String(50))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    source: Mapped["Source | None"] = relationship(back_populates="articles")


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    unsubscribe_token: Mapped[str] = mapped_column(
        String(64), default=lambda: uuid.uuid4().hex
    )
    pending_student_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    verification_code: Mapped[str | None] = mapped_column(String(6), nullable=True)
    verification_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    subscriptions: Mapped[list["Subscribe"]] = relationship(back_populates="subscriber")


class Subscribe(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("subscriber_id", "source_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    subscriber: Mapped["Subscriber"] = relationship(back_populates="subscriptions")
    source: Mapped["Source"] = relationship(back_populates="subscribers")


class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"))
    article_id: Mapped[int | None] = mapped_column(ForeignKey("articles.id"), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(String(20), default="success")  # success / fail
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
