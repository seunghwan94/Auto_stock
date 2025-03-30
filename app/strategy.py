# app/strategy.py

import pandas as pd
from app.utils.db_connect import get_connection
from app.utils.logger import get_logger
from app.utils.time_utils import get_kst_now

log = get_logger()

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()

    rs = avg_gain / (avg_loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def fetch_recent_data(limit: int = 20) -> pd.DataFrame:
    conn = get_connection()
    if not conn:
        return pd.DataFrame()

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT timestamp, open, high, low, close, volume
                FROM btc_price_1min
                ORDER BY timestamp DESC
                LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()

        df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df
    except Exception as e:
        log.error(f"[데이터 불러오기 실패] {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def recent_loss_within(minutes: int = 10) -> bool:
    """
    최근 손실 매매가 설정 시간 내에 있었는지 판단
    """
    conn = get_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT roi, executed_at FROM trade_history
                WHERE trade_type = 'buy'
                ORDER BY executed_at DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if not row:
                return False

            roi, executed_at = row
            if roi is not None and roi < 0:
                delta = get_kst_now() - executed_at
                if delta.total_seconds() < minutes * 60:
                    return True
        return False
    except Exception as e:
        log.error(f"[최근 손실 조회 실패] {e}")
        return False
    finally:
        conn.close()

def check_entry_signal() -> bool:
    # 최근 손실 후 일정 시간 내면 진입 제한
    if recent_loss_within(10):
        log.info("🚫 최근 손실 매매 이후 10분 내 → 진입 제한")
        return False

    df = fetch_recent_data()
    if df.empty or len(df) < 16:
        log.warning("⛔ 데이터 부족으로 매수 신호 계산 불가")
        return False

    df["ma3"] = df["close"].rolling(window=3).mean()
    df["ma15"] = df["close"].rolling(window=15).mean()
    df["rsi"] = calculate_rsi(df)
    df["volatility"] = (df["close"] - df["open"]).abs() / df["open"]
    df["volume_ma10"] = df["volume"].rolling(10).mean()

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # 변동성 필터
    if latest['volatility'] > 0.015:
        log.info("⚠️ 변동성 과다 → 진입 제한")
        return False

    # 강화된 전략 조건
    condition = (
        latest['rsi'] < 35 and
        latest['ma3'] >= latest['ma15'] and
        latest['close'] > latest['open'] * 1.001 and
        prev['close'] < prev['open'] and
        latest['volume'] > latest['volume_ma10']
    )

    if condition:
        log.info("✅ 매수 조건 충족")
        return True
    else:
        log.info("❌ 매수 조건 미충족")
        return False
