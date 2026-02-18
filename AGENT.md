# AGENT.md

## Project Objective
This repository is a lightweight news subscription tool for Nanjing Tech University (NJTech) pages.
It crawls a target news page, formats the latest items into HTML, and sends update emails via QQ SMTP.

## Repository Snapshot (2026-02-18)
- `njtech_news.sh`: main implementation (Python script with `.sh` extension).
- `README.md`: usage description and screenshots.
- `main.py`: empty placeholder file.
- `web/index.mjml`: empty placeholder file.
- `web/index.html`: empty placeholder file.

Current repo has no dependency lock file, no tests, and no CI configuration.

## Core Runtime Flow
1. `fetch_html(url)`
   - Uses `requests.get` with SSL verification enabled.
   - Sets response encoding from `apparent_encoding`.
2. `parse_content(html, url)`
   - Parses target page using BeautifulSoup.
   - Expects list container `ul.my-list`.
   - Reads each `li` item with link `<a>` and date `<span class="date">`.
   - Builds responsive HTML table email content.
3. `send_email(content, sender, password, receivers)`
   - Builds MIME multipart HTML email.
   - Sends through `smtp.qq.com:465` using SSL.
   - Uses `last_email_content.html` in repo root as dedup cache (skip send when unchanged).
4. `main()`
   - Uses default source URL: `https://jwc.njtech.edu.cn/index/ggtz.htm`.
   - Reads sender/password/receivers from hardcoded variables.

## Dependencies
- Python 3.8+ recommended
- `requests`
- `beautifulsoup4`

Install:
```bash
pip install requests beautifulsoup4
```

## Run Commands
```bash
python njtech_news.sh
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
Before running, update these values in `njtech_news.sh`:
- `sender`: QQ mailbox address.
- `password`: QQ SMTP authorization code (not mailbox login password).
- `receivers`: recipient email list.

## Agent Guidelines For This Repo
- Keep `njtech_news.sh` executable under Python 3.
- Do not break existing parsing assumptions unless site HTML changed:
  - list selector: `ul.my-list`
  - date selector: `span.date`
- Preserve dedup behavior based on `last_email_content.html`.
- Avoid committing secrets directly into source code.
- Prefer adding a `.gitignore` if introducing local config/cache files.
- If you change parsing logic, add clear failure logs for selector misses.

## Recommended Near-Term Improvements
1. Move email credentials to environment variables or local config (gitignored).
2. Add request headers, retry/backoff, and timeout handling strategy.
3. Add unit tests for `parse_content` using saved sample HTML.
4. Rename script to `njtech_news.py` (or add a thin shell wrapper) to avoid extension confusion.
5. Add minimal dependency file (`requirements.txt`) and quickstart command in README.

## Change Validation Checklist
- `python -m py_compile njtech_news.sh` passes.
- Crawl and parse return non-empty HTML on current target page.
- No plaintext credentials are committed.
- Duplicate-content suppression still works as expected.
