import json
import os
from config import INITIAL_SEED  # ✅ config.py에서 가져오기
from app.utils.db_connect import get_connection
from app.utils.logger import get_logger
from config import LIVE_MODE

log = get_logger()

SEED_FILE = "seed_state.json"

# 현재 보유 수량 조회
def get_holding_amount() -> float:
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT SUM(CASE 
                            WHEN trade_type = 'buy' THEN amount 
                            WHEN trade_type = 'sell' THEN -amount 
                            ELSE 0 END) as holding
                FROM trade_history
                WHERE is_simulated = %s
            """, (not LIVE_MODE,))
            result = cursor.fetchone()
            return float(result[0]) if result[0] else 0.0
    except Exception as e:
        log.error(f"[보유 수량 조회 오류] {e}")
        return 0.0


def _load_seed():
    if not os.path.exists(SEED_FILE):
        _save_seed(INITIAL_SEED)
    with open(SEED_FILE, "r") as f:
        data = json.load(f)
        return data.get("balance", INITIAL_SEED)

def _save_seed(balance):
    with open(SEED_FILE, "w") as f:
        json.dump({"balance": balance}, f)

def get_seed():
    return _load_seed()

def decrease_seed(amount: float):
    balance = _load_seed()
    balance -= amount
    _save_seed(balance)
    return balance

def increase_seed(amount: float):
    balance = _load_seed()
    balance += amount
    _save_seed(balance)
    return balance
