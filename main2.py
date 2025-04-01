import time
import pyupbit
from app.db_1min_btc import save_1min_btc_to_db
from app.strategy2 import check_entry_signal, check_exit_signal
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

def has_open_position():
    """현재 열린 포지션이 있는지 확인"""
    conn = get_connection()
    if not conn:
        return False, None, None
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT trade_type, price, amount FROM trade_history
                ORDER BY executed_at DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            
            if not row or row[0] == 'sell':
                return False, None, None
            
            # 마지막 거래가 매수면 해당 가격과 수량 반환
            return True, row[1], row[2]
    except Exception as e:
        log.error(f"[포지션 확인 실패] {e}")
        return False, None, None
    finally:
        conn.close()

# def get_current_price():
#     """현재 가격 조회 함수"""
#     # 여기에 현재 가격을 가져오는 로직 구현
#     # 예: pyupbit.get_current_price("KRW-BTC")
#     # 임시로 최근 데이터에서 가져온다고 가정
#     from app.strategy import fetch_recent_data
#     df = fetch_recent_data(1)
#     if not df.empty:
#         return df['close'].iloc[-1]
#     return None

def start_loop():
    log.info("📈 자동매매 시작")
    send_discord_message("📈 자동매매 시작됨 (main.py)")

    # ✅ 최초 실행 시 30개 강제 저장
    if not is_btc_data_sufficient():
        log.info("📥 BTC 1분봉 데이터 부족 → 30개 강제 저장")
        save_1min_btc_to_db(limit=60)
        time.sleep(1)

    # 메인 루프
    while True:
        # try:
        # 현재 포지션 확인
        has_position, entry_price, position_amount = has_open_position()
        
        if not has_position:
            # 포지션이 없을 때 진입 신호 확인
            should_enter, entry_ratio = check_entry_signal()
            
            if should_enter:
                # 진입 비율에 따라 거래 금액 계산
                entry_amount = TRADE_AMOUNT * entry_ratio
                
                # 현재 가격 조회
                current_price = get_current_price()
                if current_price:
                    # 수량 계산
                    coin_amount = entry_amount / current_price
                    
                    # 매수 실행
                    buy(entry_amount, coin_amount)
                    log.info(f"매수 실행: {entry_amount}원 ({entry_ratio*100}% 진입)")
        else:
            # 포지션이 있을 때 청산 신호 확인
            should_exit = check_exit_signal(entry_price)
            
            if should_exit:
                current_price = get_current_price()
                if current_price and entry_price:
                    # ROI 계산
                    roi = (current_price / entry_price) - 1
                    
                    # 매도 실행
                    sell(current_price, position_amount, roi)
                    log.info(f"매도 실행: {current_price}원, ROI: {roi:.2%}")
                    
        # 4. 60초 대기
        time.sleep(60)

        # except Exception as e:
        #     log.error(f"[감시 루프 오류] {e}")
        #     send_discord_message(f"❌ 감시 루프 오류 발생: {e}")
        #     time.sleep(60)

if __name__ == "__main__":
    start_loop()
