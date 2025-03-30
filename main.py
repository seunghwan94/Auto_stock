import time
import pyupbit
from app.db_1min_btc import save_1min_btc_to_db
from app.strategy import check_entry_signal
from app.trader import buy, sell
from app.utils.logger import get_logger
from app.utils.discord import send_discord_message
from app.utils.db_connect import get_connection
from app.utils.seed_tracker import get_seed  # ✅ 시드 확인용 추가
from config import TRADE_AMOUNT, TAKE_PROFIT, STOP_LOSS, COIN_TICKER

log = get_logger()

def get_current_price():
    try:
        return pyupbit.get_current_price(COIN_TICKER)
    except Exception as e:
        log.error(f"[현재가 조회 실패] {e}")
        return None

def get_last_buy():
    conn = get_connection()
    if not conn:
        return None

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT price, amount, executed_at
                FROM trade_history
                WHERE trade_type = 'buy'
                ORDER BY executed_at DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return {
                    "price": row[0],
                    "amount": row[1],
                    "executed_at": row[2]
                }
        return None
    except Exception as e:
        log.error(f"[최근 매수 조회 실패] {e}")
        return None
    finally:
        conn.close()

def is_btc_data_sufficient():
    conn = get_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM btc_price_1min")
            count = cursor.fetchone()[0]
            return count >= 20
    except Exception as e:
        log.error(f"[btc_price_1min 카운트 조회 실패] {e}")
        return False
    finally:
        conn.close()

def start_loop():
    log.info("📈 자동매매 시작")
    send_discord_message("📈 자동매매 시작됨 (main.py)")

    # ✅ 최초 실행 시 30개 강제 저장
    if not is_btc_data_sufficient():
        log.info("📥 BTC 1분봉 데이터 부족 → 30개 강제 저장")
        save_1min_btc_to_db(limit=30)
        time.sleep(1)

    while True:
        try:
            # 1. 데이터 저장 (최근 3개)
            save_1min_btc_to_db(limit=3)

            # 2. 익절/손절 체크
            buy_info = get_last_buy()
            if buy_info:
                current_price = get_current_price()
                if current_price:
                    buy_price = buy_info["price"]
                    roi = (current_price - buy_price) / buy_price

                    if roi >= TAKE_PROFIT:
                        sell(current_price, buy_info["amount"], roi)
                        time.sleep(60)
                        continue
                    elif roi <= STOP_LOSS:
                        sell(current_price, buy_info["amount"], roi)
                        time.sleep(60)
                        continue

            # 3. 매수 조건 판단
            if check_entry_signal():
                # ✅ 현재 시드가 충분한지 확인
                seed = get_seed()
                if seed >= TRADE_AMOUNT:
                    current_price = get_current_price()
                    if current_price:
                        amount = TRADE_AMOUNT / current_price
                        buy(current_price, round(amount, 8))  # 소수점 8자리 제한
                else:
                    log.info(f"⚠️ 시드 부족으로 매수 스킵 (잔고: {seed}원)")

            # 4. 60초 대기
            time.sleep(60)

        except Exception as e:
            log.error(f"[감시 루프 오류] {e}")
            send_discord_message(f"❌ 감시 루프 오류 발생: {e}")
            time.sleep(60)

if __name__ == "__main__":
    start_loop()
