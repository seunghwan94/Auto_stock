import json
import os
from config import INITIAL_SEED  # ✅ config.py에서 가져오기

SEED_FILE = "seed_state.json"

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
