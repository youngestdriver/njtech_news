# njtech_news

中文 | [English](README.en.md)

仅适用于 Linux 的 NJTech 新闻爬取与邮件通知脚本。

## 功能说明
- 抓取目标页面（默认：南京工业大学教务处通知页）。
- 从 `ul.my-list` 中解析新闻条目，并读取 `span.date` 日期。
- 生成 HTML 表格邮件内容。
- 通过 QQ SMTP（`smtp.qq.com:465`）发送邮件。
- 若内容无变化，则跳过发送（缓存文件：`last_email_content.html`）。

## 环境要求
- Linux 环境
- Python 3.10+
- QQ 邮箱 SMTP 授权码
- Python 依赖：
  - `requests`
  - `beautifulsoup4`

安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

## 配置（环境变量）
必填：
- `NEWS_SENDER_EMAIL`：发件邮箱（例如：`xxx@qq.com`）
- `NEWS_SMTP_PASSWORD`：SMTP 授权码（不是邮箱登录密码）
- `NEWS_RECEIVERS`：收件人列表，逗号分隔

可选：
- `NEWS_SOURCE_URL`（默认：`https://jwc.njtech.edu.cn/index/ggtz.htm`）
- `NEWS_SENDER_NAME`（默认：`NJTech News Bot`）
- `NEWS_MAIL_SUBJECT`（默认：`NJTech News Update`）
- `NEWS_SMTP_HOST`（默认：`smtp.qq.com`）
- `NEWS_SMTP_PORT`（默认：`465`）

模板文件：
- 复制 `.env.example` 为 `.env`，并填入真实值。
- 脚本会在启动时自动加载 `.env`（如果存在）。
- 如果系统环境变量中已存在同名键，则优先使用系统环境变量。

## 运行方式
推荐方式：

```bash
cp .env.example .env
# 编辑 .env，填入真实配置
python3 ./njtech_news.sh
```

可执行模式（可选）：

```bash
chmod +x ./njtech_news.sh
./njtech_news.sh
```

仅环境变量模式（不使用 `.env`）也支持：
- `export NEWS_SENDER_EMAIL`
- `export NEWS_SMTP_PASSWORD`
- `export NEWS_RECEIVERS`
- 然后执行脚本

## 定时执行（cron）
示例：每 30 分钟执行一次。

```bash
*/30 * * * * /usr/bin/python3 /path/to/njtech_news.sh >> /path/to/njtech_news.log 2>&1
```

请确保 cron 运行环境可以读取到必需变量（或脚本目录中存在 `.env`）。

## 适配其他学院页面
如果切换到其他新闻来源页面，请检查：
- 列表选择器 `ul.my-list` 是否仍然存在
- 日期选择器 `span.date` 是否仍然存在
- 链接结构是否需要调整解析规则
