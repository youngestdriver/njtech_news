from datetime import datetime


class SourceOut:
    id: int
    name: str
    url: str
    category: str
    is_active: bool

    class Config:
        from_attributes = True


class ArticleOut:
    id: int
    title: str
    url: str
    source_name: str | None
    publish_date: str | None
    created_at: datetime

    class Config:
        from_attributes = True
