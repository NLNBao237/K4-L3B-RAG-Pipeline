# RAG evaluation results

Dự án: **VietGo — chatbot RAG du lịch Việt Nam** (làm cá nhân). Số liệu gốc: `group_project/evaluation/results/` (`answers_*.json`, `scores_*.json`, `summary.json`, `summary.md`); tái lập bằng `python -m group_project.evaluation.run_eval`.

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-25 |
| Framework and version              | RAGAS 0.4.3 (`evaluate` + LangChain wrapper, `bypass_n=True`), Python 3.11.9 |
| Evaluator model                    | `gemini-3.1-flash-lite` (qua endpoint OpenAI-compatible của Gemini, temperature 0); embedding cho answer relevancy: `gemini-embedding-001` |
| Generator model                    | `gemini-3.5-flash-lite` (temperature 0.3, top_p 0.9, max 1024 tokens) |
| Embedding model                    | `gemini-embedding-001`, 768 chiều, ChromaDB cosine |
| Corpus version/commit              | Base commit `a23df34` + dữ liệu crawl ngày 2026-09-25: 4 PDF pháp luật + 10 bài viết → 14 Markdown → 748 chunks (800 ký tự, overlap 120) |
| Golden dataset size                | 18 câu (10 bài viết du lịch/ẩm thực, 8 văn bản pháp luật), `group_project/evaluation/golden_dataset.json` |
| `top_k`                            | 5 (ứng viên mỗi nhánh = 10) |
| Fallback threshold and calibration | 0.70 trên cosine gốc của dense. Calibrate bằng 11 query in-domain (best cosine 0.710–0.898) và 10 query out-of-domain (0.541–0.689). Dưới 0.60 → từ chối ngay không gọi LLM |

## Configurations

- **Config A — dense-only:** `semantic_search` (Gemini embedding + Chroma cosine) → lấy top 5 theo cosine (`use_reranking=False`).
- **Config B — hybrid + RRF:** dense top 10 + BM25Plus (unigram + bigram âm tiết) top 10 → RRF một lần (k = 60) → top 5 (`use_reranking=True`).

Hai config dùng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy.

## Overall scores

| Metric            | Config A | Config B | Delta B−A |
| ----------------- | -------: | -------: | --------: |
| Faithfulness      |    0.877 |    0.925 |    +0.048 |
| Answer relevance  |    0.964 |    0.973 |    +0.009 |
| Context recall    |    1.000 |    1.000 |     0.000 |
| Context precision |    0.852 |    0.753 |    −0.099 |
| **Average**       |**0.923** |**0.913** |**−0.011** |

Metric retrieval tất định (không dùng LLM, dựa trên file nguồn của từng câu golden): hit@5 = 1.000 ở cả A và B, MRR = 0.944 ở cả A và B. Không config nào từ chối nhầm câu in-domain (0/18).

## A/B comparison

- Cấu hình tốt hơn: **Không có khác biệt rõ rệt trên bộ 18 câu này.** Điểm trung bình 4 metric gần như bằng nhau (A 0.923, B 0.913). Mình vẫn giữ **Config B (hybrid + RRF)** làm mặc định cho chatbot vì faithfulness cao hơn (+0.048) và BM25 bắt được từ khoá chính xác như số hiệu văn bản hay tên món ăn. Tuy vậy, Config B kéo context precision xuống −0.099.
- Evidence:
  - Recall và hit@5 đều bằng 1.0 ở cả hai config, nghĩa là dense đơn lẻ đã luôn tìm được đúng tài liệu. Corpus nhỏ (14 tài liệu), và mỗi câu golden chứa tên riêng rõ ràng như "Đại Nội", "Bãi Sao", "ký quỹ".
  - Faithfulness tăng ở q09 (0.83 → 1.00), q16 (0.67 → 1.00), q17 (0.67 → 1.00) và q05 (0.83 → 0.94), giảm ở q01 (0.83 → 0.75).
  - Precision giảm mạnh ở q14 (1.00 → 0.25), q15 (1.00 → 0.25) và q06 (−0.67). Ở q14, BM25 kéo chunk đầu văn bản lên hạng 1–2 (`QUỐC HỘI Luật số: 09/2017/QH14 … LUẬT DU LỊCH` và phần mở đầu NĐ 168), vì các chunk này khớp từ "luật du lịch" nhưng không chứa định nghĩa.
  - Với n = 18, chênh lệch ±0.05–0.10 nằm trong vùng nhiễu của evaluator (xem q08 bên dưới).
- Trade-off về latency/cost:
  - Đo riêng retrieval trên 18 câu golden (median): dense 1101 ms (chủ yếu là lời gọi embedding API), BM25 31 ms, RRF 0.03 ms. Hybrid chỉ thêm khoảng 3% thời gian và **không tốn thêm API call**.
  - Latency end-to-end trong log là A 7.5 s, B 3.6 s. Con số này **không phản ánh cấu hình**: Config A chạy trước nên dính cold start và retry do rate limit của gói free (ví dụ q11 mất 21 s).
  - Cost generation như nhau, vì mỗi câu đều là 1 lời gọi LLM và 1 embedding.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------- | ---------- |
|   1 | q12 — Mức ký quỹ kinh doanh dịch vụ lữ hành nội địa hiện nay là bao nhiêu? | A và B | 0.333 | 0.991 | 1.000 | 0.500 | data/generation | Corpus chứa hai mức ký quỹ mâu thuẫn: NĐ 168/2017 (100 triệu) và NĐ 94/2021 (20 triệu, bản sửa đổi). Chunk không có metadata hiệu lực/"bị thay thế", nên model liệt kê cả hai mà không khẳng định mức **hiện hành**, trong khi reference chỉ có 20 triệu. Câu mở đầu "Chào bạn, tôi là VietGo" cũng bị evaluator tính là claim không có trong context. |
|   2 | q14 — Theo Luật Du lịch 2017, du lịch được định nghĩa như thế nào? | B | 1.000 | 1.000 | 1.000 | 0.250 | retrieval | BM25 ưu tiên các chunk đầu văn bản (quốc hiệu, tên luật, "căn cứ") vì lặp lại đúng cụm "luật du lịch". Sau RRF, hai chunk này đứng hạng 1–2, còn Điều 3 (định nghĩa) bị đẩy xuống hạng 4. Config A xếp đúng (precision 1.0). |
|   3 | q08 — Phở có nguồn gốc từ đâu? | A và B | 0.875 | 0.933 | 1.000 | 0.000 | retrieval/evaluation | Top 5 đều thuộc `wiki-pho` và có chứa câu trả lời (ctx4 gần như trùng reference), nhưng ctx1–ctx3 nói về giả thuyết "ngưu nhục phấn", chữ Nôm và infobox nên xếp trên đoạn đúng. Precision = 0 trong khi ctx4 rõ ràng liên quan cho thấy **evaluator lite chấm nhiễu** ở câu này. Cần chấm lại bằng evaluator mạnh hơn. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
|        1 | Thêm metadata `effective_date` / `superseded_by` cho văn bản pháp luật (NĐ 168 Điều 14 → NĐ 94/2021) và thêm vào prompt: "ưu tiên văn bản mới nhất, nói rõ mức hiện hành". | q12 faithfulness 0.33 ở cả hai config; model đưa cả mức cũ 100 triệu. | Faithfulness q12 lên ≥ 0.8 và câu trả lời nêu đúng 20 triệu là mức hiện hành. | Chạy lại `run_eval` cho q12, q13; kiểm tra thủ công câu trả lời. |
|        2 | Loại hoặc hạ trọng số các chunk "boilerplate" (quốc hiệu, căn cứ, chữ ký) khi index BM25; hoặc thêm cross-encoder rerank (Jina/BGE) sau RRF. | q14, q15, q06: precision của B giảm 0.67–0.75 do chunk đầu văn bản khớp từ khoá chung. | Context precision của B ≥ A (khoảng 0.85+) mà vẫn giữ faithfulness +0.05. | So sánh precision/MRR trên cùng golden set; thêm Config C (RRF + rerank) vào bảng A/B. |
|        3 | Bỏ lời chào/tự giới thiệu trong câu trả lời (sửa `SYSTEM_PROMPT`), đổi evaluator sang model mạnh hơn và mở rộng golden set lên 40+ câu (thêm câu paraphrase không chứa tên riêng, câu multi-hop, câu out-of-domain). | 9/18 câu mở đầu bằng "Chào bạn…", làm faithfulness bị trừ (q16, q17 = 0.67 ở A). Evaluator lite chấm q08 precision = 0 dù context đúng. Hit@5 = 1.0 cho thấy golden set quá dễ để phân biệt A và B. | Faithfulness trung bình tăng 0.03–0.05; A/B có ý nghĩa thống kê hơn. | Chạy `run_eval --regenerate` 2–3 lần, báo cáo mean ± độ lệch. |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| Conversation memory: viết lại câu follow-up thành câu độc lập (`rewrite_followup`) | Không có memory: câu "Ở đó có món gì ngon?" không chứa địa danh | Chưa đo bằng RAGAS; kiểm chứng qua demo: sau câu "Hội An mùa nào đẹp nhất?", câu follow-up được viết lại thành "Ở Hội An có món gì ngon?" và trả lời đúng từ cẩm nang Hội An, có citation | +1 lời gọi LLM (khoảng 1–2 s) cho mỗi câu có lịch sử; câu đầu tiên không tốn thêm | Chạy được, có demo trên UI (caption "câu hỏi đã viết lại"). Cần một golden set hội thoại để đo delta. |
| Source highlighting trong UI: nguồn được trích dẫn `[n]` được tô màu và gắn nhãn "✓ được trích dẫn" | Danh sách nguồn không phân biệt | Không áp dụng (tính năng UI); 36/36 câu trả lời trong evaluation có citation, 0 citation `[n]` vượt ngoài `sources` | Không đáng kể (parse regex) | Chạy được trên Streamlit; giúp kiểm chứng câu trả lời nhanh. |
