"""
VisionarySTEM Frontend — Streamlit Application
==============================================
Voice-first accessible UI for visually impaired STEM students.

Run: streamlit run frontend/app.py
"""

from __future__ import annotations

import io
import sys
import time
from pathlib import Path

import requests
import streamlit as st

# Add parent so `frontend.utils` resolves
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.utils import api_client as api
from frontend.utils.pdf_renderer import overlay_bounding_boxes, render_page_png

# ============================================================
# Page config
# ============================================================
st.set_page_config(
    page_title="VisionarySTEM — Trợ lý AI cho sinh viên khiếm thị",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load theme
CSS_FILE = Path(__file__).parent / "styles" / "high_contrast.css"
if CSS_FILE.exists():
    st.markdown(f"<style>{CSS_FILE.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


# ============================================================
# Session state init
# ============================================================
def _init_state():
    defaults = {
        "blocks": [],
        "spatial_index": {},
        "metadata": {},
        "document_id": None,
        "file_bytes": None,
        "filename": "",
        "current_page": 1,
        "highlight_block_id": None,
        "use_mock": True,
        "tts_rate": "+0%",
        "tts_pitch": "+0Hz",
        "stream_log": [],
        "query_history": [],
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


_init_state()


# ============================================================
# Sidebar — controls
# ============================================================
with st.sidebar:
    st.markdown("# 🔬 VisionarySTEM")
    st.markdown("**Trợ lý AI cho sinh viên khiếm thị STEM**")

    # Backend health
    try:
        h = api.health()
        st.success(f"✓ Backend v{h.get('version', '?')} — {h.get('gemini_model', '')}")
    except Exception as e:
        st.error(f"✗ Backend không phản hồi: {e}")
        st.info("Chạy: `uvicorn src.api.main:app --reload`")

    st.divider()

    # Mock vs Real toggle
    st.session_state.use_mock = st.toggle(
        "🧪 Dùng dữ liệu giả lập (Mock)",
        value=st.session_state.use_mock,
        help="Bật để test UI mà không tốn quota Gemini",
    )

    st.divider()

    # File upload
    st.markdown("### 📄 Tải tài liệu")
    uploaded = st.file_uploader(
        "Chọn PDF hoặc ảnh STEM",
        type=["pdf", "png", "jpg", "jpeg", "webp"],
        label_visibility="collapsed",
    )
    if uploaded is not None:
        st.session_state.file_bytes = uploaded.getvalue()
        st.session_state.filename = uploaded.name
        st.success(f"Đã chọn: {uploaded.name} ({len(uploaded.getvalue()) // 1024} KB)")

    st.divider()

    # TTS settings — accessibility critical for low-vision users
    st.markdown("### 🔊 Cài đặt giọng đọc")
    rate_pct = st.slider(
        "Tốc độ đọc (%)",
        min_value=-50, max_value=100, value=0, step=10,
        help="Người khiếm thị thường thích nghe ở 50%-100% nhanh hơn",
    )
    pitch_hz = st.slider(
        "Cao độ (Hz)",
        min_value=-20, max_value=20, value=0, step=5,
    )
    st.session_state.tts_rate = f"{'+' if rate_pct >= 0 else ''}{rate_pct}%"
    st.session_state.tts_pitch = f"{'+' if pitch_hz >= 0 else ''}{pitch_hz}Hz"
    st.caption(f"Hiện: rate={st.session_state.tts_rate}, pitch={st.session_state.tts_pitch}")


# ============================================================
# Main header
# ============================================================
st.markdown('<a href="#main-content" class="skip-link">Bỏ qua tới nội dung chính</a>', unsafe_allow_html=True)
st.markdown("# 🔬 VisionarySTEM")
st.markdown(
    "_Phân tích tài liệu STEM tiếng Việt → giọng đọc tự nhiên + truy vấn theo không gian._"
)

st.markdown('<div id="main-content"></div>', unsafe_allow_html=True)

# ============================================================
# Action row — Analyze buttons
# ============================================================
col_a, col_b, col_c = st.columns([1, 1, 1])

with col_a:
    if st.button("🚀 Phân tích (streaming)", type="primary", use_container_width=True,
                 disabled=st.session_state.file_bytes is None and not st.session_state.use_mock):
        if st.session_state.use_mock:
            with st.spinner("Đang lấy dữ liệu mock..."):
                result = api.mock_analyze()
                st.session_state.blocks = result.blocks
                st.session_state.spatial_index = result.spatial_index
                st.session_state.metadata = result.metadata
                st.session_state.document_id = result.document_id
                st.session_state.stream_log = [{"event": "done", "ts": time.time()}]
            st.rerun()
        else:
            # SSE streaming analyze
            placeholder = st.empty()
            log_box = st.expander("📡 Stream events", expanded=False)
            blocks_streamed = []
            doc_id = None
            t0 = time.time()
            try:
                for event_name, data in api.analyze_file_stream(
                    st.session_state.file_bytes,
                    st.session_state.filename or "upload.pdf",
                ):
                    elapsed = time.time() - t0
                    log_entry = {"event": event_name, "elapsed_s": round(elapsed, 2), "data": data}
                    st.session_state.stream_log.append(log_entry)
                    with log_box:
                        st.json(log_entry)

                    if event_name == "block":
                        blocks_streamed.append(data)
                        placeholder.info(f"📦 Đã nhận {len(blocks_streamed)} block. Mới nhất: `{data.get('id')}` [{data.get('type')}]")
                    elif event_name == "page_done":
                        placeholder.success(f"✓ Trang {data.get('page')} xong ({data.get('blocks_in_page')} blocks)")
                    elif event_name == "document_id":
                        doc_id = data.get("document_id")
                    elif event_name == "done":
                        st.session_state.blocks = blocks_streamed
                        st.session_state.spatial_index = data.get("spatial_index", {})
                        st.session_state.metadata = {
                            "filename": st.session_state.filename,
                            "total_pages": data.get("total_pages", 1),
                            "processing_time_ms": data.get("processing_time_ms", 0),
                            "model_used": data.get("model_used", ""),
                        }
                        st.session_state.document_id = doc_id
                        placeholder.success(f"🎉 Hoàn tất: {data.get('total_blocks')} blocks trong {data.get('processing_time_ms')}ms")
            except Exception as e:
                st.error(f"Lỗi streaming: {e}")
            st.rerun()

with col_b:
    if st.button("🎵 Phát toàn trang", use_container_width=True,
                 disabled=not st.session_state.blocks):
        url = api.tts_page_url(
            st.session_state.current_page,
            st.session_state.document_id,
            st.session_state.tts_rate,
            st.session_state.tts_pitch,
        )
        st.audio(url, format="audio/mp3", autoplay=True)

with col_c:
    if st.button("🔄 Xoá kết quả", use_container_width=True):
        for k in ("blocks", "spatial_index", "metadata", "document_id", "stream_log", "highlight_block_id"):
            st.session_state.pop(k, None)
        _init_state()
        st.rerun()


# ============================================================
# Main two-column layout
# ============================================================
if st.session_state.blocks:
    meta = st.session_state.metadata
    st.markdown(
        f"**📄 {meta.get('filename', '?')}** · "
        f"{meta.get('total_pages', '?')} trang · "
        f"{meta.get('processing_time_ms', 0)}ms · "
        f"{len(st.session_state.blocks)} blocks · "
        f"model `{meta.get('model_used', '?')}`"
    )

    left, right = st.columns([3, 2], gap="large")

    # -------- LEFT: PDF viewer + overlay --------
    with left:
        st.markdown("## 📑 Tài liệu (có overlay)")
        n_pages = max(1, meta.get("total_pages", 1))
        if n_pages > 1:
            st.session_state.current_page = st.number_input(
                "Trang", min_value=1, max_value=n_pages,
                value=st.session_state.current_page,
            )

        if st.session_state.file_bytes and not st.session_state.use_mock:
            try:
                png = render_page_png(
                    st.session_state.file_bytes,
                    st.session_state.current_page,
                )
                overlay = overlay_bounding_boxes(
                    png,
                    st.session_state.blocks,
                    st.session_state.current_page,
                    st.session_state.highlight_block_id,
                )
                st.image(overlay, caption=f"Trang {st.session_state.current_page} với bounding box các block", use_column_width=True)
            except Exception as e:
                st.warning(f"Không render được PDF: {e}")
        else:
            st.info("📋 Chế độ Mock — không có file PDF thật. Xem block list bên phải.")

    # -------- RIGHT: Block list with audio --------
    with right:
        st.markdown("## 📦 Khối nội dung")
        st.caption("Click ▶ để nghe block đó. Click 🎯 để highlight trên PDF.")

        # Filter to current page
        page_blocks = [
            b for b in st.session_state.blocks
            if b.get("coordinates", {}).get("page", 1) == st.session_state.current_page
        ]
        page_blocks.sort(key=lambda b: (b["coordinates"]["y"], b["coordinates"]["x"]))

        for block in page_blocks:
            ttype = block["type"]
            with st.container():
                st.markdown(
                    f"<div class='block-card {ttype}'>"
                    f"<span class='status-badge {ttype}'>{ttype.upper()}</span> "
                    f"<strong>{block['id']}</strong>"
                    f" <span class='block-meta'>"
                    f"📍 {block['coordinates'].get('region', '?')} "
                    f"| confidence {block.get('confidence', 0):.0%}"
                    f"</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                if block.get("latex"):
                    try:
                        st.latex(block["latex"])
                    except Exception:
                        st.code(block["latex"])

                st.markdown(f"🔊 _{block['spoken_text']}_")

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button(f"▶️ Nghe", key=f"play_{block['id']}", use_container_width=True):
                        url = api.tts_block_url(
                            block["id"],
                            st.session_state.document_id,
                            st.session_state.tts_rate,
                            st.session_state.tts_pitch,
                        )
                        st.audio(url, format="audio/mp3", autoplay=True)
                with btn_col2:
                    if st.button(f"🎯 Highlight", key=f"hi_{block['id']}", use_container_width=True):
                        st.session_state.highlight_block_id = block["id"]
                        st.rerun()
                st.divider()


# ============================================================
# Voice query section
# ============================================================
if st.session_state.blocks:
    st.markdown("---")
    st.markdown("## 🎤 Truy vấn không gian bằng giọng nói")
    st.caption("Hỏi về vị trí, loại nội dung, hoặc quan hệ không gian: \"Phía dưới biểu đồ có gì?\"")

    q_col1, q_col2 = st.columns([4, 1])
    with q_col1:
        query_text = st.text_input(
            "Câu hỏi",
            placeholder="VD: Công thức ở giữa trang là gì? / Phía dưới biểu đồ có gì?",
            label_visibility="collapsed",
            key="query_input",
        )
    with q_col2:
        ask_clicked = st.button("🔍 Hỏi", type="primary", use_container_width=True)

    # Voice recorder (optional, requires mic)
    try:
        from streamlit_mic_recorder import speech_to_text
        st.caption("🎙️ Hoặc nói câu hỏi:")
        voice_text = speech_to_text(
            language="vi",
            start_prompt="🎤 Bắt đầu nói",
            stop_prompt="🛑 Dừng",
            just_once=True,
            use_container_width=True,
            key="voice_query",
        )
        if voice_text:
            query_text = voice_text
            ask_clicked = True
    except ImportError:
        st.caption("💡 Cài `pip install streamlit-mic-recorder` để bật voice input.")

    if ask_clicked and query_text:
        with st.spinner("Đang truy vấn..."):
            try:
                result = api.query_spatial(query_text, st.session_state.document_id)
                st.session_state.query_history.append({"q": query_text, "a": result})

                st.success(f"💬 **Câu trả lời:** {result['spoken_answer']}")

                # Auto-play TTS of answer
                try:
                    audio_bytes = api.tts_speak(
                        result["spoken_answer"],
                        st.session_state.tts_rate,
                        st.session_state.tts_pitch,
                    )
                    st.audio(audio_bytes, format="audio/mp3", autoplay=True)
                except Exception as e:
                    st.warning(f"TTS lỗi: {e}")

                # Show matched blocks
                with st.expander(f"📦 {len(result['matched_blocks'])} khối khớp", expanded=True):
                    for b in result["matched_blocks"]:
                        st.markdown(
                            f"- **{b['id']}** [{b['type']}] @ {b['coordinates']['region']}: _{b['spoken_text']}_"
                        )
            except Exception as e:
                st.error(f"Lỗi truy vấn: {e}")

    # History
    if st.session_state.query_history:
        with st.expander(f"🕒 Lịch sử ({len(st.session_state.query_history)} câu)"):
            for i, entry in enumerate(reversed(st.session_state.query_history[-5:]), 1):
                st.markdown(f"**Q{i}:** {entry['q']}")
                st.markdown(f"**A:** {entry['a']['spoken_answer']}")
                st.divider()


# ============================================================
# Keyboard shortcuts hint
# ============================================================
st.markdown(
    """
    <div class='kbd-hint'>
      <strong>⌨️ Phím tắt cho người khiếm thị:</strong> &nbsp;
      <kbd>Tab</kbd> chuyển focus &nbsp;
      <kbd>Enter</kbd> kích hoạt nút &nbsp;
      <kbd>Space</kbd> phát/tạm âm thanh &nbsp;
      <kbd>↑</kbd>/<kbd>↓</kbd> điều chỉnh slider &nbsp;
      <kbd>Esc</kbd> đóng dialog
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# Footer
# ============================================================
st.caption("VisionarySTEM v2.1 · TDTU Vibe Coding 2026 · Made with ❤️ for accessibility")
