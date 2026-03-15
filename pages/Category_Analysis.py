import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="カテゴリ分析", layout="wide")
st.title("商品カテゴリ別 売上分析")

@st.cache_data
def load_data():
    order_items = pd.read_csv("sample_data/order_items.csv", parse_dates=["created_at", "shipped_at", "delivered_at", "returned_at"])
    products = pd.read_csv("sample_data/products.csv")
    df = order_items.merge(
        products[["id", "category", "department", "brand", "retail_price", "cost"]],
        left_on="product_id",
        right_on="id",
        how="left"
    )
    df["profit"] = df["sale_price"] - df["cost"]
    df["month"] = df["created_at"].dt.to_period("M").astype(str)
    return df

df = load_data()

# --- サイドバー フィルター ---
st.sidebar.header("フィルター")

departments = ["すべて"] + sorted(df["department"].dropna().unique().tolist())
selected_dept = st.sidebar.selectbox("デパートメント", departments)

statuses = ["すべて"] + sorted(df["status"].dropna().unique().tolist())
selected_status = st.sidebar.selectbox("ステータス", statuses)

filtered = df.copy()
if selected_dept != "すべて":
    filtered = filtered[filtered["department"] == selected_dept]
if selected_status != "すべて":
    filtered = filtered[filtered["status"] == selected_status]

# --- KPI ---
st.header("KPI サマリー")
total_sales = filtered["sale_price"].sum()
total_items = len(filtered)
avg_price = filtered["sale_price"].mean()
total_profit = filtered["profit"].sum()
profit_margin = total_profit / total_sales * 100 if total_sales > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("総売上", f"¥{total_sales:,.0f}")
col2.metric("総アイテム数", f"{total_items:,}")
col3.metric("平均単価", f"¥{avg_price:,.0f}")
col4.metric("利益率", f"{profit_margin:.1f}%")

st.divider()

# --- 1. カテゴリ別売上ランキング ---
st.header("1. カテゴリ別 売上ランキング")

cat_sales = (
    filtered.groupby("category")
    .agg(売上合計=("sale_price", "sum"), 販売数=("id_x", "count"), 平均単価=("sale_price", "mean"))
    .sort_values("売上合計", ascending=False)
    .reset_index()
)

col1, col2 = st.columns(2)
with col1:
    fig_bar = px.bar(
        cat_sales.head(15),
        x="売上合計", y="category",
        orientation="h",
        title="カテゴリ別 売上合計 (Top 15)",
        color="売上合計",
        color_continuous_scale="Blues",
        text_auto=".2s"
    )
    fig_bar.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    fig_scatter = px.scatter(
        cat_sales,
        x="販売数", y="売上合計",
        size="平均単価", color="category",
        hover_name="category",
        title="販売数 vs 売上合計（バブルサイズ=平均単価）"
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()

# --- 2. カテゴリ別 利益率 ---
st.header("2. カテゴリ別 利益率")

cat_profit = (
    filtered.groupby("category")
    .agg(売上合計=("sale_price", "sum"), 利益合計=("profit", "sum"))
    .assign(利益率=lambda x: x["利益合計"] / x["売上合計"] * 100)
    .sort_values("利益率", ascending=False)
    .reset_index()
)

fig_profit = px.bar(
    cat_profit,
    x="category", y="利益率",
    title="カテゴリ別 利益率 (%)",
    color="利益率",
    color_continuous_scale="RdYlGn",
    text_auto=".1f"
)
fig_profit.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig_profit, use_container_width=True)

st.divider()

# --- 3. 月別カテゴリ売上推移 ---
st.header("3. 月別カテゴリ売上推移")

top_categories = cat_sales.head(8)["category"].tolist()
selected_categories = st.multiselect(
    "表示カテゴリを選択",
    options=cat_sales["category"].tolist(),
    default=top_categories
)

if selected_categories:
    monthly = (
        filtered[filtered["category"].isin(selected_categories)]
        .groupby(["month", "category"])["sale_price"]
        .sum()
        .reset_index()
    )
    fig_trend = px.line(
        monthly, x="month", y="sale_price", color="category",
        title="月別カテゴリ売上推移", markers=True
    )
    fig_trend.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_trend, use_container_width=True)

st.divider()

# --- 4. デパートメント別分析 ---
st.header("4. デパートメント別分析")

col1, col2 = st.columns(2)
with col1:
    dept_sales = (
        filtered.groupby("department")["sale_price"].sum().reset_index()
    )
    dept_sales.columns = ["department", "売上合計"]
    fig_dept = px.pie(dept_sales, names="department", values="売上合計", title="デパートメント別 売上比率")
    st.plotly_chart(fig_dept, use_container_width=True)

with col2:
    dept_cat = (
        filtered.groupby(["department", "category"])["sale_price"]
        .sum()
        .reset_index()
        .sort_values("sale_price", ascending=False)
    )
    fig_treemap = px.treemap(
        dept_cat, path=["department", "category"], values="sale_price",
        title="デパートメント × カテゴリ 売上ツリーマップ"
    )
    st.plotly_chart(fig_treemap, use_container_width=True)

st.divider()

# --- 5. ブランド別売上 Top10 ---
st.header("5. ブランド別 売上 Top 10")

brand_sales = (
    filtered.groupby("brand")["sale_price"].sum()
    .sort_values(ascending=False)
    .head(10)
    .reset_index()
)
brand_sales.columns = ["brand", "売上合計"]

fig_brand = px.bar(
    brand_sales, x="brand", y="売上合計",
    title="ブランド別 売上合計 (Top 10)",
    color="売上合計", color_continuous_scale="Purples", text_auto=".2s"
)
fig_brand.update_layout(coloraxis_showscale=False)
st.plotly_chart(fig_brand, use_container_width=True)

st.divider()

# --- データテーブル ---
with st.expander("カテゴリ別集計データ"):
    st.dataframe(cat_sales, use_container_width=True)
