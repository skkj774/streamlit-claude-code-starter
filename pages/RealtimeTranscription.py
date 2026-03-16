import hashlib
import tempfile
import os
from datetime import datetime

import streamlit as st
import whisper

st.set_page_config(page_title="リアルタイム会話文字起こし", layout="wide")
st.title("リアルタイム会話文字起こし")
st.caption("2名の会話を交互に録音しながらリアルタイムで文字起こしします。")

# ── サイドバー ──────────────────────────────────────────────
with st.sidebar:
    st.header("設定")
    speaker_a_name = st.text_input("話者Aの名前", value="話者A")
    speaker_b_name = st.text_input("話者Bの名前", value="話者B")
    st.divider()
    model_size = st.selectbox(
        "Whisper モデルサイズ",
        options=["tiny", "base", "small", "medium"],
        index=0,
        help="会話録音はtiny/baseが応答速度の面でおすすめです。",
    )
    st.markdown("""
| モデル | サイズ | 速度 |
|--------|--------|------|
| tiny   | 39 MB  | 最速 |
| base   | 74 MB  | 速い |
| small  | 244 MB | 普通 |
| medium | 769 MB | 遅い |
""")
    st.divider()
    language = st.selectbox(
        "言語",
        options=["ja", "en", "auto"],
        index=0,
        format_func=lambda x: {"ja": "日本語", "en": "English", "auto": "自動検出"}[x],
    )
    st.divider()
    if st.button("会話ログをクリア", use_container_width=True, type="secondary"):
        st.session_state["conversation"] = []
        st.session_state.pop("last_hash_a", None)
        st.session_state.pop("last_hash_b", None)
        st.rerun()


# ── Whisper モデルのキャッシュ ──────────────────────────────
@st.cache_resource(show_spinner="Whisperモデルを読み込み中...")
def load_whisper_model(size: str):
    return whisper.load_model(size)


def transcribe_audio(audio_bytes: bytes, lang: str) -> str:
    suffix = ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        model = load_whisper_model(model_size)
        kwargs = {} if lang == "auto" else {"language": lang}
        result = model.transcribe(tmp_path, **kwargs)
        return result["text"].strip()
    finally:
        os.unlink(tmp_path)


def audio_hash(audio) -> str | None:
    if audio is None:
        return None
    audio.seek(0)
    return hashlib.md5(audio.read()).hexdigest()


# ── セッション初期化 ────────────────────────────────────────
if "conversation" not in st.session_state:
    st.session_state["conversation"] = []

# ── 録音エリア（2カラム） ───────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader(f"🎙️ {speaker_a_name}")
    audio_a = st.audio_input("録音", key="audio_a", label_visibility="collapsed")
    status_a = st.empty()

with col_b:
    st.subheader(f"🎙️ {speaker_b_name}")
    audio_b = st.audio_input("録音", key="audio_b", label_visibility="collapsed")
    status_b = st.empty()

# ── 新規録音の検出 & 文字起こし ────────────────────────────
def process_audio(audio, speaker_name: str, hash_key: str, status_placeholder):
    if audio is None:
        return
    h = audio_hash(audio)
    if h == st.session_state.get(hash_key):
        return

    st.session_state[hash_key] = h
    audio.seek(0)
    audio_bytes = audio.read()

    with status_placeholder:
        with st.spinner("文字起こし中..."):
            text = transcribe_audio(audio_bytes, language)

    if text:
        st.session_state["conversation"].append(
            {
                "speaker": speaker_name,
                "text": text,
                "time": datetime.now().strftime("%H:%M:%S"),
            }
        )
        st.rerun()


process_audio(audio_a, speaker_a_name, "last_hash_a", status_a)
process_audio(audio_b, speaker_b_name, "last_hash_b", status_b)

# ── 会話ログ ────────────────────────────────────────────────
st.divider()
st.subheader("会話ログ")

conversation = st.session_state["conversation"]

if not conversation:
    st.info("録音ボタンを押して話し、停止すると自動で文字起こしされます。")
else:
    # 色分け（話者A=青、話者B=緑、その他=グレー）
    def speaker_color(name: str) -> str:
        if name == speaker_a_name:
            return "#1f77b4"
        if name == speaker_b_name:
            return "#2ca02c"
        return "#888888"

    # 会話表示
    for entry in conversation:
        color = speaker_color(entry["speaker"])
        st.markdown(
            f"""<div style="
                margin: 6px 0;
                padding: 10px 14px;
                border-left: 4px solid {color};
                background: #f8f9fa;
                border-radius: 0 6px 6px 0;
            ">
            <span style="font-size:0.75rem; color:#888;">{entry['time']}</span>
            &nbsp;
            <span style="font-weight:bold; color:{color};">{entry['speaker']}</span>
            <br>
            <span style="font-size:1rem;">{entry['text']}</span>
            </div>""",
            unsafe_allow_html=True,
        )

    st.divider()

    # テキスト形式でエクスポート
    export_text = "\n".join(
        f"[{e['time']}] {e['speaker']}: {e['text']}" for e in conversation
    )
    col1, col2 = st.columns([2, 1])
    with col1:
        st.download_button(
            label="会話ログをダウンロード (.txt)",
            data=export_text,
            file_name=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with col2:
        st.metric("発言数", len(conversation))
