"""
Task 10 — Generation có citation.

    1. (Bonus) Viết lại câu hỏi follow-up thành câu độc lập nhờ lịch sử chat.
    2. Retrieve top-k chunks.
    3. Reorder để giảm lost-in-the-middle.
    4. Format context kèm số [n], title và source.
    5. Gọi provider được chọn trong .env.
    6. Trả answer, sources và retrieval_source.

Citation [n] luôn trỏ tới sources[n-1] (sources giữ thứ tự score giảm dần),
kể cả khi context đã bị reorder. Nếu context không đủ hoặc provider lỗi, trả
safe refusal; không bịa thông tin.
"""

import os
import re

from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve_with_info


load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3
MAX_OUTPUT_TOKENS = 1024

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
_DEFAULT_LLM = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-3.5-flash-lite",
    "anthropic": "claude-haiku-4-5",
}
LLM_MODEL = os.getenv("LLM_MODEL") or _DEFAULT_LLM.get(LLM_PROVIDER, "")

# Dưới ngưỡng này (cosine) câu hỏi chắc chắn ngoài domain -> từ chối không cần gọi LLM.
# Giữa REFUSAL_THRESHOLD và SCORE_THRESHOLD để LLM tự quyết theo prompt.
REFUSAL_THRESHOLD = float(os.getenv("REFUSAL_THRESHOLD") or 0.60)

REFUSAL_MESSAGE = (
    "Xin lỗi, mình không tìm thấy thông tin này trong nguồn dữ liệu du lịch hiện có "
    "nên không thể xác minh. Bạn thử hỏi về điểm đến, ẩm thực hoặc quy định du lịch Việt Nam nhé!"
)
REFUSAL_MARKER = "KHONG_DU_THONG_TIN"

SYSTEM_PROMPT = f"""Bạn là VietGo, trợ lý du lịch Việt Nam.
Quy tắc bắt buộc:
- Chỉ trả lời dựa trên các tài liệu trong phần Context. Không dùng kiến thức bên ngoài.
- Mỗi câu chứa thông tin phải có citation dạng [n], trong đó n là số của tài liệu
  (ví dụ: "Vé vào Đại Nội giá 200.000 đồng [2]."). Có thể ghép nhiều nguồn: [1][3].
- Không bịa số liệu, giá, ngày tháng. Nếu các tài liệu có thông tin khác nhau, nêu rõ.
- Nếu Context không chứa thông tin để trả lời câu hỏi, chỉ trả về đúng chuỗi {REFUSAL_MARKER}.
- Trả lời bằng tiếng Việt, ngắn gọn, dùng gạch đầu dòng khi liệt kê."""

REWRITE_PROMPT = """Viết lại câu hỏi cuối của người dùng thành một câu hỏi độc lập,
đầy đủ ngữ cảnh (điểm đến, món ăn, chủ đề) dựa trên lịch sử hội thoại.
Nếu câu hỏi đã độc lập thì giữ nguyên. Chỉ trả về câu hỏi, không giải thích."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context (không sửa list gốc)."""
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có số citation, title và source label."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk["metadata"]
        number = chunk.get("citation_id", index)
        url = metadata.get("url") or "N/A"
        parts.append(
            f"[{number}] Title: {metadata['title']} | Source: {metadata['source']} | URL: {url}\n"
            f"{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo LLM_PROVIDER; trả về text thuần."""
    if LLM_PROVIDER == "openai":
        from openai import OpenAI

        response = OpenAI(api_key=os.getenv("OPENAI_API_KEY")).chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
            max_tokens=MAX_OUTPUT_TOKENS,
        )
        return (response.choices[0].message.content or "").strip()

    if LLM_PROVIDER == "gemini":
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model=LLM_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            ),
        )
        return (response.text or "").strip()

    if LLM_PROVIDER == "anthropic":
        from anthropic import Anthropic

        response = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY")).messages.create(
            model=LLM_MODEL,
            system=system_prompt,
            max_tokens=MAX_OUTPUT_TOKENS,
            temperature=TEMPERATURE,
            messages=[{"role": "user", "content": user_message}],
        )
        return "".join(block.text for block in response.content if block.type == "text").strip()

    raise ValueError(f"LLM_PROVIDER không hỗ trợ: {LLM_PROVIDER}")


def rewrite_followup(query: str, history: list[dict] | None) -> str:
    """Bonus conversation memory: 'ở đó ăn gì?' -> 'Ở Hội An ăn gì?'."""
    if not history:
        return query
    turns = "\n".join(
        f"{'Người dùng' if turn['role'] == 'user' else 'Trợ lý'}: {turn['content'][:300]}"
        for turn in history[-4:]
    )
    try:
        rewritten = call_llm(REWRITE_PROMPT, f"Lịch sử:\n{turns}\n\nCâu hỏi cuối: {query}")
        return rewritten.strip().strip('"') or query
    except Exception:  # noqa: BLE001 - lỗi rewrite thì dùng câu gốc
        return query


def cited_ids(answer: str, sources: list[dict]) -> list[int]:
    """Các số [n] trong answer map được về sources (1-based)."""
    numbers = {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
    return sorted(n for n in numbers if 1 <= n <= len(sources))


def _refusal() -> dict:
    return {"answer": REFUSAL_MESSAGE, "sources": [], "retrieval_source": "none"}


def generate_answer(
    query: str,
    top_k: int = TOP_K,
    use_reranking: bool = True,
    history: list[dict] | None = None,
) -> dict:
    """GenerationResult + các field chẩn đoán (standalone_query, best_dense_score, ...).

    Dùng cho UI và A/B evaluation (use_reranking=False => Config A dense-only).
    """
    standalone_query = rewrite_followup(query, history)
    try:
        chunks, info = retrieve_with_info(standalone_query, top_k=top_k, use_reranking=use_reranking)
    except Exception as error:  # noqa: BLE001 - vector store/embedding lỗi -> từ chối an toàn
        return {**_refusal(), "standalone_query": standalone_query, "error": str(error)}

    extra = {"standalone_query": standalone_query, **info}
    if not chunks or (
        info["best_dense_score"] < REFUSAL_THRESHOLD and info["fallback"] != "pageindex"
    ):
        return {**_refusal(), **extra}

    numbered = [{**chunk, "citation_id": index} for index, chunk in enumerate(chunks, 1)]
    context = format_context(reorder_for_llm(numbered))
    user_message = f"Context:\n{context}\n\nCâu hỏi: {standalone_query}"
    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as error:  # noqa: BLE001 - provider lỗi -> từ chối an toàn
        return {**_refusal(), **extra, "error": str(error)}

    if not answer or REFUSAL_MARKER in answer:
        return {**_refusal(), **extra}

    method = chunks[0]["retrieval_method"]
    return {
        "answer": answer,
        "sources": chunks,
        # Dense-only (Config A) vẫn là nhánh retrieval chính, không phải fallback.
        "retrieval_source": "pageindex" if method == "pageindex" else "hybrid",
        **extra,
        "cited": cited_ids(answer, chunks),
    }


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult đúng contract."""
    result = generate_answer(query, top_k=top_k)
    return {key: result[key] for key in ("answer", "sources", "retrieval_source")}


if __name__ == "__main__":
    from .contracts import validate_generation_result

    for question in ("Mức ký quỹ kinh doanh lữ hành nội địa là bao nhiêu?", "Giá bitcoin hôm nay?"):
        output = generate_with_citation(question)
        validate_generation_result(output)
        print(f"Q: {question}\nA: {output['answer']}\nretrieval_source={output['retrieval_source']}")
        for index, source in enumerate(output["sources"], 1):
            print(f"  [{index}] {source['metadata']['title']} ({source['score']:.4f})")
        print()
