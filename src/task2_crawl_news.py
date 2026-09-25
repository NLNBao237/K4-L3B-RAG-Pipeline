"""
Task 2 — Crawl bài viết du lịch bằng Crawl4AI.

Nguồn: cẩm nang du lịch VnExpress và Wikipedia tiếng Việt (CC BY-SA).
Mỗi bài lưu thành một JSON trong data/landing/news/ với url, title,
date_crawled, content_markdown.

Cài browser trước khi chạy:
    python -m playwright install chromium
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

# (slug, url, title dự phòng khi trang không trả <title>)
ARTICLES = [
    ("cam-nang-da-nang", "https://vnexpress.net/cam-nang-du-lich-da-nang-4470111.html",
     "Cẩm nang du lịch Đà Nẵng"),
    ("cam-nang-nha-trang", "https://vnexpress.net/cam-nang-du-lich-nha-trang-tu-a-den-z-4127199.html",
     "Cẩm nang du lịch Nha Trang"),
    ("cam-nang-phu-quoc", "https://vnexpress.net/cam-nang-du-lich-phu-quoc-4106697.html",
     "Cẩm nang du lịch Phú Quốc"),
    ("cam-nang-hue", "https://vnexpress.net/cam-nang-du-lich-hue-4126937.html",
     "Cẩm nang du lịch Huế"),
    ("cam-nang-hoi-an", "https://vnexpress.net/cam-nang-du-lich-hoi-an-4446174.html",
     "Cẩm nang du lịch Hội An"),
    ("wiki-pho-co-ha-noi", "https://vi.wikipedia.org/wiki/Ph%E1%BB%91_c%E1%BB%95_H%C3%A0_N%E1%BB%99i",
     "Phố cổ Hà Nội"),
    ("wiki-pho", "https://vi.wikipedia.org/wiki/Ph%E1%BB%9F",
     "Phở"),
    ("wiki-bun-bo-hue", "https://vi.wikipedia.org/wiki/B%C3%BAn_b%C3%B2_Hu%E1%BA%BF",
     "Bún bò Huế"),
    ("wiki-banh-mi", "https://vi.wikipedia.org/wiki/B%C3%A1nh_m%C3%AC_Vi%E1%BB%87t_Nam",
     "Bánh mì Việt Nam"),
    ("wiki-goi-cuon", "https://vi.wikipedia.org/wiki/G%E1%BB%8Fi_cu%E1%BB%91n",
     "Gỏi cuốn"),
]

# Giữ lại ít nhất 5 URL công khai như yêu cầu của lab.
ARTICLE_URLS = [url for _, url, _ in ARTICLES]

# Phần cuối trang Wikipedia không mang thông tin du lịch.
WIKI_STOP_HEADINGS = ("Xem thêm", "Tham khảo", "Chú thích", "Liên kết ngoài", "Đọc thêm", "Ghi chú")


def clean_markdown(markdown: str, url: str) -> str:
    """Bỏ chú thích [1], dòng ảnh, menu ngắn và phần tham khảo."""
    text = re.sub(r"\[\d+\]", "", markdown)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if "wikipedia.org" in url and re.match(r"^#+\s*(%s)" % "|".join(WIKI_STOP_HEADINGS), stripped):
            break
        if stripped.startswith(("Ảnh:", "Ảnh minh họa", "!")) or stripped in {"*", "* * *"}:
            continue
        # Menu điều hướng của VnExpress: bullet rất ngắn.
        if re.fullmatch(r"\*\s*.{0,25}", stripped) and "vnexpress" in url:
            continue
        lines.append(line.rstrip())
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


async def crawl_article(url: str, crawler=None, fallback_title: str = "Unknown") -> dict:
    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

    config = CrawlerRunConfig(
        css_selector="#mw-content-text" if "wikipedia.org" in url else None,
        excluded_tags=["nav", "header", "footer", "aside", "form", "script", "style"],
        markdown_generator=DefaultMarkdownGenerator(
            options={"ignore_links": True, "ignore_images": True}
        ),
        page_timeout=60000,
        verbose=False,
    )

    async def _run(active_crawler):
        result = await active_crawler.arun(url=url, config=config)
        if not result.success:
            raise RuntimeError(result.error_message)
        title = (result.metadata or {}).get("title") or fallback_title
        title = title.split(" - Báo VnExpress")[0].split(" – Wikipedia")[0].strip()
        return {
            "url": url,
            "title": title,
            "date_crawled": datetime.now().isoformat(timespec="seconds"),
            "content_markdown": clean_markdown(str(result.markdown), url),
        }

    if crawler is not None:
        return await _run(crawler)
    async with AsyncWebCrawler() as own_crawler:
        return await _run(own_crawler)


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON (tên file ổn định theo slug)."""
    from crawl4ai import AsyncWebCrawler, BrowserConfig

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with AsyncWebCrawler(config=BrowserConfig(verbose=False)) as crawler:
        for slug, url, title in ARTICLES:
            try:
                article = await crawl_article(url, crawler, fallback_title=title)
                if len(article["content_markdown"]) < 500:
                    raise ValueError("nội dung quá ngắn, có thể bị chặn")
                output = DATA_DIR / f"{slug}.json"
                output.write_text(
                    json.dumps(article, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(f"Saved: {output.name} ({len(article['content_markdown'])} chars)")
            except Exception as error:
                print(f"Failed: {url} — {error}")


if __name__ == "__main__":
    asyncio.run(crawl_all())
