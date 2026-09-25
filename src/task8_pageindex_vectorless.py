"""
Task 8 — PageIndex vectorless fallback.

    1. Đọc PAGEINDEX_API_KEY từ .env (không có key => fallback tắt, trả []).
    2. Upload PDF gốc trong data/landing/legal/ (PageIndex nhận PDF).
    3. Cache doc_id vào pageindex_doc_ids.json để không upload lại.
    4. Parse retrieved_nodes thành SearchResult có retrieval_method="pageindex".

PageIndex là dịch vụ ngoài: mọi lỗi/timeout đều bị bắt để pipeline không crash.
"""

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
ROOT = Path(__file__).parent.parent
STANDARDIZED_DIR = ROOT / "data" / "standardized"
LEGAL_PDF_DIR = ROOT / "data" / "landing" / "legal"
DOC_ID_CACHE = ROOT / "pageindex_doc_ids.json"

POLL_INTERVAL = 2.0
QUERY_TIMEOUT = 30.0


def _client():
    from pageindex import PageIndexClient

    return PageIndexClient(api_key=PAGEINDEX_API_KEY)


def _load_doc_ids() -> dict[str, str]:
    if DOC_ID_CACHE.exists():
        return json.loads(DOC_ID_CACHE.read_text(encoding="utf-8"))
    return {}


def _load_titles() -> dict[str, dict]:
    sources = LEGAL_PDF_DIR / "sources.json"
    return json.loads(sources.read_text(encoding="utf-8")) if sources.exists() else {}


def upload_documents() -> None:
    """Upload tài liệu và lưu mapping filename -> doc_id để tái sử dụng."""
    if not PAGEINDEX_API_KEY:
        print("PAGEINDEX_API_KEY trống — bỏ qua upload (fallback sẽ tắt).")
        return
    client = _client()
    doc_ids = _load_doc_ids()
    for pdf in sorted(LEGAL_PDF_DIR.glob("*.pdf")):
        if pdf.name in doc_ids:
            print(f"Skip (đã upload): {pdf.name}")
            continue
        response = client.submit_document(str(pdf))
        print(f"Uploaded {pdf.name}: {response}")
        doc_ids[pdf.name] = response["doc_id"]
        DOC_ID_CACHE.write_text(json.dumps(doc_ids, indent=2), encoding="utf-8")
    for name, doc_id in doc_ids.items():
        print(f"{name}: retrieval_ready={client.is_retrieval_ready(doc_id)}")


def _wait_for_retrieval(client, retrieval_id: str, deadline: float) -> dict:
    while time.time() < deadline:
        result = client.get_retrieval(retrieval_id)
        if result.get("status") == "completed":
            return result
        if result.get("status") == "failed":
            raise RuntimeError(f"PageIndex retrieval failed: {result}")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError("PageIndex retrieval timeout")


def _parse_nodes(result: dict, filename: str, titles: dict) -> list[dict]:
    """Mỗi relevant_content của một node thành một ứng viên."""
    info = titles.get(filename, {})
    items = []
    for node in result.get("retrieved_nodes") or []:
        contents = node.get("relevant_contents") or [{"relevant_content": node.get("text", "")}]
        for part_index, part in enumerate(contents):
            text = (part.get("relevant_content") or "").strip()
            if not text:
                continue
            node_id = node.get("node_id", "node")
            items.append({
                "id": f"pageindex::{filename}::{node_id}::{part_index}",
                "content": text,
                "metadata": {
                    "source": f"legal/{Path(filename).stem}.md",
                    "title": f"{info.get('title', filename)} — {node.get('title', '')}".strip(" —"),
                    "doc_type": "legal",
                    "url": info.get("page") or info.get("url"),
                    "chunk_index": int(part.get("page_index") or 0),
                },
            })
    return items


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult; không có key hoặc lỗi => []."""
    if not PAGEINDEX_API_KEY or top_k <= 0:
        return []
    doc_ids = _load_doc_ids()
    if not doc_ids:
        return []

    client = _client()
    titles = _load_titles()
    deadline = time.time() + QUERY_TIMEOUT
    candidates: list[dict] = []
    for filename, doc_id in doc_ids.items():
        try:
            retrieval_id = client.submit_query(doc_id, query)["retrieval_id"]
            result = _wait_for_retrieval(client, retrieval_id, deadline)
            candidates.extend(_parse_nodes(result, filename, titles))
        except Exception as error:  # noqa: BLE001 - dịch vụ ngoài, không được làm crash
            print(f"PageIndex lỗi với {filename}: {error}")

    # API không trả score -> gán theo thứ hạng (giảm dần) và loại ID trùng.
    unique, seen = [], set()
    for item in candidates:
        if item["id"] not in seen:
            seen.add(item["id"])
            unique.append(item)
    return [
        {**item, "score": 1.0 / rank, "retrieval_method": "pageindex"}
        for rank, item in enumerate(unique[:top_k], 1)
    ]


if __name__ == "__main__":
    upload_documents()
