# njtech_news

[中文](README.md) | English

Linux-only crawler + email notifier for NJTech news pages.

## What It Does
- Crawls a target page (default: NJTech Academic Affairs announcements).
- Parses list items from `ul.my-list` with date in `span.date`.
- Builds an HTML email table.
- Sends updates via QQ SMTP (`smtp.qq.com:465`).
- Skips duplicate sends when content is unchanged (`last_email_content.html` cache).

## Requirements
- Linux environment
- Python 3.10+
- QQ mailbox SMTP authorization code
- Python packages:
  - `requests`
  - `beautifulsoup4`

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Compatibility alias (also works):

```bash
python3 -m pip install -r requirement.txt
```

## Configuration (Environment Variables)
Required:
- `NEWS_SENDER_EMAIL`: sender mailbox (for example: `xxx@qq.com`)
- `NEWS_SMTP_PASSWORD`: SMTP auth code (not mailbox login password)
- `NEWS_RECEIVERS`: comma-separated recipient list

Optional:
- `NEWS_SOURCE_URL` (default: `https://jwc.njtech.edu.cn/index/ggtz.htm`)
- `NEWS_SENDER_NAME` (default: `NJTech News Bot`)
- `NEWS_MAIL_SUBJECT` (default: `NJTech News Update`)
- `NEWS_SMTP_HOST` (default: `smtp.qq.com`)
- `NEWS_SMTP_PORT` (default: `465`)

Template file:
- Copy `.env.example` to `.env`, then fill your real values.
- Script auto-loads `.env` if present.
- Existing OS environment variables take priority over `.env` values.

## Run
Recommended:

```bash
cp .env.example .env
# edit .env with your real values
python3 ./njtech_news.sh
```

Optional executable mode:

```bash
chmod +x ./njtech_news.sh
./njtech_news.sh
```

Environment-only mode (without `.env`) is supported:
- export `NEWS_SENDER_EMAIL`
- export `NEWS_SMTP_PASSWORD`
- export `NEWS_RECEIVERS`
- run script

## Scheduled Execution (cron)
Example: run every 30 minutes.

```bash
*/30 * * * * /usr/bin/python3 /path/to/njtech_news.sh >> /path/to/njtech_news.log 2>&1
```

Make sure the cron environment can access required variables (or use `.env` in script directory).

## Customizing Other College Pages
If you switch to another source page, check:
- whether list selector `ul.my-list` still exists
- whether date selector `span.date` still exists
- whether link structure needs adjusted parsing rules
