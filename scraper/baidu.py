# scraper/baidu_spider.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import urllib.request
import urllib.error
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any


class BaiduHotSpider:
    """
    百度实时热搜爬虫
    run() -> List[Dict[str, Any]]
    每条数据字段：
      {
        "rank": 1,
        "title": "...",
        "desc": "...",
        "heat_text": "7904613",
        "image_url": "https://...",
        "url": "https://www.baidu.com/s?wd=xxx",
        "scraped_at": "2025-11-07 10:00:00"
      }
    """

    def __init__(self) -> None:
        self.url = "https://top.baidu.com/board?tab=realtime"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }

    def fetch_html(self) -> str:
        req = urllib.request.Request(self.url, headers=self.headers)
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            return resp.read().decode("utf-8", errors="ignore")
        except urllib.error.URLError as e:
            print(f"❌ 请求失败: {e}")
            return ""

    def parse(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        results: List[Dict[str, Any]] = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        items = soup.find_all("div", class_="category-wrap_iQLoo")
        for i, item in enumerate(items, 1):
            # 排名
            rank_div = item.find("div", class_="index_1Ew5p")
            rank = rank_div.get_text(strip=True) if rank_div else str(i)

            # 封面图
            image_url = ""
            img_wrap = item.find("a", class_="img-wrapper_29V76") or item.find("a", class_="img-wrapper_")
            if img_wrap:
                img_tag = img_wrap.find("img")
                if img_tag and img_tag.get("src"):
                    src = img_tag["src"]
                    image_url = "https:" + src if src.startswith("//") else src

            # 标题
            title_div = item.find("div", class_="c-single-text-ellipsis")
            title = title_div.get_text(strip=True) if title_div else ""

            # 描述
            desc_div = item.find("div", class_="hot-desc_1m_jR")
            desc = ""
            if desc_div:
                desc = desc_div.get_text(strip=True).replace("查看更多>", "").strip()

            # 热度
            hot_div = item.find("div", class_="hot-index_1Bl1a")
            heat_text = hot_div.get_text(strip=True) if hot_div else ""

            # 链接
            url = ""
            link_tag = item.find("a", href=True)
            if link_tag:
                href = link_tag["href"]
                url = href if href.startswith("http") else "https://www.baidu.com" + href

            results.append(
                {
                    "rank": int(rank) if rank.isdigit() else rank,
                    "title": title,
                    "desc": desc,
                    "heat_text": heat_text,
                    "image_url": image_url,   # ✅ 改为统一字段名
                    "url": url,
                    "scraped_at": now,
                }
            )

        return results

    def run(self) -> List[Dict[str, Any]]:
        html = self.fetch_html()
        return self.parse(html) if html else []


if __name__ == "__main__":
    spider = BaiduHotSpider()
    data = spider.run()
    print(f"共抓取 {len(data)} 条百度热榜")
    for d in data[:5]:
        print(f"{d['rank']}. {d['title']} 🔥{d['heat_text']}")
        print(f"   封面: {d['image_url']}")
        if d['desc']:
            print("   " + d['desc'])