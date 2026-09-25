"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Mọi file Markdown đầu ra có cùng header để Task 4 đọc lại metadata:

    # <title>

    **Source:** <url>

    ---

Chạy lại sẽ ghi đè đúng file cũ (tên file theo tên file gốc) nên không tạo trùng.
"""

import json
import re
from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"

MIN_CHARS = 200


def build_header(title: str, url: str | None, extra: str = "") -> str:
    header = f"# {title}\n\n**Source:** {url or 'N/A'}\n\n"
    if extra:
        header += f"{extra}\n\n"
    return header + "---\n\n"


def clean_legal_text(text: str) -> str:
    """Bỏ header trang Công báo, nối các dòng bị ngắt giữa câu."""
    text = re.sub(r"(?m)^\s*\d*\s*CÔNG BÁO/Số .*$", "", text)
    text = re.sub(r"(?m)^\s*\d{1,3}\s*$", "", text)  # số trang đứng riêng
    # PDF ngắt dòng theo khổ giấy (kể cả chèn dòng trống): nối lại nếu dòng
    # trước chưa kết thúc câu và dòng sau không mở đầu một khoản/điều mới.
    lines = [re.sub(r"\s{2,}", " ", line).strip() for line in text.splitlines()]
    merged: list[str] = []
    for line in filter(None, lines):
        starts_block = re.match(r"^(Điều \d+|Chương [IVXLC]+|Mục \d+|\d+\.|[a-zđ]\))", line)
        prev_is_heading = bool(merged) and re.match(r"^Điều \d+\.", merged[-1])
        if (
            merged and not starts_block and not prev_is_heading
            and not merged[-1].endswith((".", ":", ";"))
        ):
            merged[-1] = f"{merged[-1]} {line}"
        else:
            merged.append(line)
    text = "\n\n".join(merged)
    # Tiêu đề Điều/Chương thành heading để chunk giữ ngữ cảnh.
    text = re.sub(r"(?m)^(Chương [IVXLC]+.*)$", r"## \1", text)
    text = re.sub(r"(?m)^(Điều \d+\..*)$", r"### \1", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def write_if_valid(path: Path, content: str) -> bool:
    body = content.split("---", 1)[-1].strip()
    if len(body) < MIN_CHARS:
        print(f"Skip (quá ngắn): {path.name}")
        return False
    path.write_text(content, encoding="utf-8")
    print(f"Saved: {path.relative_to(OUTPUT_DIR)} ({len(content)} chars)")
    return True


def convert_legal_docs() -> None:
    from markitdown import MarkItDown

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    sources_file = legal_dir / "sources.json"
    sources = json.loads(sources_file.read_text(encoding="utf-8")) if sources_file.exists() else {}

    converter = MarkItDown()
    for path in sorted(legal_dir.iterdir()):
        if path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue
        info = sources.get(path.name, {})
        result = converter.convert(str(path))
        body = clean_legal_text(result.text_content)
        header = build_header(
            info.get("title", path.stem),
            info.get("page") or info.get("url"),
            "**Loại tài liệu:** Văn bản quy phạm pháp luật",
        )
        write_if_valid(output_dir / f"{path.stem}.md", header + body)


def convert_news_articles() -> None:
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in sorted(news_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        header = build_header(
            data["title"], data["url"], f"**Crawled:** {data['date_crawled']}"
        )
        write_if_valid(output_dir / f"{path.stem}.md", header + data["content_markdown"].strip())


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
