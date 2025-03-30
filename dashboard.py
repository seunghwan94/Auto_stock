
import streamlit as st
import pandas as pd
import pymysql
from config import DB_CONFIG
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="📊 BTC 자동매매 대시보드", layout="wide")
st.title("📈 BTC 자동매매 대시보드")

# DB 연결 함수
@st.cache_resource
def get_connection():
    return pymysql.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        db=DB_CONFIG['database'],
        charset='utf8mb4',
        autocommit=True
    )

conn = get_connection()

# 최근 시드 잔고
def get_latest_seed():
    with conn.cursor() as cursor:
        cursor.execute("SELECT seed_balance FROM trade_history ORDER BY executed_at DESC LIMIT 1")
        result = cursor.fetchone()
        return int(result[0]) if result else None

# 누적 수익률
def get_total_roi():
    with conn.cursor() as cursor:
        cursor.execute("SELECT roi FROM trade_history WHERE roi IS NOT NULL")
        rows = cursor.fetchall()
        total = sum([r[0] for r in rows])
        return total

# 최근 거래 내역
def get_trade_history(limit=20):
    with conn.cursor() as cursor:
        cursor.execute(f"""
            SELECT trade_type, price, amount, roi, executed_at, is_simulated, seed_balance
            FROM trade_history
            ORDER BY executed_at DESC
            LIMIT {limit}
        """)
        rows = cursor.fetchall()
        df = pd.DataFrame(rows, columns=["Type", "Price", "Amount", "ROI", "Executed At", "Simulated", "Seed"])
        return df

# 월별 수익
def get_monthly_returns():
    with conn.cursor() as cursor:
        cursor.execute("SELECT executed_at, roi FROM trade_history WHERE roi IS NOT NULL")
        rows = cursor.fetchall()
        df = pd.DataFrame(rows, columns=["executed_at", "roi"])
        df["executed_at"] = pd.to_datetime(df["executed_at"])
        df["month"] = df["executed_at"].dt.to_period("M").astype(str)
        monthly = df.groupby("month")["roi"].sum().reset_index()
        return monthly

# 실시간 시드 및 수익률 표시
col1, col2 = st.columns(2)
with col1:
    st.metric("💰 현재 시드 잔고", f"{get_latest_seed():,} 원")
with col2:
    st.metric("📈 누적 수익률", f"{get_total_roi():.2%}")

st.markdown("---")

# 거래 내역 테이블
st.subheader("📋 최근 거래 내역")
history_df = get_trade_history()
st.dataframe(history_df, use_container_width=True)

# 수익률 그래프
st.subheader("📊 월별 누적 수익률")
monthly_df = get_monthly_returns()
fig = px.bar(monthly_df, x="month", y="roi", text="roi", title="월별 수익률")
st.plotly_chart(fig, use_container_width=True)
