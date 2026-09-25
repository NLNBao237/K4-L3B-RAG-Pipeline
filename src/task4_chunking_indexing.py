"""
Task 4 — Chunking, embedding và indexing.

    1. Đọc toàn bộ Markdown trong data/standardized/ (header chứa title + URL).
    2. Chia văn bản bằng RecursiveCharacterTextSplitter, ưu tiên cắt theo heading.
    3. Embed chunks bằng một provider duy nhất (EMBEDDING_PROVIDER trong .env).
    4. Upsert vào ChromaDB với cosine distance.

ID chunk = "<đường dẫn tương đối>::chunk-<index>" nên chạy lại không tạo trùng.
Chunk nào nội dung không đổi thì không embed lại (tiết kiệm quota API).
Task 5 import embed_texts() từ file này để query và document cùng không gian vector.
"""

import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# 800 ký tự ~ 1 khoản luật hoặc 1 mục cẩm nang; overlap 15% để không cắt đôi ý.
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
CHUNKING_METHOD = "recursive"

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "gemini").strip().lower()
_DEFAULT_MODELS = {
    "gemini": ("gemini-embedding-001", 768),
    "openai": ("text-embedding-3-small", 1536),
    "sentence_transformers": ("BAAI/bge-m3", 1024),
}
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL") or _DEFAULT_MODELS[EMBEDDING_PROVIDER][0]
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM") or _DEFAULT_MODELS[EMBEDDING_PROVIDER][1])

# Đổi model/dimension => đổi tên collection, tránh trộn vector khác không gian.
COLLECTION_NAME = f"rag_documents_{EMBEDDING_PROVIDER}_{EMBEDDING_DIM}"

BATCH_SIZE = 50
_st_model = None


def _with_retry(func, *args, retries: int = 5, **kwargs):
    """Gọi API có backoff khi gặp rate limit (free tier)."""
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as error:  # noqa: BLE001 - SDK mỗi provider ném lỗi khác nhau
            if attempt == retries - 1:
                raise
            wait = 2 ** attempt * 5
            print(f"  embed lỗi ({type(error).__name__}), thử lại sau {wait}s")
            time.sleep(wait)


def _embed_batch(texts: list[str]) -> list[list[float]]:
    if EMBEDDING_PROVIDER == "gemini":
        from google import genai

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=texts,
            config={"output_dimensionality": EMBEDDING_DIM},
        )
        return [list(item.values) for item in response.embeddings]

    if EMBEDDING_PROVIDER == "openai":
        from openai import OpenAI

        response = OpenAI().embeddings.create(model=EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in response.data]

    if EMBEDDING_PROVIDER == "sentence_transformers":
        global _st_model
        if _st_model is None:
            from sentence_transformers import SentenceTransformer

            _st_model = SentenceTransformer(EMBEDDING_MODEL)
        return _st_model.encode(texts, normalize_embeddings=True).tolist()

    raise ValueError(f"EMBEDDING_PROVIDER không hỗ trợ: {EMBEDDING_PROVIDER}")


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed danh sách text theo batch; dùng chung cho index và query."""
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        vectors.extend(_with_retry(_embed_batch, texts[start:start + BATCH_SIZE]))
    return vectors


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _parse_header(text: str, fallback_title: str) -> tuple[str, str | None, str]:
    """Tách header do Task 3 tạo: trả về (title, url, body)."""
    title_match = re.search(r"^# (.+)$", text, flags=re.MULTILINE)
    url_match = re.search(r"^\*\*Source:\*\* (\S+)", text, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else fallback_title
    url = url_match.group(1).strip() if url_match else None
    if url in {"N/A", ""}:
        url = None
    body = text.split("\n---\n", 1)[1].strip() if "\n---\n" in text else text
    return title, url, body


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document."""
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        title, url, body = _parse_header(text, path.stem)
        if not body.strip():
            continue
        documents.append({
            "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
            "content": body,
            "metadata": {
                "source": path.relative_to(STANDARDIZED_DIR).as_posix(),
                "title": title,
                "doc_type": "legal" if "legal" in path.parts else "news",
                "url": url,
            },
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for document in documents:
        pieces = [piece.strip() for piece in splitter.split_text(document["content"])]
        for index, text in enumerate(piece for piece in pieces if piece):
            chunks.append({
                "id": f"{document['id']}::chunk-{index}",
                "content": text,
                "metadata": {**document["metadata"], "chunk_index": index},
            })
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk (bản copy, không sửa input)."""
    vectors = embed_texts([chunk["content"] for chunk in chunks])
    return [{**chunk, "embedding": vector} for chunk, vector in zip(chunks, vectors)]


def _to_chroma_metadata(metadata: dict) -> dict:
    # Chroma bỏ key có giá trị None -> lưu "" rồi Task 5/6 đổi ngược lại.
    return {key: ("" if value is None else value) for key, value in metadata.items()}


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    collection = get_collection()
    for start in range(0, len(chunks), 500):
        batch = chunks[start:start + 500]
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=[_to_chroma_metadata(chunk["metadata"]) for chunk in batch],
        )


def _changed_chunks(chunks: list[dict]) -> list[dict]:
    """Chỉ giữ chunk mới/đổi nội dung; xoá chunk cũ không còn trong corpus."""
    collection = get_collection()
    existing = collection.get(include=["documents"])
    stored = dict(zip(existing["ids"], existing["documents"]))
    current_ids = {chunk["id"] for chunk in chunks}
    stale = [item_id for item_id in stored if item_id not in current_ids]
    if stale:
        collection.delete(ids=stale)
        print(f"Removed {len(stale)} stale chunks")
    return [chunk for chunk in chunks if stored.get(chunk["id"]) != chunk["content"]]


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    print(f"{len(documents)} documents -> {len(chunks)} chunks "
          f"({EMBEDDING_PROVIDER}/{EMBEDDING_MODEL}, dim={EMBEDDING_DIM})")
    todo = _changed_chunks(chunks)
    if todo:
        embedded_chunks = embed_chunks(todo)
        index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(todo)} new/changed chunks; collection has {get_collection().count()}")


if __name__ == "__main__":
    run_pipeline()
