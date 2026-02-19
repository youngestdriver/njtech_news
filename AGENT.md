# AGENT.md

## Project Objective
This repository is a lightweight news subscription tool for Nanjing Tech University (NJTech) pages.
It crawls a target news page, formats the latest items into HTML, and sends update emails via QQ SMTP.
Execution target is Linux only.

## Repository Snapshot (2026-02-18)
- `njtech_news.sh`: main implementation (Python script with `.sh` extension).
- `README.md`: usage description and screenshots.
- `main.py`: empty placeholder file.
- `web/index.mjml`: empty placeholder file.
- `web/index.html`: empty placeholder file.

Current repo has `requirements.txt`, but still no tests and no CI configuration.

## Core Runtime Flow
1. `fetch_html(url)`
   - Uses `requests.get` with SSL verification enabled.
   - Sets response encoding from `apparent_encoding`.
2. `parse_content(html, url)`
   - Parses target page using BeautifulSoup.
   - Expects list container `ul.my-list`.
   - Reads each `li` item with link `<a>` and date `<span class="date">`.
   - Builds responsive HTML table email content.
3. `send_email(content, config)`
   - Builds MIME multipart HTML email.
   - Sends through SMTP SSL (`smtp.qq.com:465` by default).
   - Uses `last_email_content.html` in repo root as dedup cache (skip send when unchanged).
4. `main()`
   - Uses default source URL: `https://jwc.njtech.edu.cn/index/ggtz.htm`.
   - Fails fast on non-Linux platforms.
   - Auto-loads `.env` (if present), then loads runtime config from environment variables.

## Dependencies
- Python 3.8+ recommended
- `requests`
- `beautifulsoup4`

Install:
```bash
pip install -r requirements.txt
```

## Run Commands
```bash
python3 njtech_news.sh
```

Linux executable mode (optional):
```bash
chmod +x ./njtech_news.sh
./njtech_news.sh
```

Syntax check:
```bash
python -m py_compile njtech_news.sh
```

## Configuration Requirements
Required environment variables:
- `NEWS_SENDER_EMAIL`: QQ mailbox address.
- `NEWS_SMTP_PASSWORD`: QQ SMTP authorization code (not mailbox login password).
- `NEWS_RECEIVERS`: recipient list separated by commas.

Optional environment variables:
- `NEWS_SOURCE_URL` (default `https://jwc.njtech.edu.cn/index/ggtz.htm`)
- `NEWS_SENDER_NAME` (default `NJTech News Bot`)
- `NEWS_MAIL_SUBJECT` (default `NJTech News Update`)
- `NEWS_SMTP_HOST` (default `smtp.qq.com`)
- `NEWS_SMTP_PORT` (default `465`)

Configuration file support:
- `.env` in repo root is auto-loaded at startup.
- Existing process environment variables override `.env` values.

## Agent Guidelines For This Repo
- Keep `njtech_news.sh` executable under Python 3.
- Keep the script Linux-only unless explicitly requested otherwise.
- Do not break existing parsing assumptions unless site HTML changed:
  - list selector: `ul.my-list`
  - date selector: `span.date`
- Preserve dedup behavior based on `last_email_content.html`.
- Avoid committing secrets directly into source code.
- Prefer adding a `.gitignore` if introducing local config/cache files.
- If you change parsing logic, add clear failure logs for selector misses.

## Recommended Near-Term Improvements
1. Add request headers, retry/backoff, and timeout handling strategy.
2. Add unit tests for `parse_content` using saved sample HTML.
3. Rename script to `njtech_news.py` (or add a thin shell wrapper) to avoid extension confusion.
4. Move config loading into a dedicated module if the project grows.

## Change Validation Checklist
- `python -m py_compile njtech_news.sh` passes.
- Crawl and parse return non-empty HTML on current target page.
- No plaintext credentials are committed.
- Duplicate-content suppression still works as expected.
