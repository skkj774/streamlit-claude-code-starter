import streamlit as st
import whisper
import tempfile
import os
import anthropic

st.set_page_config(page_title="栄養指導アシスタント", layout="wide")
st.title("栄養指導アシスタント")
st.caption("音声文字起こし → 要点まとめ → 病態把握・改善案 → 食事メニュー提案")

# ── サイドバー ──────────────────────────────────────────────
with st.sidebar:
    st.header("設定")
    api_key = st.text_input(
        "Anthropic API キー",
        type="password",
        help="Claude APIキーを入力してください（sk-ant-...）",
    )
    st.divider()
    model_size = st.selectbox(
        "Whisper モデルサイズ",
        options=["tiny", "base", "small", "medium"],
        index=1,
        help="小さいモデルほど速いが精度が下がります。",
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
    st.markdown("**対応フォーマット**")
    st.markdown("mp3, mp4, wav, m4a, ogg, webm, flac")


def get_claude_client():
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        st.error("サイドバーにAnthropicのAPIキーを入力してください。")
        st.stop()
    return anthropic.Anthropic(api_key=key)


# ── STEP 1: 文字起こし & 要点まとめ ────────────────────────
st.header("Step 1: 音声文字起こし & 要点まとめ")

uploaded_file = st.file_uploader(
    "音声ファイルをアップロード",
    type=["mp3", "mp4", "wav", "m4a", "ogg", "webm", "flac"],
)

if uploaded_file is not None:
    st.audio(uploaded_file)
    st.caption(f"ファイル名: {uploaded_file.name}  |  サイズ: {uploaded_file.size / 1024:.1f} KB")

    if st.button("文字起こし開始", type="primary", use_container_width=True):
        with st.spinner(f"Whisperモデル ({model_size}) を読み込み中..."):
            model = whisper.load_model(model_size)

        with st.spinner("文字起こし中..."):
            suffix = os.path.splitext(uploaded_file.name)[1] or ".mp3"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name
            try:
                result = model.transcribe(tmp_path)
                st.session_state["transcript"] = result["text"].strip()
                st.session_state["transcript_filename"] = uploaded_file.name
                st.session_state.pop("summary", None)
                st.session_state.pop("analysis", None)
                st.session_state.pop("menu", None)
            finally:
                os.unlink(tmp_path)

if "transcript" in st.session_state and st.session_state["transcript"]:
    st.subheader("文字起こし結果")
    transcript_text = st.text_area(
        label="テキスト（編集可能）",
        value=st.session_state["transcript"],
        height=250,
        key="transcript_edit",
    )
    # 編集内容をセッションに反映
    st.session_state["transcript"] = transcript_text

    col1, col2 = st.columns([1, 1])
    with col1:
        st.download_button(
            label="テキストダウンロード",
            data=transcript_text,
            file_name=f"{st.session_state.get('transcript_filename', 'transcript')}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with col2:
        st.metric("文字数", f"{len(transcript_text):,}")

    st.divider()
    if st.button("要点をまとめる（Claude）", type="primary", use_container_width=True):
        client = get_claude_client()
        with st.spinner("要点をまとめています..."):
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": f"""以下は医療・栄養指導の音声文字起こしテキストです。
患者の主訴、食習慣、生活習慣、自覚症状などを中心に、重要な要点を箇条書きで簡潔にまとめてください。

【文字起こしテキスト】
{transcript_text}

【出力形式】
- 主訴・気になること
- 食習慣・食事内容
- 生活習慣（睡眠・運動・飲酒・喫煙など）
- 自覚症状
- その他特記事項
""",
                    }
                ],
            )
            st.session_state["summary"] = response.content[0].text

if "summary" in st.session_state:
    st.subheader("要点まとめ")
    summary_text = st.text_area(
        label="要点（編集可能）",
        value=st.session_state["summary"],
        height=250,
        key="summary_edit",
    )
    st.session_state["summary"] = summary_text


# ── STEP 2: 病態把握 & 栄養改善案 ──────────────────────────
if "summary" in st.session_state:
    st.divider()
    st.header("Step 2: 病態把握 & 栄養改善案")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("検査値入力")
        st.caption("検査値を自由形式で入力してください（例: HbA1c 7.2%, LDL 145 mg/dL）")
        lab_values = st.text_area(
            label="検査値",
            placeholder="""例:
HbA1c: 7.2%
空腹時血糖: 135 mg/dL
LDL: 145 mg/dL
HDL: 42 mg/dL
中性脂肪: 210 mg/dL
AST: 38 U/L
ALT: 52 U/L
尿酸: 7.8 mg/dL
eGFR: 68 mL/min
血圧: 138/88 mmHg
BMI: 27.3""",
            height=280,
            key="lab_values_input",
        )

    with col_right:
        st.subheader("患者基本情報（任意）")
        col_a, col_b = st.columns(2)
        with col_a:
            patient_age = st.number_input("年齢", min_value=0, max_value=120, value=0, step=1)
            patient_gender = st.selectbox("性別", ["未入力", "男性", "女性"])
        with col_b:
            patient_height = st.number_input("身長 (cm)", min_value=0.0, max_value=250.0, value=0.0, step=0.1)
            patient_weight = st.number_input("体重 (kg)", min_value=0.0, max_value=300.0, value=0.0, step=0.1)
        patient_disease = st.text_input("既往歴・疾患名", placeholder="例: 2型糖尿病、高血圧")

    if st.button("病態把握・改善案を生成（Claude）", type="primary", use_container_width=True):
        if not lab_values.strip():
            st.warning("検査値を入力してください。")
        else:
            client = get_claude_client()
            basic_info = ""
            if patient_age > 0:
                basic_info += f"年齢: {patient_age}歳、"
            if patient_gender != "未入力":
                basic_info += f"性別: {patient_gender}、"
            if patient_height > 0:
                basic_info += f"身長: {patient_height}cm、"
            if patient_weight > 0:
                basic_info += f"体重: {patient_weight}kg、"
            if patient_disease:
                basic_info += f"既往歴: {patient_disease}"

            with st.spinner("病態を分析しています..."):
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=2048,
                    messages=[
                        {
                            "role": "user",
                            "content": f"""あなたは経験豊富な管理栄養士です。
以下の情報をもとに、①病態の把握、②患者の生活習慣の評価、③検査値・栄養素レベルでの改善案を提示してください。

【患者基本情報】
{basic_info if basic_info else "未入力"}

【検査値】
{lab_values}

【問診・生活習慣の要点】
{st.session_state["summary"]}

【出力形式】
## ① 病態の把握
（現在の病態・リスクを検査値から解説）

## ② 生活習慣の評価
（問診内容から読み取れる生活習慣上の課題）

## ③ 検査値・栄養素レベルでの改善案
（どの検査値を改善すべきか、そのために必要な栄養素・食事成分のターゲット値や摂取量の目安を具体的に提示）
""",
                        }
                    ],
                )
                st.session_state["analysis"] = response.content[0].text
                st.session_state["lab_values"] = lab_values

    if "analysis" in st.session_state:
        st.subheader("分析結果")
        analysis_text = st.text_area(
            label="病態把握・改善案（編集可能）",
            value=st.session_state["analysis"],
            height=400,
            key="analysis_edit",
        )
        st.session_state["analysis"] = analysis_text


# ── STEP 3: 食事メニュー・レシピ提案 ───────────────────────
if "analysis" in st.session_state:
    st.divider()
    st.header("Step 3: 食事メニュー・レシピ提案")

    col1, col2 = st.columns([1, 1])
    with col1:
        meal_days = st.selectbox("提案する日数", [1, 3, 7], index=1, format_func=lambda x: f"{x}日分")
    with col2:
        dietary_restriction = st.text_input(
            "食事制限・アレルギー・好み（任意）",
            placeholder="例: 魚介アレルギー、和食中心、辛いものが苦手",
        )

    if st.button("食事メニュー・レシピを提案（Claude）", type="primary", use_container_width=True):
        client = get_claude_client()
        restriction_text = f"\n【食事制限・アレルギー・好み】\n{dietary_restriction}" if dietary_restriction else ""

        with st.spinner("食事メニューを考案しています..."):
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": f"""あなたは経験豊富な管理栄養士です。
以下の病態把握・改善案をもとに、患者に適した{meal_days}日分の具体的な食事メニューとレシピを提案してください。{restriction_text}

【病態把握・栄養改善案】
{st.session_state["analysis"]}

【出力形式】
各日について、朝食・昼食・夕食（＋間食があれば）を提案し、それぞれ以下を含めてください：
- メニュー名
- 主な食材
- 簡単な調理ポイント（2〜3行）
- その食事が改善案のどの点に対応しているか（1行）

最後に「1日の栄養バランスのポイント」を簡潔にまとめてください。
""",
                    }
                ],
            )
            st.session_state["menu"] = response.content[0].text

    if "menu" in st.session_state:
        st.subheader("提案メニュー")
        st.markdown(st.session_state["menu"])

        st.download_button(
            label="メニュー提案をダウンロード",
            data=st.session_state["menu"],
            file_name="meal_plan.txt",
            mime="text/plain",
            use_container_width=True,
        )
