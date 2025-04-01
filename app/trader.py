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
    if not is_simulated:
        # ✅ 실제 매매 시 잔고 확인
        current_seed = get_seed()
        if current_seed < TRADE_AMOUNT:
            log.warning("❌ 잔고 부족으로 매수 취소")
            send_discord_message(f"❌ [실매매] 잔고 부족으로 매수 실패 (잔고: {current_seed})")
            return

    if is_simulated:
        if amount is None:
            amount = TRADE_AMOUNT / price
        log.info(f"🟢 모의 매수 - 가격: {price:,.0f}, 수량: {amount:.8f}")
        send_discord_message(f"🟢 [모의매매] 매수 - {price:,.0f}원, 수량: {amount:.8f}")
    else:
        try:
            upbit = pyupbit.Upbit(UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY)
            resp = upbit.buy_market_order(COIN_TICKER, TRADE_AMOUNT)  # 실매매는 금액 기준
            # 실제 매수 수량 추정
            amount = TRADE_AMOUNT / price  # 정확히 fill된 수량은 resp['executed_volume']이 필요함
            log.info(f"✅ 실전 매수 완료: {resp}")
            send_discord_message(f"✅ [실전매매] 매수 - {price:,.0f}원, 수량: {amount:.8f}")
        except Exception as e:
            log.error(f"[실매수 오류] {e}")
            send_discord_message(f"❌ 실매수 실패: {e}")
            return

    # ✅ 시드 차감
    if is_simulated or LIVE_MODE:
        new_balance = decrease_seed(TRADE_AMOUNT)
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
        except Exception as e:
            log.error(f"[매수 기록 저장 실패] {e}")
        finally:
            conn.close()


def sell(price: float, amount: float, roi: float, is_simulated: bool = not LIVE_MODE):
    holding = get_holding_amount()
    if holding <= 0:
        log.warning("⚠️ 현재 보유 수량 없음 → 매도 불가")
        send_discord_message("⚠️ [매도 차단] 보유 수량이 없어 매도하지 않습니다.")
        return

    amount = min(amount, holding)  # 보유 수량 초과 매도 방지

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

    # ✅ 시드 복구 (익절 기준 회수 금액 반영)
    if is_simulated or LIVE_MODE:
        profit_amount = TRADE_AMOUNT * (1 + roi)
        new_balance = increase_seed(profit_amount)
        log.info(f"💰 수익 반영 후 잔고: {new_balance}원")

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
        except Exception as e:
            log.error(f"[매도 기록 저장 실패] {e}")
        finally:
            conn.close()
