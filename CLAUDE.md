# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Syntax check (no runtime)
python -m py_compile njtech_news.sh

# Run (requires .env or env vars set)
python3 njtech_news.sh

# Docker
docker build -t njtech-news .
docker compose run --rm njtech-news
```

Python 3.10+ required (uses `str | None` union syntax).

## Project Structure

Single-file Python script (`njtech_news.sh`, not a shell script — `.sh` extension only for historical reasons) that crawls a target news page and sends HTML email updates via QQ SMTP. `main.py` is an empty placeholder with no functional role.

### Core Flow (`main()`)
1. **Platform guard** — `ensure_linux_runtime()` blocks non-Linux platforms
2. **Config** — loads `.env` via `load_dotenv_file()`, reads env vars into `MailConfig` dataclass
3. **Template validation** — `ensure_template_files()` checks `web/index.html` and `web/index.mjml` exist, are non-empty, and contain `{{NEWS_TITLE}}`, `{{NEWS_ROWS}}`, `{{SOURCE_URL}}`
4. **Page fetch** — `fetch_html()` GETs the source URL with 30s timeout
5. **Parsing** — `parse_content()` uses BeautifulSoup to extract `<a>` titles/hrefs and `span.date` from `ul.my-list` container, builds HTML table rows
6. **Email sending** — `send_email()` compares against `last_email_content.html` cache (dedup), builds MIME message, sends via `smtplib.SMTP_SSL`, updates cache on success

### Key Files
- `njtech_news.sh` — sole implementation (~310 lines), all logic in one file
- `web/index.html` — runtime HTML email template (must have `{{NEWS_TITLE}}`, `{{NEWS_ROWS}}`, `{{SOURCE_URL}}`)
- `web/index.mjml` — MJML source template (design authority; keep in sync with `index.html`)
- `last_email_content.html` — auto-generated cache file for dedup (gitignored)
- `Dockerfile` — `python:3.10-slim` based, sets `NEWS_CACHE_DIR=/data`
- `.env` — local config (gitignored), auto-loaded at startup if present

### Template Rules
- `web/index.mjml` is the design source; `web/index.html` is the runtime template. Always update both and keep them in sync.
- Both templates must contain the three placeholders or the script errors out.

## Configuration

Required env vars: `NEWS_SENDER_EMAIL`, `NEWS_SMTP_PASSWORD`, `NEWS_RECEIVERS` (comma-separated).

Optional: `NEWS_SOURCE_URL`, `NEWS_SENDER_NAME`, `NEWS_MAIL_SUBJECT`, `NEWS_SMTP_HOST`, `NEWS_SMTP_PORT`, `NEWS_CACHE_DIR`.

`.env` supports `export KEY=VALUE` syntax and quoted values. Existing OS env vars take priority.

## Key Constraints
- Linux-only runtime (`sys.platform.startswith("linux")`)
- Parser selectors: `ul.my-list` for news container, `span.date` for dates
- Dedup is content-based on the full rendered HTML (cache file comparison)
- No tests, no CI — validate manually or via Docker build
