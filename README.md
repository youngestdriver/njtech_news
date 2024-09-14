# njtech_news
❤️一些爬取njtech教务处网站最新新闻的脚本❤️
---
一般用法：<br>
1.修改`sender` 替换为你的实际发件人地址 <br> 
> *自定义方法查看https://service.mail.qq.com/detail/124/995* <br>

2.修改`password` 替换为你的SMTP授权码 <br>
> *具体方法查看https://wx.mail.qq.com/list/readtemplate?name=app_intro.html#/agreement/authorizationCode* <br>

3.修改`receivers` 替换为你的实际收件人地址 <br>
> *可多可少，用英文逗号分隔*

4.将脚本拷贝到linux服务器上，命令行输入指令，赋予权限
> `chmod 777 ./njtech_news.sh` <br>

5.然后设置cron，定时运行该脚本
> 具体操作自行查阅 <br>

效果预览: <br>
<img src="https://pic.papercrane.top/file/AgACAgUAAyEGAASGppjQAAMFZuWO2C840ldC_f63gczcvod6qekAAr7AMRtLaihXLK08XNGPP1oBAAMCAAN3AAM2BA.png" alt="pic_pc.png" width=70% /> <br>
<img src="https://pic.papercrane.top/file/AgACAgUAAyEGAASGppjQAAMGZuWO2kkTHWz4i_vBwVXw2QOGJ2YAAr_AMRtLaihXZnyEDYJ2iqEBAAMCAAN3AAM2BA.png" alt="pic_phone.png" width=30% />
