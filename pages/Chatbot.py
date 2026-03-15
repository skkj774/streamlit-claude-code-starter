import streamlit as st
import pandas as pd
import anthropic

st.set_page_config(page_title="データ分析チャットボット", layout="wide")
st.title("データ分析チャットボット")
st.caption("注文・ユーザー・商品データについて質問してください。")

# サイドバーでAPIキーを設定
with st.sidebar:
    st.header("設定")
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="sk-ant-...",
        value=st.session_state.get("anthropic_api_key", ""),
        help="Anthropic ConsoleからAPIキーを取得してください。",
    )
    if api_key:
        st.session_state["anthropic_api_key"] = api_key
        st.success("APIキーが設定されました")
    else:
        st.warning("APIキーを入力してください")

@st.cache_data
def load_data():
    orders = pd.read_csv("sample_data/orders.csv")
    users = pd.read_csv("sample_data/users.csv")
    order_items = pd.read_csv("sample_data/order_items.csv")
    products = pd.read_csv("sample_data/products.csv")
    return orders, users, order_items, products

orders_df, users_df, order_items_df, products_df = load_data()

def build_system_prompt():
    def df_summary(df, name):
        return (
            f"## {name}\n"
            f"- 行数: {len(df):,}\n"
            f"- カラム: {', '.join(df.columns.tolist())}\n"
            f"- サンプル（先頭3行）:\n{df.head(3).to_string(index=False)}\n"
        )

    order_status = orders_df["status"].value_counts().to_string()
    category_sales = (
        order_items_df.merge(products_df[["id", "category"]], left_on="product_id", right_on="id", how="left")
        .groupby("category")["sale_price"].sum()
        .sort_values(ascending=False)
        .head(10)
        .to_string()
    )
    top_countries = users_df["country"].value_counts().head(5).to_string()
    traffic_sources = users_df["traffic_source"].value_counts().to_string()

    return f"""あなたはECサイトのデータアナリストです。以下のデータセットに基づいて、ユーザーの質問に日本語で回答してください。

# データセット概要

{df_summary(orders_df, "orders（注文データ）")}
{df_summary(users_df, "users（ユーザーデータ）")}
{df_summary(order_items_df, "order_items（注文アイテムデータ）")}
{df_summary(products_df, "products（商品データ）")}

# 主要な統計情報

## 注文ステータス別件数
{order_status}

## カテゴリ別売上合計（Top 10）
{category_sales}

## 国別ユーザー数（Top 5）
{top_countries}

## 流入経路別ユーザー数
{traffic_sources}

# 回答のガイドライン
- データに基づいた具体的な数値を含めて回答してください
- 不明な場合は正直に「データからは判断できません」と伝えてください
- 分析の示唆や改善提案も積極的に行ってください
"""

# セッション状態の初期化
if "messages" not in st.session_state:
    st.session_state.messages = []

# チャット履歴の表示
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ユーザー入力
if prompt := st.chat_input("データについて質問してください（例：どのカテゴリの売上が一番高いですか？）"):
    if not st.session_state.get("anthropic_api_key"):
        st.error("サイドバーにAPIキーを入力してください。")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("考え中..."):
            client = anthropic.Anthropic(api_key=st.session_state["anthropic_api_key"])
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=1024,
                system=build_system_prompt(),
                messages=st.session_state.messages,
            )
            answer = response.content[0].text

        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})

# 会話リセットボタン
if st.session_state.messages:
    if st.button("会話をリセット"):
        st.session_state.messages = []
        st.rerun()
