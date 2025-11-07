# 🔥 Hot Search Scraper
一个轻量级的「知乎、微博、抖音、百度」热榜采集与可视化系统。

# Quick Start
## 创建数据库
这会创建 hot.db 并建立必要的表结构与索引。
```bash
python init_db.py
```
## 获取数据
开启爬虫，默认4小时获取一次。
```bash
python main.py 
```

## 界面可视化
开启浏览器访问。
```bash
streamlit run app.py
```
