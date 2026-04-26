# AGENT.md

## Project Objective
This repository is a lightweight news subscription tool for Nanjing Tech University (NJTech) pages.
It crawls a target news page, formats the latest items into HTML, and sends update emails via QQ SMTP.
Execution target is Linux only.

## Repository Snapshot (2026-04-26)
- `njtech_news.sh`: main implementation (Python 3 script with `.sh` extension, ~310 lines).
- `web/index.html`: runtime HTML template for email content.
- `web/index.mjml`: MJML source template for email layout (authoritative design source).
- `requirements.txt`: Python dependencies (`requests`, `beautifulsoup4`).
- `.env.example`: template for environment variable configuration.
- `.gitignore`: ignores `__pycache__`, `last_email_content.html`, `.env`.
- `main.py`: empty placeholder (no functional role).
- `Dockerfile`: container image definition.
- `docker-compose.yml`: container orchestration with named volumes and env vars.
- `.dockerignore`: excludes secrets, cache, and metadata from build context.
- `README.md` / `README.en.md`: bilingual usage documentation.
- No tests, no CI configuration.

## Python Version
The script uses PEP 604 union syntax (`str | None`) and thus requires **Python 3.10+**.

## Core Runtime Flow
`main()` orchestrates the following sequence:

1. **Platform guard** — `ensure_linux_runtime()`: raises `RuntimeError` on non-Linux platforms.

2. **Config loading** — `load_dotenv_file(ENV_FILE, override=False)`: loads `.env` from repo root if present. Supports `export ` prefix and single/double-quoted values via `unquote_env_value()`. Existing OS environment variables take priority.
   - `load_config_from_env()`: reads env vars into a `MailConfig` dataclass. Validates that required fields (`NEWS_SENDER_EMAIL`, `NEWS_SMTP_PASSWORD`, `NEWS_RECEIVERS`) are non-empty. Parses `NEWS_SMTP_PORT` as int.

3. **Template validation** — `ensure_template_files()`: verifies both `web/index.html` and `web/index.mjml` exist, are non-empty, and contain all three required placeholders (`{{NEWS_TITLE}}`, `{{NEWS_ROWS}}`, `{{SOURCE_URL}}`). Fails fast if any check fails.

4. **Page fetch** — `fetch_html(url)`: GET request with 30s timeout, SSL verification enabled. Sets encoding from `apparent_encoding`.

5. **Content parsing** — `parse_content(page_html, source_url)`:
   - Parses with BeautifulSoup (`html.parser`).
   - Finds list container `ul.my-list`, iterates `li` children.
   - Extracts title + href from `<a>`, date from `<span class="date">`.
   - Resolves relative URLs via `urllib.parse.urljoin`.
   - Builds table rows as HTML strings.
   - Delegates final rendering to `render_email_content(rows, source_url)`.

6. **Email rendering** — `render_email_content(news_rows, source_url)`: loads the HTML template and replaces `{{NEWS_TITLE}}`, `{{NEWS_ROWS}}`, `{{SOURCE_URL}}` with escaped values.

7. **Email sending** — `send_email(content, config)`:
   - Compares against `last_email_content.html` cache; skips send if identical (dedup).
   - Builds `MIMEMultipart` HTML email with UTF-8 encoding.
   - Sends via `smtplib.SMTP_SSL` through QQ SMTP (`smtp.qq.com:465` by default).
   - On success, updates the cache file.

## Dependencies
- Python 3.10+
- `requests>=2.31.0`
- `beautifulsoup4>=4.12.0`

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

## Docker Deployment

### Build
```bash
docker build -t njtech-news .
```

### Run (one-shot)
```bash
docker run --rm \
  -e NEWS_SENDER_EMAIL=your_email@qq.com \
  -e NEWS_SMTP_PASSWORD=your_auth_code \
  -e NEWS_RECEIVERS=user@qq.com \
  -v njtech-cache:/data \
  njtech-news
```

### Run with docker-compose
Create a `.env` file in the project root (use `.env.example` as template), then:
```bash
docker compose run --rm njtech-news
```

### Periodic execution (host cron)
```
*/30 * * * * docker run --rm -v njtech-cache:/data --env-file /path/to/.env njtech-news
```
Or with docker compose (from the project directory):
```
*/30 * * * * cd /path/to/njtech_news && docker compose run --rm njtech-news
```

### Volume mount reference
| Mount point | Purpose | Required |
|---|---|---|
| `/data` | Cache persistence (`last_email_content.html`) | Recommended |
| `/app/web/index.html` | Override runtime HTML template | Optional |
| `/app/web/index.mjml` | Override MJML source template | Optional |
| `/app/.env` | Load `.env` file as alternative to `-e` flags | Optional |

### Docker-specific env var
- `NEWS_CACHE_DIR` (default `/data` in container): directory where `last_email_content.html` is written. Change this if you mount the cache volume at a different path.

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
- Supports `export KEY=VALUE` syntax and quoted values (`"val"` or `'val'`).
- Existing process environment variables override `.env` values.

## Agent Guidelines For This Repo
- Keep `njtech_news.sh` executable under Python 3.10+.
- Keep the script Linux-only unless explicitly requested otherwise.
- Template changes: `web/index.mjml` is the design source; `web/index.html` is the runtime template. Always update both and keep them in sync.
- `ensure_template_files()` validates both template files — if you modify template structure, update the validation logic to match.
- Do not break existing parsing assumptions unless site HTML changed:
  - list selector: `ul.my-list`
  - date selector: `span.date`
- Preserve dedup behavior based on `last_email_content.html` cache.
- Avoid committing secrets directly into source code.
- If adding new local config/cache files, add them to `.gitignore`.
- If changing parsing logic, add clear failure logs for selector misses.

## Recommended Near-Term Improvements
1. Add request headers (User-Agent), retry/backoff, and configurable timeout.
2. Add unit tests for `parse_content` using saved sample HTML fixtures.
3. Rename script to `njtech_news.py` (or add a thin shell wrapper) to avoid extension confusion.
4. Move config loading into a dedicated module if the project grows beyond the single-script scope.

## Change Validation Checklist
- `python -m py_compile njtech_news.sh` passes.
- `docker build -t njtech-news .` succeeds.
- `docker run --rm njtech-news` with no env vars fails with clear missing-config error.
- Crawl and parse return non-empty HTML on current target page.
- No plaintext credentials are committed.
- Duplicate-content suppression still works as expected (run twice with same cache volume — second run skips).
- Both template files (`web/index.html`, `web/index.mjml`) contain `{{NEWS_TITLE}}`, `{{NEWS_ROWS}}`, `{{SOURCE_URL}}`.