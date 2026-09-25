"""VietGo — Streamlit chatbot RAG du lịch Việt Nam (giao diện theo mẫu VietGo)."""

import html
import time

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv


load_dotenv()

st.set_page_config(page_title="VietGo — Khám phá Việt Nam cùng AI", page_icon="✦", layout="wide")

# --------------------------------------------------------------------------- #
# Dữ liệu hiển thị (ảnh lấy từ mẫu thiết kế)
# --------------------------------------------------------------------------- #
UNSPLASH = "https://images.unsplash.com/{}?auto=format&fit=crop&w=900&q=80"
DESTINATIONS = [
    ("Hà Nội", "Phố cổ · Văn hóa · Ẩm thực", "photo-1509030450996-dd1a26dda07a", "Phố cổ Hà Nội có gì đặc biệt?"),
    ("Hội An", "Phố cổ · Đèn lồng · Chậm rãi", "photo-1559592413-7cec4d0cae2b", "Hội An mùa nào đẹp nhất?"),
    ("Đà Nẵng", "Biển · Núi · Thành phố", "photo-1559592413-7cec4d0cae2b", "Đà Nẵng có những điểm tham quan nào?"),
    ("Nha Trang", "Biển xanh · Lặn biển · Nghỉ dưỡng", "photo-1609766418204-94aae0ecf7b0", "Nha Trang có những đặc sản gì?"),
    ("Phú Quốc", "Hoàng hôn · Đảo · Hải sản", "photo-1540202404-a2f29016b523", "Đi Phú Quốc nên tắm biển ở bãi nào?"),
    ("Huế", "Cố đô · Di sản · Văn hóa", "photo-1583417319070-4a69db38a482", "Vé tham quan Đại Nội Huế giá bao nhiêu?"),
]
FOODS = [
    ("Phở", "Miền Bắc · Hà Nội", "photo-1555126634-323283e090fa"),
    ("Bánh mì", "Phổ biến khắp Việt Nam", "photo-1601050690597-df0568f70950"),
    ("Bún bò Huế", "Miền Trung · Huế", "photo-1569058242253-92a9c755a0ec"),
    ("Gỏi cuốn", "Miền Nam · Tươi mát", "photo-1604908177522-0406d1e6c0f8"),
]
SUGGESTED = [
    "Hội An mùa nào đẹp nhất?",
    "Ẩm thực Đà Nẵng có gì?",
    "Phở có nguồn gốc từ đâu?",
    "Mức ký quỹ kinh doanh lữ hành nội địa?",
]
FAQ = [
    "Khách du lịch có những quyền gì?",
    "Thị thực điện tử có thời hạn bao lâu?",
    "Bún bò Huế gồm nguyên liệu gì?",
    "Phú Quốc có những trải nghiệm nào?",
]
METHOD_LABEL = {"hybrid": "Hybrid · RRF", "dense": "Dense", "bm25": "BM25", "pageindex": "PageIndex"}

# --------------------------------------------------------------------------- #
# CSS — design tokens từ mẫu VietGo
# --------------------------------------------------------------------------- #
st.html("""
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{--teal:#087f78;--teal-dark:#075d59;--sea:#159fc0;--sun:#f6bd4f;--wood:#a46c3c;--cream:#fffaf0;
--ink:#173c3a;--muted:#6b7d7b;--line:#e5ece9;--shadow:0 18px 50px rgba(18,73,68,.12);--radius:22px;}
html,body,[class*="st-"],.stMarkdown,button,input,textarea{font-family:"Be Vietnam Pro",sans-serif!important;}
.stApp{background:#fbfdfc;color:var(--ink);}
header[data-testid="stHeader"]{background:transparent;}
.block-container{padding-top:0!important;max-width:1200px;}
#MainMenu,footer[data-testid="stFooter"]{visibility:hidden;}

.vg-nav{display:flex;align-items:center;justify-content:space-between;height:72px;}
.vg-logo{display:flex;align-items:center;gap:10px;font-size:1.25rem;font-weight:800;color:var(--ink);}
.vg-logo-mark{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;color:#fff;
  background:linear-gradient(145deg,var(--teal),var(--sea));}
.vg-links{display:flex;gap:26px;font-size:.92rem;font-weight:600;}
.vg-links a{color:var(--ink)!important;text-decoration:none!important;}
.vg-links a:hover{color:var(--teal)!important;}
.vg-cta{padding:10px 18px;border-radius:999px;background:var(--teal);color:#fff!important;font-weight:700;text-decoration:none!important;}

.vg-hero{min-height:470px;border-radius:28px;overflow:hidden;display:flex;align-items:center;color:#fff;padding:56px;
  background:linear-gradient(90deg,rgba(7,54,55,.85) 0%,rgba(7,54,55,.5) 50%,rgba(7,54,55,.12) 100%),
  url("https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=1800&q=85") center/cover;}
.vg-eyebrow{display:inline-flex;padding:8px 13px;border-radius:999px;background:rgba(255,255,255,.16);font-size:.82rem;font-weight:700;}
.vg-hero h1{max-width:720px;margin:18px 0 14px;font-size:clamp(2.3rem,5vw,4.6rem);line-height:1.04;letter-spacing:-2px;color:#fff;font-weight:800;padding:0;}
.vg-hero p{max-width:640px;color:rgba(255,255,255,.88);font-size:1.05rem;}
.vg-stats{display:flex;gap:26px;margin-top:22px;flex-wrap:wrap;}
.vg-stats b{display:block;font-size:1.4rem;}
.vg-stats span{font-size:.8rem;color:rgba(255,255,255,.75);}

.st-key-hero_search{background:#fff;border-radius:18px;padding:10px 12px 2px;margin:-38px auto 0;max-width:880px;
  box-shadow:0 22px 55px rgba(0,0,0,.14);position:relative;z-index:5;}
.st-key-hero_search input{border:0!important;}

.vg-kicker{color:var(--teal);font-size:.78rem;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;margin-top:56px;}
.vg-h2{font-size:clamp(1.7rem,3.4vw,2.5rem);line-height:1.15;margin:6px 0 4px;font-weight:800;color:var(--ink);}
.vg-sub{color:var(--muted);margin-bottom:22px;}

.vg-grid{display:grid;gap:18px;}
.vg-grid.dest{grid-template-columns:repeat(3,1fr);}
.vg-grid.food{grid-template-columns:repeat(4,1fr);}
.vg-dest{position:relative;height:260px;border-radius:var(--radius);overflow:hidden;color:#fff;box-shadow:0 8px 28px rgba(0,0,0,.08);transition:.3s;}
.vg-dest:hover{transform:translateY(-6px);box-shadow:var(--shadow);}
.vg-dest img{width:100%;height:100%;object-fit:cover;transition:transform .5s;}
.vg-dest:hover img{transform:scale(1.06);}
.vg-dest::after{content:"";position:absolute;inset:35% 0 0;background:linear-gradient(transparent,rgba(0,0,0,.72));}
.vg-dest-info{position:absolute;z-index:2;left:20px;right:20px;bottom:18px;}
.vg-dest-info h3{font-size:1.3rem;color:#fff;padding:0;margin:0;font-weight:800;}
.vg-dest-info p{color:rgba(255,255,255,.85);font-size:.85rem;margin:0;}
.vg-food{border-radius:20px;overflow:hidden;background:#fff;border:1px solid var(--line);transition:.25s;}
.vg-food:hover{transform:translateY(-5px);box-shadow:var(--shadow);}
.vg-food img{width:100%;height:170px;object-fit:cover;}
.vg-food div{padding:13px 16px 16px;}
.vg-food h3{font-size:1rem;margin:0;padding:0;color:var(--ink);font-weight:700;}
.vg-food span{color:var(--wood);font-size:.8rem;}

.stButton>button{border-radius:999px;border:1px solid var(--line);background:#fff;color:var(--ink);font-weight:600;font-size:.82rem;transition:.2s;}
.stButton>button:hover{border-color:var(--teal);color:var(--teal);background:#fff;}
.st-key-hero_search .stButton>button,.stFormSubmitButton>button{background:var(--teal)!important;color:#fff!important;border:0!important;border-radius:13px!important;font-weight:700;}

.st-key-chat_panel{background:#fff;border:1px solid var(--line);border-radius:24px;box-shadow:var(--shadow);padding:0 0 8px;overflow:hidden;}
.vg-chat-head{display:flex;align-items:center;gap:12px;padding:16px 20px;border-bottom:1px solid var(--line);}
.vg-ai{width:40px;height:40px;display:grid;place-items:center;border-radius:13px;background:linear-gradient(145deg,var(--teal),var(--sea));color:#fff;font-weight:800;font-size:.8rem;}
.vg-status{color:#3b8b62;font-size:.73rem;}
[data-testid="stChatMessage"]{background:transparent;}
[data-testid="stChatInput"] textarea{font-size:.92rem;}

.vg-sources{display:grid;gap:8px;margin-top:6px;}
.vg-src{border:1px solid var(--line);border-radius:14px;padding:10px 12px;background:#fbfdfc;font-size:.8rem;}
.vg-src.cited{border-color:var(--teal);background:#effaf8;box-shadow:inset 3px 0 0 var(--teal);}
.vg-src-top{display:flex;gap:8px;align-items:center;flex-wrap:wrap;}
.vg-num{min-width:24px;height:24px;border-radius:8px;display:grid;place-items:center;background:var(--teal);color:#fff;font-weight:800;font-size:.75rem;}
.vg-src:not(.cited) .vg-num{background:#c9d6d3;}
.vg-title{font-weight:700;color:var(--ink);}
.vg-pill{padding:2px 8px;border-radius:999px;background:#fff;border:1px solid var(--line);color:var(--muted);font-size:.7rem;font-weight:600;}
.vg-pill.legal{color:var(--wood);border-color:#ecd9c6;}
.vg-snippet{color:var(--muted);margin-top:6px;line-height:1.5;}
.vg-src a{color:var(--teal)!important;font-weight:600;}
.vg-meta{color:var(--muted);font-size:.72rem;margin-top:4px;}

.vg-footer{background:#123f3b;color:#fff;border-radius:24px;padding:34px 36px 22px;margin:70px 0 30px;}
.vg-footer p{color:rgba(255,255,255,.65);font-size:.85rem;margin:6px 0 0;}
.vg-copy{border-top:1px solid rgba(255,255,255,.12);margin-top:22px;padding-top:14px;color:rgba(255,255,255,.5);font-size:.75rem;}

@media (max-width:900px){.vg-links{display:none;}.vg-grid.dest{grid-template-columns:repeat(2,1fr);}.vg-grid.food{grid-template-columns:repeat(2,1fr);}}
@media (max-width:620px){.vg-hero{padding:34px 22px;}.vg-cta{display:none;}.vg-grid.dest,.vg-grid.food{grid-template-columns:1fr;}}
</style>
""")

# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Xin chào! 👋 Mình là VietGo. Hỏi mình về điểm đến, món ăn hay quy định du lịch Việt Nam nhé — "
                   "mọi câu trả lời đều kèm nguồn để bạn kiểm chứng.",
        "sources": [],
    }]
if "pending" not in st.session_state:
    st.session_state.pending = None


def ask(question: str) -> None:
    """Callback cho các nút gợi ý: đưa câu hỏi vào hàng đợi và cuộn tới chat."""
    st.session_state.pending = question
    st.session_state.scroll_to_chat = True


# --------------------------------------------------------------------------- #
# Sidebar — cấu hình pipeline (phục vụ demo A/B)
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown("### ✦ VietGo settings")
    top_k = st.slider("Số chunks (top_k)", 3, 10, 5)
    mode = st.radio("Retrieval", ["Hybrid (Dense + BM25 + RRF)", "Dense-only"], index=0)
    use_memory = st.toggle("Conversation memory", value=True,
                           help="Viết lại câu hỏi follow-up dựa trên lịch sử chat")
    show_debug = st.toggle("Hiện thông tin retrieval", value=True)
    if st.button("🗑️ Xoá hội thoại", use_container_width=True):
        st.session_state.messages = st.session_state.messages[:1]
        st.rerun()
    try:
        from src.task10_generation import LLM_MODEL, LLM_PROVIDER
        from src.task4_chunking_indexing import EMBEDDING_MODEL
        from src.task9_retrieval_pipeline import SCORE_THRESHOLD
        st.caption(f"LLM: `{LLM_PROVIDER}/{LLM_MODEL}`  \nEmbedding: `{EMBEDDING_MODEL}`  \n"
                   f"Fallback threshold (cosine): `{SCORE_THRESHOLD}`")
    except Exception as error:  # noqa: BLE001
        st.error(f"Không load được pipeline: {error}")

# --------------------------------------------------------------------------- #
# Nav + Hero
# --------------------------------------------------------------------------- #
st.html("""
<div class="vg-nav">
  <div class="vg-logo"><span class="vg-logo-mark">✦</span><span>Viet<span style="color:var(--teal)">Go</span></span></div>
  <div class="vg-links"><a href="#destinations">Điểm đến</a><a href="#food">Ẩm thực</a><a href="#assistant">AI Assistant</a><a href="#faq">Câu hỏi</a></div>
  <a class="vg-cta" href="#assistant">Hỏi AI ✨</a>
</div>
<section class="vg-hero"><div>
  <span class="vg-eyebrow">🇻🇳 Khám phá Việt Nam theo cách của bạn</span>
  <h1>Mỗi hành trình<br>là một câu chuyện.</h1>
  <p>Tìm điểm đến, món ngon và quy định du lịch. Trợ lý AI trả lời từ cẩm nang du lịch, Wikipedia và văn bản pháp luật chính thức — luôn kèm nguồn.</p>
  <div class="vg-stats"><div><b>14</b><span>tài liệu nguồn</span></div><div><b>4</b><span>văn bản pháp luật</span></div><div><b>Hybrid</b><span>Dense + BM25 + RRF</span></div></div>
</div></section>
""")

with st.container(key="hero_search"):
    with st.form("hero_form", clear_on_submit=True, border=False):
        col_input, col_button = st.columns([5, 1])
        hero_query = col_input.text_input("Tìm kiếm", placeholder="⌕  Bạn muốn khám phá gì? Ví dụ: Hội An mùa nào đẹp?",
                                          label_visibility="collapsed")
        if col_button.form_submit_button("Khám phá →", use_container_width=True) and hero_query.strip():
            ask(hero_query.strip())

# --------------------------------------------------------------------------- #
# Điểm đến & Ẩm thực
# --------------------------------------------------------------------------- #
dest_cards = "".join(
    f'<article class="vg-dest"><img src="{UNSPLASH.format(img)}" alt="{name}">'
    f'<div class="vg-dest-info"><h3>{name}</h3><p>{tags}</p></div></article>'
    for name, tags, img, _ in DESTINATIONS
)
st.html(f"""
<div id="destinations" class="vg-kicker">Đi đâu hôm nay?</div>
<div class="vg-h2">Điểm đến nổi bật</div>
<div class="vg-sub">Chọn một điểm đến bên dưới để hỏi nhanh VietGo.</div>
<div class="vg-grid dest">{dest_cards}</div>
""")
for column, (name, _, _, question) in zip(st.columns(6), DESTINATIONS):
    column.button(f"Hỏi về {name}", key=f"dest_{name}", on_click=ask, args=(question,), use_container_width=True)

food_cards = "".join(
    f'<article class="vg-food"><img src="{UNSPLASH.format(img).replace("w=900", "w=700")}" alt="{name}">'
    f'<div><h3>{name}</h3><span>{region}</span></div></article>'
    for name, region, img in FOODS
)
st.html(f"""
<div id="food" class="vg-kicker">Ăn gì đây?</div>
<div class="vg-h2">Ẩm thực Việt Nam</div>
<div class="vg-sub">Mỗi vùng miền có một hương vị riêng.</div>
<div class="vg-grid food">{food_cards}</div>
""")
for column, (name, _, _) in zip(st.columns(4), FOODS):
    column.button(f"🍜 {name} là gì?", key=f"food_{name}", on_click=ask,
                  args=(f"{name} có nguồn gốc và cách chế biến như thế nào?",), use_container_width=True)


# --------------------------------------------------------------------------- #
# Render helpers
# --------------------------------------------------------------------------- #
def render_sources(sources: list[dict], cited: list[int]) -> None:
    if not sources:
        return
    cards = []
    for index, source in enumerate(sources, 1):
        meta = source["metadata"]
        is_cited = index in cited
        snippet = html.escape(source["content"][:260].replace("\n", " ")) + ("…" if len(source["content"]) > 260 else "")
        link = (f'<a href="{html.escape(meta["url"])}" target="_blank">Mở nguồn ↗</a>'
                if meta.get("url") else "")
        doc_type = "Pháp luật" if meta.get("doc_type") == "legal" else "Bài viết"
        cards.append(f"""
        <div class="vg-src {'cited' if is_cited else ''}">
          <div class="vg-src-top"><span class="vg-num">{index}</span>
            <span class="vg-title">{html.escape(meta['title'])}</span>
            <span class="vg-pill {'legal' if meta.get('doc_type') == 'legal' else ''}">{doc_type}</span>
            <span class="vg-pill">{METHOD_LABEL.get(source['retrieval_method'], source['retrieval_method'])} · {source['score']:.4f}</span>
            {'<span class="vg-pill" style="color:var(--teal)">✓ được trích dẫn</span>' if is_cited else ''}
          </div>
          <div class="vg-snippet">{snippet}</div>
          <div class="vg-meta">{html.escape(meta['source'])} · chunk #{meta.get('chunk_index', 0)} {('· ' + link) if link else ''}</div>
        </div>""")
    with st.expander(f"📚 Nguồn tham khảo ({len(cited)}/{len(sources)} được trích dẫn)", expanded=bool(cited)):
        st.html(f'<div class="vg-sources">{"".join(cards)}</div>')


def render_message(message: dict) -> None:
    avatar = "🧑" if message["role"] == "user" else "🧭"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])
        info = message.get("info")
        if info and show_debug and message["role"] == "assistant":
            parts = [f"retrieval: **{info.get('retrieval_source')}**",
                     f"best dense cosine: **{info.get('best_dense_score', 0):.3f}**",
                     f"fallback: {info.get('fallback')}", f"{info.get('latency', 0):.1f}s"]
            if info.get("standalone_query") and info["standalone_query"] != info.get("query"):
                parts.insert(0, f"câu hỏi đã viết lại: _{info['standalone_query']}_")
            st.caption(" · ".join(parts))
        render_sources(message.get("sources", []), message.get("cited", []))


# --------------------------------------------------------------------------- #
# AI Assistant
# --------------------------------------------------------------------------- #
st.html('<div id="assistant"></div>')
left, right = st.columns([1, 1.35], gap="large")
with left:
    st.html("""
    <div class="vg-kicker">AI Travel Assistant</div>
    <div class="vg-h2">Không biết đi đâu?<br>Hỏi VietGo.</div>
    <div class="vg-sub">Trợ lý tìm trong kho cẩm nang du lịch, Wikipedia và văn bản pháp luật về du lịch,
    trả lời có trích dẫn <b>[n]</b> để bạn kiểm chứng. Câu hỏi ngoài phạm vi sẽ được từ chối lịch sự.</div>
    """)
    for index, question in enumerate(SUGGESTED):
        st.button(question, key=f"sugg_{index}", on_click=ask, args=(question,))

with right:
    with st.container(key="chat_panel"):
        st.html("""<div class="vg-chat-head"><div class="vg-ai">AI</div>
            <div><strong>VietGo Assistant</strong><div class="vg-status">● Đang sẵn sàng hỗ trợ</div></div></div>""")
        history_box = st.container(height=520, border=False)
        typed = st.chat_input("Hỏi AI về chuyến đi của bạn...")

    query = typed or st.session_state.pending
    st.session_state.pending = None

    with history_box:
        for message in st.session_state.messages:
            render_message(message)

        if query:
            history = [m for m in st.session_state.messages[1:] if m["role"] in {"user", "assistant"}]
            user_message = {"role": "user", "content": query}
            st.session_state.messages.append(user_message)
            render_message(user_message)

            with st.chat_message("assistant", avatar="🧭"):
                with st.spinner("VietGo đang tìm trong kho tài liệu..."):
                    started = time.time()
                    try:
                        from src.task10_generation import generate_answer

                        result = generate_answer(
                            query,
                            top_k=top_k,
                            use_reranking=mode.startswith("Hybrid"),
                            history=history if use_memory else None,
                        )
                    except Exception as error:  # noqa: BLE001 - UI không được crash
                        result = {"answer": f"Xin lỗi, hệ thống đang gặp sự cố: {error}",
                                  "sources": [], "retrieval_source": "none"}
            info = {
                "query": query,
                "retrieval_source": result.get("retrieval_source"),
                "best_dense_score": result.get("best_dense_score", 0.0),
                "fallback": result.get("fallback", "-"),
                "standalone_query": result.get("standalone_query"),
                "latency": time.time() - started,
            }
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["answer"],
                "sources": result.get("sources", []),
                "cited": result.get("cited", []),
                "info": info,
            })
            st.rerun()

# --------------------------------------------------------------------------- #
# FAQ + Footer
# --------------------------------------------------------------------------- #
st.html("""<div id="faq" class="vg-kicker">Khám phá nhanh</div><div class="vg-h2">Câu hỏi nổi bật</div>
<div class="vg-sub">Bấm để hỏi ngay — câu trả lời hiện trong khung chat phía trên.</div>""")
for column, (index, question) in zip(st.columns(4), enumerate(FAQ)):
    column.button(question, key=f"faq_{index}", on_click=ask, args=(question,), use_container_width=True)

st.html("""
<footer class="vg-footer">
  <div style="display:flex;justify-content:space-between;gap:24px;flex-wrap:wrap">
    <div><div class="vg-logo" style="color:#fff">✦ VietGo</div><p>Khám phá Việt Nam cùng AI.</p></div>
    <p>Nguồn dữ liệu: Công báo Chính phủ · VnExpress Du lịch · Wikipedia tiếng Việt (CC BY-SA)</p>
  </div>
  <div class="vg-copy">© 2026 VietGo. Demo RAG Travel Assistant — K4 Day 8 lab.</div>
</footer>
""")

# Cuộn tới khung chat khi câu hỏi đến từ nút ở hero/điểm đến/FAQ.
if st.session_state.pop("scroll_to_chat", False):
    components.html(
        "<script>setTimeout(()=>window.parent.document.getElementById('assistant')"
        "?.scrollIntoView({behavior:'smooth'}),300)</script>",
        height=0,
    )
