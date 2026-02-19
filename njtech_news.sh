#!/usr/bin/env python3

import html
import os
import smtplib
import ssl
import sys
import urllib.parse
from dataclasses import dataclass
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DEFAULT_SOURCE_URL = "https://jwc.njtech.edu.cn/index/ggtz.htm"
DEFAULT_SMTP_HOST = "smtp.qq.com"
DEFAULT_SMTP_PORT = 465
DEFAULT_SENDER_NAME = "NJTech News Bot"
DEFAULT_SUBJECT = "NJTech News Update"
DEFAULT_NEWS_TITLE = "NJTech Academic Affairs News"
CACHE_FILE = Path("last_email_content.html")
ENV_FILE = Path(".env")
WEB_DIR = Path(__file__).resolve().parent / "web"
HTML_TEMPLATE_FILE = WEB_DIR / "index.html"
MJML_TEMPLATE_FILE = WEB_DIR / "index.mjml"


@dataclass
class MailConfig:
    source_url: str
    sender_email: str
    smtp_password: str
    receivers: list[str]
    sender_name: str
    subject: str
    smtp_host: str
    smtp_port: int


def ensure_linux_runtime() -> None:
    if not sys.platform.startswith("linux"):
        raise RuntimeError(
            f"This script is Linux-only. Current platform: '{sys.platform}'."
        )


def unquote_env_value(raw_value: str) -> str:
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_dotenv_file(file_path: Path, override: bool = False) -> None:
    if not file_path.exists():
        return

    for raw_line in file_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = unquote_env_value(value)

        if override or key not in os.environ:
            os.environ[key] = value


def ensure_template_files() -> bool:
    required_files = [HTML_TEMPLATE_FILE, MJML_TEMPLATE_FILE]
    missing_files = [str(path) for path in required_files if not path.exists()]
    if missing_files:
        print(f"Missing template files: {', '.join(missing_files)}")
        return False

    template_content: dict[Path, str] = {}
    empty_files: list[str] = []
    for file_path in required_files:
        try:
            content = file_path.read_text(encoding="utf-8-sig")
            template_content[file_path] = content
            if not content.strip():
                empty_files.append(str(file_path))
        except OSError as exc:
            print(f"Failed to read template file '{file_path}': {exc}")
            return False

    if empty_files:
        print(f"Template files are empty: {', '.join(empty_files)}")
        return False

    required_tokens = ["{{NEWS_TITLE}}", "{{NEWS_ROWS}}", "{{SOURCE_URL}}"]
    for file_path in required_files:
        missing_tokens = [
            token for token in required_tokens if token not in template_content[file_path]
        ]
        if missing_tokens:
            print(
                f"Template placeholders missing in '{file_path}': "
                f"{', '.join(missing_tokens)}"
            )
            return False

    return True


def load_html_template() -> str | None:
    try:
        template = HTML_TEMPLATE_FILE.read_text(encoding="utf-8-sig")
    except OSError as exc:
        print(f"Failed to read HTML template '{HTML_TEMPLATE_FILE}': {exc}")
        return None

    required_tokens = ["{{NEWS_TITLE}}", "{{NEWS_ROWS}}", "{{SOURCE_URL}}"]
    missing_tokens = [token for token in required_tokens if token not in template]
    if missing_tokens:
        print(
            f"HTML template missing placeholders: {', '.join(missing_tokens)} "
            f"(file: {HTML_TEMPLATE_FILE})"
        )
        return None

    return template


def render_email_content(news_rows: list[str], source_url: str) -> str | None:
    template = load_html_template()
    if template is None:
        return None

    replacements = {
        "{{NEWS_TITLE}}": html.escape(DEFAULT_NEWS_TITLE),
        "{{NEWS_ROWS}}": "".join(news_rows),
        "{{SOURCE_URL}}": html.escape(source_url, quote=True),
    }
    for token, value in replacements.items():
        template = template.replace(token, value)

    return template


def split_receivers(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def load_config_from_env() -> MailConfig:
    source_url = os.getenv("NEWS_SOURCE_URL", DEFAULT_SOURCE_URL).strip()
    sender_email = os.getenv("NEWS_SENDER_EMAIL", "").strip()
    smtp_password = os.getenv("NEWS_SMTP_PASSWORD", "").strip()
    receivers = split_receivers(os.getenv("NEWS_RECEIVERS", ""))

    sender_name = os.getenv("NEWS_SENDER_NAME", DEFAULT_SENDER_NAME).strip() or DEFAULT_SENDER_NAME
    subject = os.getenv("NEWS_MAIL_SUBJECT", DEFAULT_SUBJECT).strip() or DEFAULT_SUBJECT
    smtp_host = os.getenv("NEWS_SMTP_HOST", DEFAULT_SMTP_HOST).strip() or DEFAULT_SMTP_HOST

    smtp_port_raw = os.getenv("NEWS_SMTP_PORT", str(DEFAULT_SMTP_PORT)).strip()
    try:
        smtp_port = int(smtp_port_raw)
        if smtp_port <= 0:
            raise ValueError
    except ValueError as exc:
        raise ValueError(f"NEWS_SMTP_PORT must be a positive integer, got '{smtp_port_raw}'.") from exc

    missing = []
    if not sender_email:
        missing.append("NEWS_SENDER_EMAIL")
    if not smtp_password:
        missing.append("NEWS_SMTP_PASSWORD")
    if not receivers:
        missing.append("NEWS_RECEIVERS")
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return MailConfig(
        source_url=source_url,
        sender_email=sender_email,
        smtp_password=smtp_password,
        receivers=receivers,
        sender_name=sender_name,
        subject=subject,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
    )


def fetch_html(url: str) -> str | None:
    try:
        response = requests.get(url, timeout=30, verify=True)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        return response.text
    except requests.RequestException as exc:
        print(f"Failed to fetch source page: {exc}")
        return None


def parse_content(page_html: str, source_url: str) -> str | None:
    soup = BeautifulSoup(page_html, "html.parser")
    news_list = soup.find("ul", class_="my-list")
    if news_list is None:
        print("News list container not found: ul.my-list")
        return None

    news_items = news_list.find_all("li")
    if not news_items:
        print("No news items found under ul.my-list.")
        return None

    rows: list[str] = []
    for item in news_items:
        link = item.find("a")
        date = item.find("span", class_="date")
        if link is None or date is None:
            continue

        title = link.get_text(strip=True)
        href = (link.get("href") or "").strip()
        news_date = date.get_text(strip=True)
        if not title or not href:
            continue

        full_url = urllib.parse.urljoin(source_url, href)
        safe_title = html.escape(title)
        safe_date = html.escape(news_date)
        safe_url = html.escape(full_url, quote=True)
        rows.append(f'<tr><td><a href="{safe_url}">{safe_title}</a></td><td>{safe_date}</td></tr>')

    if not rows:
        print("No valid news rows were parsed.")
        return None

    return render_email_content(rows, source_url)


def load_last_content(cache_path: Path) -> str:
    if not cache_path.exists():
        return ""
    return cache_path.read_text(encoding="utf-8")


def save_last_content(cache_path: Path, content: str) -> None:
    cache_path.write_text(content, encoding="utf-8")


def send_email(content: str, config: MailConfig) -> bool:
    last_content = load_last_content(CACHE_FILE)
    if content == last_content:
        print("No content change detected. Skip sending email.")
        return True

    message = MIMEMultipart()
    message["From"] = f"{str(Header(config.sender_name, 'utf-8'))} <{config.sender_email}>"
    message["To"] = ", ".join(config.receivers)
    message["Subject"] = str(Header(config.subject, "utf-8"))
    message.attach(MIMEText(content, "html", "utf-8"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, context=context) as smtp_obj:
            smtp_obj.login(config.sender_email, config.smtp_password)
            smtp_obj.sendmail(config.sender_email, config.receivers, message.as_string())
        save_last_content(CACHE_FILE, content)
        print("Email sent successfully.")
        return True
    except smtplib.SMTPException as exc:
        print(f"Failed to send email: {exc}")
        return False


def main() -> int:
    try:
        ensure_linux_runtime()
        load_dotenv_file(ENV_FILE, override=False)
        config = load_config_from_env()
    except (RuntimeError, ValueError) as exc:
        print(exc)
        return 1

    if not ensure_template_files():
        return 1

    page_html = fetch_html(config.source_url)
    if page_html is None:
        return 1

    content = parse_content(page_html, config.source_url)
    if content is None:
        return 1

    return 0 if send_email(content, config) else 1


if __name__ == "__main__":
    sys.exit(main())
