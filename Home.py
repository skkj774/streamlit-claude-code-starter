import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Streamlit BI x Claude Code Starter", layout="wide")

st.title("Streamlit BI x Claude Code Starter")

@st.cache_data
def load_data():
    orders_df = pd.read_csv("sample_data/orders.csv", parse_dates=["created_at", "returned_at", "shipped_at", "delivered_at"])
    users_df = pd.read_csv("sample_data/users.csv", parse_dates=["created_at"])
    return orders_df, users_df

orders_df, users_df = load_data()

# --- 1. KPIサマリー ---
st.header("KPI サマリー")
total_orders = len(orders_df)
complete_orders = len(orders_df[orders_df["status"] == "Complete"])
cancelled_orders = len(orders_df[orders_df["status"] == "Cancelled"])
returned_orders = len(orders_df[orders_df["status"] == "Returned"])
total_users = len(users_df)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("総注文数", f"{total_orders:,}")
col2.metric("完了注文", f"{complete_orders:,}")
col3.metric("キャンセル率", f"{cancelled_orders / total_orders * 100:.1f}%")
col4.metric("返品率", f"{returned_orders / total_orders * 100:.1f}%")
col5.metric("総ユーザー数", f"{total_users:,}")

st.divider()

# --- 2. 注文ステータス分析 ---
st.header("1. 注文ステータス分析")
status_counts = orders_df["status"].value_counts().reset_index()
status_counts.columns = ["status", "count"]
fig_status = px.pie(status_counts, names="status", values="count", title="ステータス別注文割合")
st.plotly_chart(fig_status, use_container_width=True)

st.divider()

# --- 3. 時系列トレンド分析 ---
st.header("2. 時系列トレンド分析")

col1, col2 = st.columns(2)

with col1:
    orders_monthly = orders_df.groupby(orders_df["created_at"].dt.to_period("M")).size().reset_index()
    orders_monthly.columns = ["month", "count"]
    orders_monthly["month"] = orders_monthly["month"].astype(str)
    fig_orders_trend = px.line(orders_monthly, x="month", y="count", title="月別注文数推移", markers=True)
    st.plotly_chart(fig_orders_trend, use_container_width=True)

with col2:
    users_monthly = users_df.groupby(users_df["created_at"].dt.to_period("M")).size().reset_index()
    users_monthly.columns = ["month", "count"]
    users_monthly["month"] = users_monthly["month"].astype(str)
    fig_users_trend = px.line(users_monthly, x="month", y="count", title="月別ユーザー登録数推移", markers=True)
    st.plotly_chart(fig_users_trend, use_container_width=True)

st.divider()

# --- 4. ユーザー属性分析 ---
st.header("3. ユーザー属性分析")

col1, col2, col3 = st.columns(3)

with col1:
    country_counts = users_df["country"].value_counts().head(10).reset_index()
    country_counts.columns = ["country", "count"]
    fig_country = px.bar(country_counts, x="count", y="country", orientation="h", title="国別ユーザー数 (Top 10)")
    fig_country.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_country, use_container_width=True)

with col2:
    fig_age = px.histogram(users_df, x="age", nbins=20, title="年齢分布")
    st.plotly_chart(fig_age, use_container_width=True)

with col3:
    gender_counts = users_df["gender"].value_counts().reset_index()
    gender_counts.columns = ["gender", "count"]
    fig_gender = px.pie(gender_counts, names="gender", values="count", title="性別比率")
    st.plotly_chart(fig_gender, use_container_width=True)

st.divider()

# --- 5. 流入経路分析 ---
st.header("4. 流入経路分析")
traffic_counts = users_df["traffic_source"].value_counts().reset_index()
traffic_counts.columns = ["traffic_source", "count"]
fig_traffic = px.bar(traffic_counts, x="traffic_source", y="count", title="流入経路別ユーザー数", color="traffic_source")
st.plotly_chart(fig_traffic, use_container_width=True)

st.divider()

# --- 6. ユーザー × 注文 クロス分析 ---
st.header("5. ユーザー × 注文 クロス分析")

orders_per_user = orders_df.groupby("user_id").size().reset_index(name="order_count")
avg_orders = orders_per_user["order_count"].mean()
st.metric("1ユーザーあたりの平均注文数", f"{avg_orders:.2f}")

col1, col2 = st.columns(2)

with col1:
    fig_order_dist = px.histogram(orders_per_user, x="order_count", nbins=15, title="ユーザーあたりの注文数分布")
    st.plotly_chart(fig_order_dist, use_container_width=True)

with col2:
    gender_status = orders_df.groupby(["gender", "status"]).size().reset_index(name="count")
    fig_gender_status = px.bar(gender_status, x="status", y="count", color="gender", barmode="group", title="性別 × ステータス別注文数")
    st.plotly_chart(fig_gender_status, use_container_width=True)

st.divider()

# --- データプレビュー ---
with st.expander("データプレビュー"):
    st.subheader("Orders Data (Top 10 rows)")
    st.dataframe(orders_df.head(10))
    st.subheader("Users Data (Top 10 rows)")
    st.dataframe(users_df.head(10))
