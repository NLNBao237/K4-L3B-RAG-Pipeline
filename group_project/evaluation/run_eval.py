"""
Evaluation A/B cho VietGo RAG bằng RAGAS.

    Config A — dense-only : semantic_search -> top_k           (use_reranking=False)
    Config B — hybrid+RRF : dense + BM25 -> RRF -> top_k        (use_reranking=True)

Hai config dùng chung golden dataset, generator, evaluator, prompt và top_k;
chỉ khác retrieval strategy.

Metrics (RAGAS 0.4): faithfulness, answer relevance (ResponseRelevancy),
context recall (LLMContextRecall), context precision (LLMContextPrecisionWithReference).
Thêm 2 metric retrieval tất định không cần LLM: hit@k và MRR theo file nguồn của golden.

Chạy:
    python -m group_project.evaluation.run_eval            # dùng lại câu trả lời đã cache
    python -m group_project.evaluation.run_eval --regenerate
"""

import argparse
import json
import math
import os
import time
import warnings
from pathlib import Path

from dotenv import load_dotenv


warnings.filterwarnings("ignore")
load_dotenv()

EVAL_DIR = Path(__file__).parent
RESULTS_DIR = EVAL_DIR / "results"
GOLDEN_PATH = EVAL_DIR / "golden_dataset.json"

TOP_K = 5
EVALUATOR_MODEL = os.getenv("EVALUATOR_MODEL", "gemini-3.1-flash-lite")
EVALUATOR_EMBEDDING = "gemini-embedding-001"
GEMINI_OPENAI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"

CONFIGS = {
    "A_dense": {"label": "Config A — dense-only", "use_reranking": False},
    "B_hybrid": {"label": "Config B — hybrid + RRF", "use_reranking": True},
}
METRICS = ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]


def generate_answers(config_key: str, golden: list[dict], regenerate: bool) -> list[dict]:
    """Chạy pipeline cho từng câu hỏi; cache ra JSON để chấm lại không tốn quota."""
    from src.task10_generation import generate_answer

    cache = RESULTS_DIR / f"answers_{config_key}.json"
    if cache.exists() and not regenerate:
        return json.loads(cache.read_text(encoding="utf-8"))

    rows = []
    for item in golden:
        started = time.time()
        result = generate_answer(item["question"], top_k=TOP_K,
                                 use_reranking=CONFIGS[config_key]["use_reranking"])
        latency = time.time() - started
        sources = [source["metadata"]["source"] for source in result["sources"]]
        rank = next((i for i, source in enumerate(sources, 1) if source == item["source"]), None)
        rows.append({
            "id": item["id"],
            "question": item["question"],
            "answer": result["answer"],
            "reference": item["expected_answer"],
            "contexts": [source["content"] for source in result["sources"]],
            "sources": sources,
            "retrieval_source": result["retrieval_source"],
            "best_dense_score": result.get("best_dense_score"),
            "hit": rank is not None,
            "reciprocal_rank": 1.0 / rank if rank else 0.0,
            "latency_s": round(latency, 2),
        })
        print(f"[{config_key}] {item['id']} {latency:.1f}s hit={rank is not None}")
        time.sleep(1)  # nhẹ tay với rate limit free tier
    cache.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return rows


def ragas_score(rows: list[dict]) -> list[dict]:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas import EvaluationDataset, RunConfig, evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import (
        Faithfulness,
        LLMContextPrecisionWithReference,
        LLMContextRecall,
        ResponseRelevancy,
    )

    api_key = os.environ["GEMINI_API_KEY"]
    # Gemini qua endpoint tương thích OpenAI; bypass_n vì Gemini không hỗ trợ n>1.
    llm = LangchainLLMWrapper(
        ChatOpenAI(model=EVALUATOR_MODEL, api_key=api_key, base_url=GEMINI_OPENAI_BASE, temperature=0),
        bypass_n=True,
    )
    embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(
        model=EVALUATOR_EMBEDDING, api_key=api_key, base_url=GEMINI_OPENAI_BASE,
        check_embedding_ctx_length=False,
    ))
    dataset = EvaluationDataset.from_list([
        {
            "user_input": row["question"],
            "response": row["answer"],
            "retrieved_contexts": row["contexts"] or ["(không có ngữ cảnh)"],
            "reference": row["reference"],
        }
        for row in rows
    ])
    result = evaluate(
        dataset,
        metrics=[Faithfulness(), ResponseRelevancy(strictness=1), LLMContextRecall(), LLMContextPrecisionWithReference()],
        llm=llm,
        embeddings=embeddings,
        run_config=RunConfig(max_workers=2, timeout=240, max_retries=12, max_wait=65),
        show_progress=True,
    )
    frame = result.to_pandas().rename(columns={"llm_context_precision_with_reference": "context_precision"})
    scored = []
    for row, (_, metric_row) in zip(rows, frame.iterrows()):
        scored.append({**row, **{metric: _clean(metric_row.get(metric)) for metric in METRICS}})
    return scored


def _clean(value) -> float | None:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(value) else value


def _mean(values: list) -> float | None:
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


def summarize(scored: dict[str, list[dict]]) -> dict:
    summary = {}
    for key, rows in scored.items():
        metrics = {metric: _mean([row[metric] for row in rows]) for metric in METRICS}
        metrics["average"] = _mean(list(metrics.values()))
        metrics["hit_at_k"] = _mean([float(row["hit"]) for row in rows])
        metrics["mrr"] = _mean([row["reciprocal_rank"] for row in rows])
        metrics["latency_s"] = _mean([row["latency_s"] for row in rows])
        metrics["refusals"] = sum(row["retrieval_source"] == "none" for row in rows)
        summary[key] = metrics
    return summary


def fmt(value) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def write_markdown(summary: dict, scored: dict[str, list[dict]]) -> str:
    a, b = summary["A_dense"], summary["B_hybrid"]
    lines = ["| Metric | Config A | Config B | Delta B−A |", "|---|---:|---:|---:|"]
    for metric in METRICS + ["average", "hit_at_k", "mrr", "latency_s"]:
        delta = None if a[metric] is None or b[metric] is None else b[metric] - a[metric]
        lines.append(f"| {metric} | {fmt(a[metric])} | {fmt(b[metric])} | {fmt(delta)} |")
    lines.append(f"| refusals | {a['refusals']} | {b['refusals']} | |")

    lines += ["", "Worst performers (average of 4 metrics):", "",
              "| Config | ID | Question | Faith | Relev | Recall | Prec | hit | sources |",
              "|---|---|---|---:|---:|---:|---:|---|---|"]
    all_rows = [(key, row) for key, rows in scored.items() for row in rows]
    all_rows.sort(key=lambda pair: _mean([pair[1][m] for m in METRICS]) or 0)
    for key, row in all_rows[:6]:
        lines.append(
            f"| {key} | {row['id']} | {row['question']} | " +
            " | ".join(fmt(row[m]) for m in METRICS) +
            f" | {row['hit']} | {', '.join(Path(s).stem for s in row['sources'][:3])} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--regenerate", action="store_true", help="bỏ cache, sinh lại câu trả lời")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(exist_ok=True)
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    scored = {}
    for key in CONFIGS:
        rows = generate_answers(key, golden, args.regenerate)
        print(f"Scoring {key} with RAGAS ({EVALUATOR_MODEL})...")
        scored[key] = ragas_score(rows)
        (RESULTS_DIR / f"scores_{key}.json").write_text(
            json.dumps(scored[key], ensure_ascii=False, indent=2), encoding="utf-8")

    summary = summarize(scored)
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report = write_markdown(summary, scored)
    (RESULTS_DIR / "summary.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
