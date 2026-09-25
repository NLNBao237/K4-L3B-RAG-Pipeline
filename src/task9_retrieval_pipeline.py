"""
Task 9 — Retrieval pipeline hoàn chỉnh.

Luồng xử lý:
    1. Chạy semantic_search và lexical_search.
    2. Fuse hai danh sách bằng RRF đúng một lần.
    3. Lấy best cosine score gốc từ dense results.
    4. Nếu score dưới threshold, thử PageIndex fallback.
    5. Nếu fallback lỗi/rỗng, trả hybrid results thay vì crash.

Không so sánh threshold với RRF score vì hai thang đo khác nhau.

Calibration (gemini-embedding-001, 768 dim) trên 11 query in-domain và 10
query out-of-domain: in-domain best dense score 0.710–0.898, out-of-domain
0.541–0.689 => SCORE_THRESHOLD = 0.70.
"""

import os

from dotenv import load_dotenv

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_rrf
from .task8_pageindex_vectorless import pageindex_search


load_dotenv()

SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD") or 0.70)
DEFAULT_TOP_K = 5
CANDIDATE_MULTIPLIER = 2


def retrieve_with_info(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> tuple[list[dict], dict]:
    """Như retrieve() nhưng trả thêm thông tin chẩn đoán cho UI/evaluation."""
    dense = semantic_search(query, top_k=top_k * CANDIDATE_MULTIPLIER)
    best_dense_score = dense[0]["score"] if dense else 0.0
    info = {"best_dense_score": best_dense_score, "fallback": "not_needed"}

    if use_reranking:
        sparse = lexical_search(query, top_k=top_k * CANDIDATE_MULTIPLIER)
        results = rerank_rrf([dense, sparse], top_k=top_k)
    else:
        results = dense[:top_k]

    if best_dense_score < score_threshold:
        try:
            fallback = pageindex_search(query, top_k=top_k)
            if fallback:
                info["fallback"] = "pageindex"
                return fallback[:top_k], info
            info["fallback"] = "empty"
        except Exception as error:  # noqa: BLE001 - fallback không được làm crash
            info["fallback"] = f"error: {error}"
    return results[:top_k], info


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """Trả về hybrid hoặc pageindex SearchResult."""
    results, _ = retrieve_with_info(query, top_k, score_threshold, use_reranking)
    return results


if __name__ == "__main__":
    for result in retrieve("Mức ký quỹ lữ hành nội địa là bao nhiêu?", top_k=3):
        print(f"{result['retrieval_method']} {result['score']:.4f} | "
              f"{result['metadata']['title']} | {result['content'][:80]}")
