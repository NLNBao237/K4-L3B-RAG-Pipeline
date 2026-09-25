# VietGo — RAG chatbot du lịch Việt Nam (Day 8 lab)

Chatbot trả lời câu hỏi về **điểm đến, ẩm thực và quy định du lịch Việt Nam** từ bộ tài liệu nhóm tự thu thập, dùng hybrid retrieval (Dense + BM25 + RRF), PageIndex fallback, citation `[n]` và safe refusal.

## Dữ liệu

| Loại | Số lượng | Nguồn |
|---|---:|---|
| Văn bản pháp luật (PDF) | 4 | Công báo Chính phủ: Luật Du lịch 2017, NĐ 168/2017, NĐ 94/2021 (ký quỹ lữ hành), Luật Nhập cảnh người nước ngoài (VBHN 2023) |
| Bài viết (JSON) | 10 | 5 cẩm nang VnExpress Du lịch (Đà Nẵng, Nha Trang, Phú Quốc, Huế, Hội An) + 5 trang Wikipedia tiếng Việt (Phố cổ Hà Nội, Phở, Bún bò Huế, Bánh mì, Gỏi cuốn) |

URL gốc của từng tài liệu: `data/landing/legal/sources.json` và trường `url` trong `data/landing/news/*.json`.

## Kiến trúc

```
PDF/HTML ─► Task1-2 landing ─► Task3 Markdown (header: title + Source URL)
        ─► Task4 chunk 800/120 (recursive, ưu tiên heading) ─► Gemini embedding 768d ─► ChromaDB (cosine)
query ─► Task5 dense ┐
      ─► Task6 BM25+ ┴► Task7 RRF (k=60, fuse 1 lần) ─► Task9: best dense cosine < 0.70 ? PageIndex fallback
      ─► Task10 reorder + context [n] ─► LLM (gemini/openai/anthropic) ─► answer + sources (hoặc safe refusal)
```

| Quyết định | Giá trị | Lý do |
|---|---|---|
| Chunk | 800 ký tự, overlap 120 | ~1 khoản luật / 1 mục cẩm nang; separators ưu tiên `## `/`### ` |
| Embedding | `gemini-embedding-001`, 768 chiều | Hỗ trợ tiếng Việt tốt, free tier, không cần cài torch |
| BM25 | `BM25Plus` + unigram & bigram âm tiết | Okapi cho IDF = 0 trên corpus nhỏ; bigram giúp khớp từ ghép tiếng Việt ("hội an", "ký quỹ") |
| Threshold fallback | 0.70 (cosine dense) | Calibrate: 11 câu in-domain 0.710–0.898, 10 câu out-of-domain 0.541–0.689 |
| Refusal | cosine < 0.60 → từ chối ngay; còn lại LLM trả `KHONG_DU_THONG_TIN` nếu thiếu evidence | Tiết kiệm quota, không bịa |
| Bonus | Conversation memory (viết lại câu follow-up), source highlighting (nguồn được trích dẫn tô màu) | |

## Cài đặt

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m playwright install chromium
copy .env.example .env            # macOS/Linux: cp .env.example .env
```

Điền `GEMINI_API_KEY` trong `.env` (mặc định `LLM_PROVIDER=gemini`, `EMBEDDING_PROVIDER=gemini`). Có thể đổi sang `openai`/`anthropic`; đổi embedding provider thì collection Chroma mới được tạo tự động. `PAGEINDEX_API_KEY` là tuỳ chọn — không có key thì fallback tắt và pipeline trả hybrid/refusal.

## Chạy lại toàn bộ

```bash
python -m src.task1_collect_legal_docs     # tải 4 PDF
python -m src.task2_crawl_news             # crawl 10 bài bằng Crawl4AI
python -m src.task3_convert_markdown       # -> data/standardized/
python -m src.task4_chunking_indexing      # chunk + embed + ChromaDB (chỉ embed chunk mới/đổi)
python -m src.task8_pageindex_vectorless   # (tuỳ chọn) upload PDF lên PageIndex
python -m src.task10_generation            # thử 1 câu in-domain + 1 câu out-of-domain
streamlit run app.py                       # giao diện VietGo
pytest -q                                  # contract + acceptance tests
python -m group_project.evaluation.run_eval   # A/B RAGAS -> group_project/evaluation/results/
```

Trên Windows nếu terminal báo `UnicodeEncodeError`, chạy `set PYTHONUTF8=1` trước.

## Báo cáo

- Kết quả đánh giá: [reports/RESULT.md](reports/RESULT.md) (bản copy cho acceptance test: [group_project/evaluation/RESULT.md](group_project/evaluation/RESULT.md))
- Báo cáo cá nhân (làm một mình): [reports/INDIVIDUAL_REPORT.md](reports/INDIVIDUAL_REPORT.md)
- Tài liệu lab: [Module contracts](docs/MODULE_CONTRACTS.md) · [Step-by-step](docs/STEP_BY_STEP.md) · [Rubric](docs/GRADING_RUBRIC.md)
