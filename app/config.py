from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="news_",
    )

    # SMTP
    sender_email: str = ""
    smtp_password: str = ""
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 465
    sender_name: str = "NJTech News"
    mail_subject: str = "今日公告汇总"
    receivers: str = ""

    # Crawler
    source_url: str = ""
    crawl_interval: int = 300

    # Database
    database_url: str = "sqlite+aiosqlite:////data/njtech.db"

    # Deletion detection
    deletion_lookback_days: int = 7

    # App
    base_url: str = "http://localhost:8000"
