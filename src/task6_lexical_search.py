"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5 (đọc từ ChromaDB). BM25 phù hợp với từ khóa
chính xác, số hiệu văn bản và tên riêng. Output theo SearchResult, sort giảm dần.

Lựa chọn kỹ thuật:
- BM25Plus thay vì BM25Okapi: Okapi cho IDF = 0 khi từ xuất hiện ở đúng nửa
  corpus (corpus nhỏ) nên mọi score bằng 0; BM25Plus luôn có IDF dương.
- Tiếng Việt là ngôn ngữ đơn lập: một từ gồm nhiều âm tiết ("hội an",
  "ký quỹ"). Ta index cả unigram lẫn bigram âm tiết để khớp cụm từ.
"""

import re


CORPUS: list[dict] = []

_TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)
_cache: dict = {"key": None, "bm25": None, "corpus": None, "tokens": None}


def tokenize(text: str) -> list[str]:
    syllables = _TOKEN_RE.findall(text.lower())
    bigrams = [f"{a}_{b}" for a, b in zip(syllables, syllables[1:])]
    return syllables + bigrams


def _load_corpus() -> list[dict]:
    """CORPUS (test/monkeypatch) nếu có, ngược lại đọc toàn bộ chunks từ Chroma."""
    if CORPUS:
        return CORPUS
    from .task4_chunking_indexing import get_collection

    data = get_collection().get(include=["documents", "metadatas"])
    return [
        {
            "id": item_id,
            "content": content,
            "metadata": {**metadata, "url": metadata.get("url") or None},
        }
        for item_id, content, metadata in zip(data["ids"], data["documents"], data["metadatas"])
    ]


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    from rank_bm25 import BM25Plus

    return BM25Plus([tokenize(item["content"]) for item in corpus])


def _get_index() -> tuple[object, list[dict], list[set[str]]]:
    corpus = _load_corpus()
    key = tuple(item["id"] for item in corpus)
    if _cache["key"] != key:
        _cache.update(
            key=key,
            bm25=build_bm25_index(corpus) if corpus else None,
            corpus=corpus,
            tokens=[set(tokenize(item["content"])) for item in corpus],
        )
    return _cache["bm25"], _cache["corpus"], _cache["tokens"]


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    import numpy as np

    bm25, corpus, corpus_tokens = _get_index()
    query_tokens = tokenize(query)
    if bm25 is None or not query_tokens or top_k <= 0:
        return []

    scores = bm25.get_scores(query_tokens)
    # Chỉ giữ chunk có ít nhất một token khớp query (BM25Plus cho điểm nền > 0).
    query_set = set(query_tokens)
    results = []
    for index in np.argsort(scores)[::-1]:
        if len(results) >= top_k:
            break
        if not query_set & corpus_tokens[index]:
            continue
        item = corpus[index]
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": float(scores[index]),
            "metadata": item["metadata"],
            "retrieval_method": "bm25",
        })
    return results


if __name__ == "__main__":
    for result in lexical_search("mức ký quỹ lữ hành quốc tế", top_k=3):
        print(f"{result['score']:.2f} | {result['metadata']['title']} | {result['content'][:100]}")
