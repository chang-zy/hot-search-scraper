# main.py
# -*- coding: utf-8 -*-
"""
定时抓取各平台热榜并写入 SQLite: hot_items_history

用法：
    python main.py
    python main.py --db hot.db --providers zhihu,weibo,baidu
    python main.py --interval 3600    # 每小时跑一次

注意：
- 微博需要环境变量 WEIBO_COOKIE
- 你可以通过 HTTPS_PROXY / HTTP_PROXY 走代理
"""
from __future__ import annotations
import argparse
import time
from datetime import datetime

from storage import HotItemsHistoryDB

from scraper.zhihu import ZhihuHotSpider
from scraper.weibo import WeiboHotSpider
from scraper.douyin import DouyinHotSpider
from scraper.baidu import BaiduHotSpider
from scraper.cailian import CailianHotSpider

# 一个注册表，方便后面循环
SPIDER_REGISTRY = {
    "zhihu": ZhihuHotSpider,
    "weibo": WeiboHotSpider,
    "douyin": DouyinHotSpider,
    "baidu": BaiduHotSpider,
    "cailian": CailianHotSpider,
}


def parse_args():
    p = argparse.ArgumentParser(description="抓取热榜并写入 SQLite")
    p.add_argument("--db", default="hot.db", help="SQLite 文件路径")
    p.add_argument(
        "--providers",
        default="zhihu,weibo,douyin,baidu,cailian",
        help="要抓取的平台，逗号分隔，可选：zhihu,weibo,douyin,baidu",
    )
    p.add_argument(
        "--interval",
        type=int,
        default=12 * 60 * 60,
        help="两次抓取之间的间隔（秒），默认 12 小时",
    )
    return p.parse_args()


def run_once(db_path: str, provider_names: list[str]):
    """
    跑一轮：依次抓取各平台，写入 SQLite
    """
    print(f"\n====== 执行抓取任务 @ {datetime.now():%Y-%m-%d %H:%M:%S} ======")

    db = HotItemsHistoryDB(db_path=db_path)
    total = 0

    try:
        for name in provider_names:
            name = name.lower()
            if name not in SPIDER_REGISTRY:
                print(f"[skip] 不支持的平台：{name}")
                continue

            SpiderCls = SPIDER_REGISTRY[name]
            spider = SpiderCls()

            print(f"[{name}] 开始抓取...")
            try:
                items = spider.run()
            except Exception as e:
                print(f"[{name}] 抓取异常：{e}")
                continue

            if not items:
                print(f"[{name}] 无数据，可能被风控/需要 Cookie")
                continue

            # 不同平台的特殊字段
            extra_fields: list[str] = []
            topic_key_field: str | None = None

            if name == "weibo":
                topic_key_field = "word_scheme"
                extra_fields = ["word_scheme"]
            elif name == "douyin":
                topic_key_field = "sentence_id"
            elif name == "baidu":
                extra_fields = ["avatar_url"]
            elif name == "zhihu":
                extra_fields = ["avatar_url"]
            elif name == "cailian":
                extra_fields = ["id", "ctime", "level", "comment_num"]

            try:
                inserted = db.upsert_history(
                    platform=name,
                    items=items,
                    topic_key_field=topic_key_field,
                    tags_join_from=None,
                    extra_fields=extra_fields,
                )
                print(f"[{name}] upsert 成功：{inserted} 条")
                total += inserted
            except Exception as e:
                print(f"[{name}] 入库失败：{e}")

    finally:
        db.close()

    print(f"[done] 本轮共写入 {total} 条记录")
    print("=" * 60)


def main():
    args = parse_args()
    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    interval = args.interval

    # 持续循环
    while True:
        start = time.time()
        run_once(args.db, providers)
        elapsed = time.time() - start
        sleep_sec = max(0, interval - elapsed)
        # 这里不能做异步，只是阻塞 sleep
        print(f"[sleep] 将在 {sleep_sec/3600:.2f} 小时后再次抓取...\n")
        time.sleep(sleep_sec)


if __name__ == "__main__":
    main()
