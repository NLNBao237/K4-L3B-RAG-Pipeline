"""
Task 1 — Thu thập tài liệu chính sách/quy định (chủ đề: Du lịch Việt Nam).

Nguồn: Công báo Chính phủ (congbao.chinhphu.vn) — bản PDF có text layer,
không phải bản scan, nên MarkItDown trích xuất được nội dung.

Metadata (url gốc, tiêu đề) được lưu vào data/landing/legal/sources.json để
Task 3 ghi vào header Markdown và dùng làm citation.
"""

import json
from pathlib import Path

import requests


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"
SOURCES_FILE = DATA_DIR / "sources.json"

CDN = "https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan"

LEGAL_DOCUMENTS = {
    "luat-du-lich-2017.pdf": {
        "title": "Luật Du lịch số 09/2017/QH14",
        "url": f"{CDN}/2017/6/24241/18448-1-2017515-51609-2017-qh14.pdf",
        "page": "https://congbao.chinhphu.vn/van-ban/luat-so-09-2017-qh14-24241/18448.htm",
    },
    "nghi-dinh-168-2017-huong-dan-luat-du-lich.pdf": {
        "title": "Nghị định 168/2017/NĐ-CP quy định chi tiết một số điều của Luật Du lịch",
        "url": f"{CDN}/2017/12/26028/21615-1-2018429-430168-2017-nd-cp.pdf",
        "page": "https://congbao.chinhphu.vn/noi-dung-van-ban-so-168-2017-nd-cp-26028?cbid=21615",
    },
    "nghi-dinh-94-2021-ky-quy-lu-hanh.pdf": {
        "title": "Nghị định 94/2021/NĐ-CP sửa đổi mức ký quỹ kinh doanh dịch vụ lữ hành",
        "url": f"{CDN}/2021/10/34718/37380-1-2021931-93294-2021-nd-cp.pdf",
        "page": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-94-2021-nd-cp-34718.htm",
    },
    "luat-nhap-canh-nguoi-nuoc-ngoai-hop-nhat-2023.pdf": {
        "title": "Luật Nhập cảnh, xuất cảnh, quá cảnh, cư trú của người nước ngoài tại Việt Nam (VBHN 30/VBHN-VPQH, 2023)",
        "url": f"{CDN}/2023/8/40515/47239-1-20231257-125830-vbhn-vpqh.pdf",
        "page": "https://congbao.chinhphu.vn/tai-ve-van-ban-so-30-vbhn-vpqh-40515-47239",
    },
}

HEADERS = {"User-Agent": "Mozilla/5.0 (K4-L3B RAG lab; educational use)"}


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Tải các PDF; bỏ qua file đã có để chạy lại không tải trùng."""
    for filename, info in LEGAL_DOCUMENTS.items():
        target = DATA_DIR / filename
        if target.exists() and target.stat().st_size > 1024:
            print(f"Skip (exists): {filename}")
            continue
        response = requests.get(info["url"], headers=HEADERS, timeout=60)
        response.raise_for_status()
        if not response.content.startswith(b"%PDF"):
            raise ValueError(f"{info['url']} không trả về PDF")
        target.write_bytes(response.content)
        print(f"Saved: {filename} ({len(response.content) // 1024} KB)")

    SOURCES_FILE.write_text(
        json.dumps(LEGAL_DOCUMENTS, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved metadata: {SOURCES_FILE}")


if __name__ == "__main__":
    setup_directory()
    download_documents()
