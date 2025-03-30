# app/db_1min_btc.py

import pyupbit
from app.utils.db_connect import get_connection
from app.utils.time_utils import get_kst_now
from app.utils.logger import get_logger

log = get_logger()

def save_1min_btc_to_db(limit: int = 3):
    """
    최신 1분봉 데이터 n개를 pyupbit에서 가져와 DB에 저장
    :param limit: 몇 개의 1분봉을 가져올지 (기본 3개)
    """
    try:
        df = pyupbit.get_ohlcv("KRW-BTC", interval="minute1", count=limit)
        if df is None or df.empty:
            log.warning("📉 1분봉 데이터가 없습니다.")
            return

        conn = get_connection()
        if not conn:
            return

        with conn.cursor() as cursor:
            for timestamp, row in df.iterrows():
                sql = """
                    INSERT IGNORE INTO btc_price_1min
                    (timestamp, open, high, low, close, volume, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """
                cursor.execute(sql, (
                    timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    row['open'],
                    row['high'],
                    row['low'],
                    row['close'],
                    row['volume']
                ))

        log.info(f"✅ 1분봉 데이터 {limit}개 저장 완료")
    except Exception as e:
        log.error(f"[save_1min_btc_to_db 에러] {e}")
    finally:
        if 'conn' in locals():
            conn.close()

