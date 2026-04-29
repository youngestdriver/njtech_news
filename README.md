# NJTech News

<p align="center">
  <img src="static/logo.png" width="256" alt="NJTech News">
</p>

南京工业大学各学院/部门公告聚合服务。支持 Web 浏览、邮件订阅。

[![Docker Pulls](https://img.shields.io/docker/pulls/papercranewillfly/njtech-news)](https://hub.docker.com/r/papercranewillfly/njtech-news)
[![Build](https://github.com/youngestdriver/njtech_news/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/youngestdriver/njtech_news/actions)

## 功能

- **公告聚合** — 从各学院/部门网站抓取公告，统一展示
- **邮件订阅** — 绑定学号+邮箱，验证码确认，可选择关注的数据源
- **定时推送** — 按可配置的间隔自动爬取并推送新公告到订阅邮箱
- **订阅管理** — 在邮件底部链接修改关注范围或退订

## 快速开始

### Docker 部署

```bash
git clone https://github.com/youngestdriver/njtech_news.git
cd njtech_news
cp .env.example .env
# 编辑 .env，填入 NEWS_SENDER_EMAIL 和 NEWS_SMTP_PASSWORD
docker compose up -d
```

如需使用预构建镜像（无需本地编译），将 `docker-compose.yml` 中的 `build: .` 替换为 `image: papercranewillfly/njtech-news:latest`

```yaml
services:
  njtech-news:
    image: papercranewillfly/njtech-news:latest
    ports:
      - 8000:8000
    volumes:
      - ./data:/data
    env_file:
      - .env
    restart: unless-stopped
```

支持 `linux/amd64` 和 `linux/arm64` 架构。

### 从源码部署

```bash
git clone https://github.com/youngestdriver/njtech_news.git
cd njtech_news
pip install -r requirements.txt
cp .env.example .env
# 填入必要的环境变量
uvicorn app.main:app --reload
```

访问 http://localhost:8000

## 配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `NEWS_SENDER_EMAIL` | SMTP 发件邮箱（必填） | — |
| `NEWS_SMTP_PASSWORD` | SMTP 密码/授权码（必填） | — |
| `NEWS_SMTP_HOST` | SMTP 服务器 | `smtp.qq.com` |
| `NEWS_SMTP_PORT` | SMTP 端口 | `465` |
| `NEWS_SENDER_NAME` | 发件人名称 | `NJTech News` |
| `NEWS_MAIL_SUBJECT` | 邮件主题 | `今日公告汇总` |
| `NEWS_CRAWL_INTERVAL` | 爬取间隔（秒） | `300` |
| `NEWS_BASE_URL` | 应用公网地址 | `http://localhost:8000` |

数据源配置在 `sources.yaml` 中管理。

## 项目结构

```
├── app/
│   ├── main.py          # FastAPI 入口
│   ├── config.py        # 环境变量配置
│   ├── database.py      # 数据库连接
│   ├── models.py        # ORM 模型
│   ├── routers/
│   │   └── pages.py     # Web 页面路由
│   └── services/
│       ├── scraper.py   # 爬虫引擎
│       ├── scheduler.py # 定时调度
│       └── mailer.py    # 邮件发送
├── templates/           # Jinja2 模板
├── static/              # 静态资源
├── sources.yaml         # 数据源配置
├── docker-compose.yml
└── Dockerfile
```
