# Individual contribution report

## Thông tin

- Họ và tên: `<Nguyễn Lê Ngọc Bảo>`
- Mã học viên: `<2A202602852>`
- Nhóm: Làm cá nhân (không có nhóm) — tự thực hiện toàn bộ pipeline, đề tài **Du lịch Việt Nam (VietGo)**
- Repository/branch: `K4-L3B-RAG-Pipeline` / `main` (GitHub: NLNBao237)

## Phần việc đã thực hiện

Vì làm một mình, tôi phụ trách toàn bộ các module dưới đây.

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Thu thập dữ liệu (Task 1–2) | Tải 4 PDF pháp luật từ Công báo Chính phủ, lưu URL gốc vào `sources.json`; crawl 10 bài (5 cẩm nang VnExpress, 5 Wikipedia) bằng Crawl4AI, bỏ link/ảnh/phần tham khảo | `src/task1_collect_legal_docs.py`, `src/task2_crawl_news.py`, `data/landing/` | Done |
| Chuẩn hoá (Task 3) | MarkItDown cho PDF; nối dòng bị ngắt theo khổ giấy; chuyển "Chương/Điều" thành heading; header chung `# title` + `**Source:** url` | `src/task3_convert_markdown.py`, `data/standardized/` | Done |
| Chunk, embed, index (Task 4) | Recursive 800/120 ưu tiên heading; `embed_texts` hỗ trợ gemini/openai/sentence-transformers, có batch và retry; chỉ embed chunk mới hoặc đã đổi; ChromaDB cosine (748 chunks) | `src/task4_chunking_indexing.py` | Done |
| Hybrid search (Task 5–7) | Dense search (đổi `url` từ `""` về `None` để đúng contract); BM25Plus + bigram âm tiết tiếng Việt; RRF k = 60 | `src/task5_semantic_search.py`, `src/task6_lexical_search.py`, `src/task7_reranking.py` | Done |
| Fallback + pipeline (Task 8–9) | PageIndex SDK (upload PDF, cache doc_id, poll có timeout, lỗi thì trả `[]`); `retrieve_with_info` fuse đúng một lần, fallback dựa trên cosine dense; calibrate threshold 0.70 | `src/task8_pageindex_vectorless.py`, `src/task9_retrieval_pipeline.py` | Done (PageIndex chưa có API key nên fallback đang tắt, pipeline trả hybrid/refusal) |
| Generation (Task 10) | Dispatch 3 provider; citation `[n]` luôn trỏ về `sources[n-1]` kể cả sau khi reorder; safe refusal 2 tầng; conversation memory (viết lại câu follow-up) | `src/task10_generation.py` | Done |
| Chatbot UI | Streamlit theo thiết kế VietGo (hero, điểm đến, ẩm thực, FAQ); thẻ nguồn có score/method, tô màu nguồn được trích dẫn; sidebar chuyển Hybrid/Dense để demo A/B | `app.py` | Done |
| Evaluation | Golden set 18 câu có `expected_context` trích nguyên văn; script RAGAS 4 metric + hit@k/MRR, A/B dense vs hybrid; viết báo cáo phân tích | `group_project/evaluation/golden_dataset.json`, `run_eval.py`, `results/`, `RESULT.md` | Done |

Bằng chứng kiểm thử: `pytest -q` pass **20/20** (15 contract + 5 acceptance). Commit chứa toàn bộ phần trên: `<điền hash sau khi commit>`.

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng `BM25Plus` với token gồm unigram và bigram âm tiết, thay cho `BM25Okapi` + `split()` như code mẫu.
   **Lý do/evidence:** Khi thử trên corpus 2 tài liệu của contract test, `BM25Okapi` trả score `[0, 0]` (IDF = 0 khi từ xuất hiện ở đúng một nửa corpus), nên test `lexical_search` fail. `BM25Plus` cho `[4.26, 2.19]`. Tiếng Việt là ngôn ngữ đơn lập nên bigram giúp khớp các cụm như "hội an", "ký quỹ", "lữ hành".
   **Trade-off:** Index lớn gấp khoảng 2 lần (vẫn chỉ khoảng 31 ms/query trên 748 chunks). Bigram cũng làm BM25 khớp mạnh với chunk đầu văn bản lặp tên luật: context precision của hybrid ở q14/q15 giảm từ 1.00 xuống 0.25.

2. **Quyết định:** Threshold fallback 0.70 trên **cosine gốc của dense** (không dùng RRF score), kết hợp từ chối ngay khi cosine < 0.60 và để LLM trả marker `KHONG_DU_THONG_TIN` khi context không đủ.
   **Lý do/evidence:** Calibrate bằng 21 query: in-domain 0.710–0.898, out-of-domain 0.541–0.689. RRF score (khoảng 0.03) là thang thứ hạng, không so sánh được. Kết quả: 0/18 câu golden bị từ chối nhầm; "Giá bitcoin hôm nay?" bị từ chối mà không gọi LLM.
   **Trade-off:** Khoảng cách giữa hai cụm hẹp (0.689 so với 0.710). Câu in-domain diễn đạt lạ có thể rơi xuống dưới 0.70 (lúc đó thử PageIndex); câu ngoài domain nhưng gần chủ đề (như "Cách nấu bánh chưng", 0.689) vẫn tới LLM và phụ thuộc vào prompt để từ chối.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: `pytest tests/test_contracts.py` và `tests/test_acceptance.py`; 21 query calibrate in/out-of-domain; 18 câu golden cho RAGAS; demo UI với "Hội An mùa nào đẹp nhất?", rồi follow-up "Ở đó có món gì ngon?", và "Giá bitcoin hôm nay?".
- Kết quả trước/sau nếu có:
  - Hybrid so với dense-only: faithfulness 0.877 → 0.925 (+0.048), answer relevance 0.964 → 0.973, context recall giữ 1.000, context precision 0.852 → 0.753 (−0.099), trung bình 0.923 → 0.913. Hit@5 = 1.0 và MRR = 0.944 ở cả hai.
  - Memory: câu follow-up được viết lại thành "Ở Hội An có món gì ngon?" và trả lời đúng nguồn.
- Lỗi đã phát hiện và cách xử lý:
  - Chroma tự bỏ key metadata có giá trị `None`, làm `validate_document` fail. Xử lý: lưu `""` rồi đổi ngược lại khi đọc.
  - PDF Nghị định 168 trên vanban.chinhphu.vn là bản scan (0 ký tự text). Xử lý: đổi sang bản PDF của Công báo có text layer.
  - Console Windows cp1252 gây `UnicodeEncodeError`. Xử lý: `reconfigure(encoding="utf-8")` trong `src/__init__.py`.
  - Evaluator `gemini-3.5-flash` hết quota free tier (limit 20), khiến điểm ra NaN. Xử lý: đổi sang `gemini-3.1-flash-lite` và bật `bypass_n=True` (Gemini không hỗ trợ `n > 1`).
  - Avatar "✦" không phải emoji làm `st.chat_message` crash. Xử lý: đổi sang emoji 🧭.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Văn bản pháp luật không có metadata hiệu lực. Câu "mức ký quỹ lữ hành nội địa hiện nay" (q12) nêu cả mức cũ 100 triệu (NĐ 168/2017) lẫn mức mới 20 triệu (NĐ 94/2021) mà không khẳng định mức hiện hành, nên faithfulness chỉ đạt 0.33. Ngoài ra golden set quá dễ (hit@5 = 1.0 ở cả hai config) nên A/B chưa phân biệt được rõ.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Thêm `effective_date`/`superseded_by` vào metadata chunk pháp luật và yêu cầu prompt ưu tiên văn bản mới nhất; sau đó thêm cross-encoder rerank sau RRF để lấy lại context precision, rồi đo lại trên golden set mở rộng 40+ câu.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-25
- Tên thành viên: `<điền họ tên>`
