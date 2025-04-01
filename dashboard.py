import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from app.utils.db_connect import get_connection
from app.utils.seed_tracker import get_seed
from datetime import datetime

st.set_page_config(page_title="BTC 자동매매 대시보드", layout="wide")
st.title("📊 비트코인 자동매매 대시보드")

# 시드 잔고 표시
seed = get_seed()
st.metric("💰 현재 시드 잔고", f"{seed:,} 원")

# 누적 수익률 계산 함수
def get_total_roi():
    conn = get_connection()
    if not conn:
        return 0.0
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT roi FROM trade_history WHERE roi IS NOT NULL")
            rows = cursor.fetchall()
            if not rows:
                return 0.0
            total_roi = sum(r[0] for r in rows)
            return total_roi
    except Exception as e:
        st.error(f"[누적 수익률 조회 실패] {e}")
        return 0.0
    finally:
        conn.close()

# 누적 수익률 표시
st.metric("📈 누적 수익률", f"{get_total_roi():.2%}")

# 거래 시점이 표시된 시세 차트
def plot_trade_chart():
    conn = get_connection()
    if not conn:
        return
    try:
        df = pd.read_sql("SELECT * FROM btc_price_1min ORDER BY timestamp DESC LIMIT 60", conn)
        df = df.sort_values("timestamp")

        trades = pd.read_sql("SELECT * FROM trade_history ORDER BY executed_at DESC LIMIT 30", conn)

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='BTC 시세'
        ))

        # 거래 시점 표시
        for _, row in trades.iterrows():
            color = "green" if row['trade_type'] == 'buy' else "red"
            fig.add_trace(go.Scatter(
                x=[row['executed_at']],
                y=[row['price']],
                mode="markers+text",
                marker=dict(color=color, size=10),
                name=row['trade_type'],
                text=[row['trade_type']],
                textposition="top center"
            ))

        fig.update_layout(title="BTC 시세 + 거래 시점", xaxis_title="시간", yaxis_title="가격")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"[차트 로딩 실패] {e}")
    finally:
        conn.close()

# 최근 거래 내역 테이블
def show_trade_history():
    conn = get_connection()
    if not conn:
        return
    try:
        df = pd.read_sql("SELECT * FROM trade_history ORDER BY executed_at DESC LIMIT 20", conn)
        df['executed_at'] = pd.to_datetime(df['executed_at']).dt.strftime("%Y-%m-%d %H:%M")
        st.subheader("🧾 최근 거래 내역")
        st.dataframe(df)
    except Exception as e:
        st.error(f"[거래 내역 로딩 실패] {e}")
    finally:
        conn.close()

# 대시보드 표시
st.divider()
plot_trade_chart()
st.divider()
show_trade_history()
