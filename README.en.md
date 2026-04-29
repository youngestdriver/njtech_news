# NJTech News

Announcement aggregation service for Nanjing Tech University (NJTech). Aggregates notices from college/department websites with web browsing and email subscription.

## Features

- **Announcement Aggregation** — Scrapes notices from multiple department websites into one place
- **Email Subscription** — Student ID + email binding with verification code, selectable sources
- **Scheduled Push** — Configurable interval for crawling and email delivery
- **Subscription Management** — Token-based link to modify sources or unsubscribe

## Quick Start

### Docker

```bash
git clone https://github.com/youngestdriver/njtech_news.git
cd njtech_news

cp .env.example .env
# Fill in NEWS_SENDER_EMAIL and NEWS_SMTP_PASSWORD

docker compose up -d
```

Visit http://localhost:8000

### Manual

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in required environment variables
uvicorn app.main:app --reload
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `NEWS_SENDER_EMAIL` | SMTP sender email (required) | — |
| `NEWS_SMTP_PASSWORD` | SMTP password/app password (required) | — |
| `NEWS_SMTP_HOST` | SMTP server | `smtp.qq.com` |
| `NEWS_SMTP_PORT` | SMTP port | `465` |
| `NEWS_SENDER_NAME` | Sender name | `NJTech News` |
| `NEWS_MAIL_SUBJECT` | Email subject | `今日公告汇总` |
| `NEWS_CRAWL_INTERVAL` | Crawl interval (seconds) | `300` |
| `NEWS_BASE_URL` | Public URL of the app | `http://localhost:8000` |

Sources are managed in `sources.yaml`.

## Project Structure

```
├── app/
│   ├── main.py          # FastAPI entry point
│   ├── config.py        # Environment config
│   ├── database.py      # Database connection
│   ├── models.py        # ORM models
│   ├── routers/
│   │   └── pages.py     # Web page routes
│   └── services/
│       ├── scraper.py   # Scraping engine
│       ├── scheduler.py # Task scheduler
│       └── mailer.py    # Email delivery
├── templates/           # Jinja2 templates
├── sources.yaml         # Source definitions
├── docker-compose.yml
└── Dockerfile
```
