#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl
import os


def fetch_html(url):
    try:
        # 处理SSL证书验证
        response = requests.get(url, timeout=30, verify='/etc/ssl/certs/ca-certificates.crt')  # 指定证书路径
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        return response.text
    except requests.RequestException as e:
        print(f"获取数据失败: {e}")
        return None

def parse_content(html):
    base_url = 'https://jwc.njtech.edu.cn'
    soup = BeautifulSoup(html, 'html.parser')
    news_list = soup.find('ul', class_='my-list')
    if not news_list:
        print("未找到新闻列表")
        return None

    news_items = news_list.find_all('li')
    if not news_items:
        print("未找到新闻项")
        return None

    content = """
    <html>
    <head>
        <style>
            table { width: 100%; border-collapse: collapse; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <h2>Njtech教务处新闻</h2>
        <table>
            <tr>
                <th>标题</th>
                <th>日期</th>
            </tr>
    """
    for item in news_items:
        link = item.find('a')
        date = item.find('span', class_='date')
        if link and date:
            title = link.text.strip()
            url = link['href']
            url = url.replace('../', '')  # 删除所有 '../'
            url = base_url + '/' + url  # 添加基础 URL
            news_date = date.text.strip()
            content += f"<tr><td><a href='{url}'>{title}</a></td><td>{news_date}</td></tr>"
        else:
            print("某些新闻项缺少必要信息")
            continue
    content += "</table></body></html>"
    return content

def send_email(content, sender, password, receivers):
    message = MIMEMultipart()
    message['From'] = sender
    message['To'] = ", ".join(receivers)
    message['Subject'] = 'Njtech教务处网站新闻'
    message.attach(MIMEText(content, 'html', 'utf-8'))

    # 读取上一次的邮件内容
    last_content_path = './last_email_content.html'
    if os.path.exists(last_content_path):
        with open(last_content_path, 'r', encoding='utf-8') as file:
            last_content = file.read()
    else:
        last_content = ''

    # 比较当前内容与上一次内容
    if content == last_content:
        print("邮件内容未变更，不发送邮件")
        return
    else:
    try:
            # 使用SSL上下文来安全发送邮件
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.qq.com", 465, context=context) as smtp_obj:
            smtp_obj.login(sender, password)
            smtp_obj.sendmail(sender, receivers, message.as_string())
            print("邮件发送成功")
                # 保存当前内容为最新内容
                with open(last_content_path, 'w', encoding='utf-8') as file:
                    file.write(content)
    except smtplib.SMTPException as e:
        print(f"错误: 无法发送邮件，原因：{e}")

def main():
    url = 'https://jwc.njtech.edu.cn/index/ggtz.htm'
    html = fetch_html(url)
    if html:
        content = parse_content(html)
        sender = 'xxx@qq.com'                       # 替换为你的实际发件人地址 自定义方法查看https://service.mail.qq.com/detail/124/995
        password = ''                               # 替换为你的SMTP授权码 具体方法查看https://wx.mail.qq.com/list/readtemplate?name=app_intro.html#/agreement/authorizationCode
        receivers = ['xxx1@qq.com, xxx2@qq.com']    # 替换为你的实际收件人地址
        send_email(content, sender, password, receivers)

if __name__ == "__main__":
    main()
