# app/trader.py

import pyupbit
from config import LIVE_MODE, UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY, COIN_TICKER, TRADE_AMOUNT
from app.utils.db_connect import get_connection
from app.utils.logger import get_logger
from app.utils.time_utils import get_kst_now
from app.utils.discord import send_discord_message
from app.utils.seed_tracker import get_seed, decrease_seed, increase_seed, get_holding_amount


log = get_logger()

def buy(price: float, amount: float = None, is_simulated: bool = not LIVE_MODE):
    """
    매수 함수
    
    Args:
        price: 매수 가격
        amount: 매수 수량
        is_simulated: 모의 매매 여부
    """
    # 실제 사용 금액 계산
    entry_amount = amount * price

    # 실제 매매 모드에서 잔고 확인
    if not is_simulated:
        current_seed = get_seed()
        if current_seed < entry_amount:
            log.warning(f"❌ 잔고 부족으로 매수 취소 (필요: {entry_amount}, 보유: {current_seed})")
            send_discord_message(f"❌ [실매매] 잔고 부족으로 매수 실패 (잔고: {current_seed})")
            return

    # 매수 실행
    if is_simulated:
        log.info(f"🟢 모의 매수 - 가격: {price:,.0f}, 수량: {amount:.8f}, 금액: {entry_amount:,.0f}")
        send_discord_message(f"🟢 [모의매매] 매수 - {price:,.0f}원, 수량: {amount:.8f}, 금액: {entry_amount:,.0f}")
    else:
        try:
            upbit = pyupbit.Upbit(UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY)
            resp = upbit.buy_market_order(COIN_TICKER, entry_amount)
            # 실제 매수 수량 추정
            amount = entry_amount / price  # 정확히 fill된 수량은 resp['executed_volume']이 필요함
            log.info(f"✅ 실전 매수 완료: {resp}")
            send_discord_message(f"✅ [실전매매] 매수 - {price:,.0f}원, 수량: {amount:.8f}, 금액: {entry_amount:,.0f}")
        except Exception as e:
            log.error(f"[실매수 오류] {e}")
            send_discord_message(f"❌ 실매수 실패: {e}")
            return

    # 시드 차감 - 실제 사용된 금액(entry_amount)만큼 차감
    if is_simulated or LIVE_MODE:
        new_balance = decrease_seed(entry_amount)
        log.info(f"💰 잔고 차감 후 잔액: {new_balance}원")

    # DB 저장
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                sql = """
                  INSERT INTO trade_history
                  (trade_type, price, amount, roi, executed_at, is_simulated, seed_balance)
                  VALUES ('buy', %s, %s, %s, %s, %s, %s)
                """
                executed_at = get_kst_now().strftime("%Y-%m-%d %H:%M:%S")
                current_seed = get_seed()
                cursor.execute(sql, (price, amount, None, executed_at, is_simulated, current_seed))
            conn.commit()
        except Exception as e:
            log.error(f"[매수 기록 저장 실패] {e}")
        finally:
            conn.close()


def sell(price: float, amount: float, roi: float, is_simulated: bool = not LIVE_MODE):
    """
    매도 함수
    
    Args:
        price: 매도 가격
        amount: 매도 수량
        roi: 수익률
        is_simulated: 모의 매매 여부
    """
    # 보유 수량 확인
    holding = get_holding_amount()
    if holding <= 0:
        log.warning("⚠️ 현재 보유 수량 없음 → 매도 불가")
        send_discord_message("⚠️ [매도 차단] 보유 수량이 없어 매도하지 않습니다.")
        return

    # 보유 수량 초과 매도 방지
    amount = min(amount, holding)

    # 매도 실행
    if is_simulated:
        log.info(f"🔴 모의 매도 - 가격: {price:,.0f}, 수량: {amount:.8f}, 수익률: {roi:.2%}")
        send_discord_message(f"🔴 [모의매매] 매도 - {price:,.0f}원, 수익률: {roi:.2%}")
    else:
        try:
            upbit = pyupbit.Upbit(UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY)
            resp = upbit.sell_market_order(COIN_TICKER, amount)
            log.info(f"✅ 실전 매도 완료: {resp}")
            send_discord_message(f"✅ [실전매매] 매도 - {price:,.0f}원, 수익률: {roi:.2%}")
        except Exception as e:
            log.error(f"[실매도 오류] {e}")
            send_discord_message(f"❌ 실매도 실패: {e}")
            return

    # 시드 관리 (수익 반영)
    if is_simulated or LIVE_MODE:
        # 원래 진입 금액 계산
        entry_amount = price * amount / (1 + roi)
        # 실제 회수 금액 (수익 또는 손실 포함)
        profit_amount = price * amount
        
        # 시드 증가 (회수 금액만큼)
        new_balance = increase_seed(profit_amount)
        log.info(f"💰 수익 반영 후 잔고: {new_balance}원 (ROI: {roi:.2%})")

    # DB 저장
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO trade_history
                    (trade_type, price, amount, roi, executed_at, is_simulated, seed_balance)
                    VALUES ('sell', %s, %s, %s, %s, %s, %s)
                """
                executed_at = get_kst_now().strftime("%Y-%m-%d %H:%M:%S")
                current_seed = get_seed()
                cursor.execute(sql, (price, amount, roi, executed_at, is_simulated, current_seed))
            conn.commit()
        except Exception as e:
            log.error(f"[매도 기록 저장 실패] {e}")
        finally:
            conn.close()