import pandas as pd
import numpy as np
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

def calculate_bollinger_bands(df: pd.DataFrame, window: int = 20, std_dev: float = 2.0) -> tuple:
    """볼린저 밴드 계산"""
    middle_band = df['close'].rolling(window=window).mean()
    rolling_std = df['close'].rolling(window=window).std()
    
    upper_band = middle_band + (rolling_std * std_dev)
    lower_band = middle_band - (rolling_std * std_dev)
    
    return lower_band, middle_band, upper_band

def fetch_recent_data(limit: int = 60) -> pd.DataFrame:
    """더 많은 데이터를 가져와서 분석의 정확성 향상"""
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

def recent_loss_within(minutes: int = 5) -> bool:
    """최근 손실 매매가 설정 시간 내에 있었는지 판단 (시간 감소)"""
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
            if roi is not None and roi < -2.0:  # 손실이 2% 이상일 때만 제한
                delta = get_kst_now() - executed_at
                if delta.total_seconds() < minutes * 60:
                    return True
        return False
    except Exception as e:
        log.error(f"[최근 손실 조회 실패] {e}")
        return False
    finally:
        conn.close()

def calculate_macd(df: pd.DataFrame) -> tuple:
    """MACD 계산"""
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal
    return macd, signal, histogram

def check_entry_signal() -> tuple:
    """진입 신호 확인 및 추천 진입 비율 반환"""
    # 최근 손실 후 일정 시간 내면 진입 제한 (시간 단축)
    if recent_loss_within(5):
        log.info("🚫 최근 큰 손실(-2% 이상) 매매 이후 5분 내 → 진입 제한")
        return False, 0

    df = fetch_recent_data(60)  # 더 많은 데이터 가져오기
    if df.empty or len(df) < 30:
        log.warning("⛔ 데이터 부족으로 매수 신호 계산 불가")
        return False, 0

    # 기술적 지표 계산
    df["ma5"] = df["close"].rolling(window=5).mean()
    df["ma10"] = df["close"].rolling(window=10).mean()
    df["ma20"] = df["close"].rolling(window=20).mean()
    df["rsi"] = calculate_rsi(df, period=14)
    df["lower_band"], df["middle_band"], df["upper_band"] = calculate_bollinger_bands(df)
    df["macd"], df["signal"], df["histogram"] = calculate_macd(df)
    
    # 변동성 및 거래량 지표
    df["volatility"] = (df["high"] - df["low"]) / df["low"]
    df["volume_ratio"] = df["volume"] / df["volume"].rolling(10).mean()
    
    # 과거 추세 분석
    df["price_change"] = df["close"].pct_change()
    df["trend"] = df["price_change"].rolling(5).sum()
    
    # 가장 최근 데이터
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 로그 출력 (향상된 분석 정보)
    log.info(f"🔍 RSI: {latest['rsi']:.2f}, MACD: {latest['macd']:.2f}, Signal: {latest['signal']:.2f}")
    log.info(f"🔍 MA5: {latest['ma5']:.2f}, MA10: {latest['ma10']:.2f}, MA20: {latest['ma20']:.2f}")
    log.info(f"🔍 볼린저밴드: Lower={latest['lower_band']:.2f}, Middle={latest['middle_band']:.2f}")
    log.info(f"🔍 가격변화: {latest['price_change']*100:.2f}%, 5분 추세: {latest['trend']*100:.2f}%")
    log.info(f"🔍 거래량비율: {latest['volume_ratio']:.2f}, 변동성: {latest['volatility']:.4f}")

    # 신호 강도 점수 시스템 (100점 만점)
    signal_strength = 0
    
    # 1. RSI 기반 과매도 조건 (최대 30점)
    if latest['rsi'] < 30:
        signal_strength += 30
    elif latest['rsi'] < 40:
        signal_strength += 20
    elif latest['rsi'] < 45:
        signal_strength += 10
    
    # 2. 볼린저 밴드 기반 (최대 20점)
    if latest['close'] < latest['lower_band']:
        signal_strength += 20
    elif latest['close'] < latest['lower_band'] * 1.01:
        signal_strength += 15
    
    # 3. MACD 기반 (최대 15점)
    if latest['histogram'] > prev['histogram'] and latest['histogram'] < 0:
        signal_strength += 15
    elif latest['macd'] > latest['signal'] and prev['macd'] < prev['signal']:
        signal_strength += 10
    
    # 4. 이동평균선 기반 (최대 15점)
    if latest['ma5'] > latest['ma10'] and prev['ma5'] <= prev['ma10']:
        signal_strength += 15
    elif latest['ma5'] > latest['ma20']:
        signal_strength += 10
    
    # 5. 추세 전환 신호 (최대 10점)
    if latest['trend'] > 0 and df.iloc[-6]['trend'] < 0:
        signal_strength += 10
    
    # 6. 거래량 분석 (최대 10점)
    if latest['volume_ratio'] > 1.5:
        signal_strength += 10
    elif latest['volume_ratio'] > 1.2:
        signal_strength += 5
    
    # 변동성 필터 - 과도한 변동성 시 감점
    if latest['volatility'] > 0.02:
        signal_strength -= 20
    elif latest['volatility'] > 0.015:
        signal_strength -= 10
    
    # 신호 강도에 따른 진입 비율 결정 (리스크 관리)
    entry_ratio = 0
    if signal_strength >= 70:  # 매우 강한 신호
        entry_ratio = 1.0  # 100% 진입
        log.info(f"✅✅✅ 매우 강한 매수 신호 (점수: {signal_strength}) → 100% 진입 권장")
        return True, entry_ratio
    elif signal_strength >= 55:  # 강한 신호
        entry_ratio = 0.7  # 70% 진입
        log.info(f"✅✅ 강한 매수 신호 (점수: {signal_strength}) → 70% 진입 권장")
        return True, entry_ratio
    elif signal_strength >= 40:  # 중간 신호
        entry_ratio = 0.5  # 50% 진입
        log.info(f"✅ 적정 매수 신호 (점수: {signal_strength}) → 50% 진입 권장")
        return True, entry_ratio
    elif signal_strength >= 30:  # 약한 신호
        entry_ratio = 0.3  # 30% 진입
        log.info(f"⚠️ 약한 매수 신호 (점수: {signal_strength}) → 30% 진입 권장")
        return True, entry_ratio
    else:
        log.info(f"❌ 매수 조건 미충족 (점수: {signal_strength})")
        return False, 0

def check_exit_signal(entry_price: float) -> bool:
    """매도 신호 확인"""
    df = fetch_recent_data()
    if df.empty or len(df) < 20:
        return False
    
    # 기술적 지표 계산
    df["rsi"] = calculate_rsi(df)
    df["ma5"] = df["close"].rolling(window=5).mean()
    df["ma10"] = df["close"].rolling(window=10).mean()
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 현재 수익률 계산
    current_roi = (latest['close'] / entry_price - 1) * 100
    
    # 로그 출력
    log.info(f"🔍 현재 수익률: {current_roi:.2f}%, RSI: {latest['rsi']:.2f}")
    
    # 매도 조건
    # 1. 목표 수익률 도달 (1.5% 이상)
    if current_roi >= 1.5:
        log.info(f"💰 목표 수익률 달성 ({current_roi:.2f}%) → 매도 신호")
        return True
    
    # 2. RSI 과매수 구간 진입
    if latest['rsi'] > 70:
        log.info(f"📈 RSI 과매수 구간 ({latest['rsi']:.2f}) → 매도 신호")
        return True
    
    # 3. 이동평균선 하향 돌파
    if latest['ma5'] < latest['ma10'] and prev['ma5'] >= prev['ma10']:
        log.info("📉 단기 이동평균선 하향 돌파 → 매도 신호")
        return True
    
    # 4. 손절 조건 (0.7% 이상 손실)
    if current_roi <= -0.7:
        log.info(f"🛑 손절 라인 도달 ({current_roi:.2f}%) → 매도 신호")
        return True
    
    return False