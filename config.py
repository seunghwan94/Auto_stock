# config.py

import os
from dotenv import load_dotenv


# 모의 투자 금액 설정
INITIAL_SEED = int(os.getenv("INITIAL_SEED", 100000))


# 로컬 환경일 경우 .env 파일 로드
if os.getenv("ENV") != "production":
    load_dotenv()

# 공통 설정
LIVE_MODE = os.getenv("LIVE_MODE", "False") == "True"

UPBIT_ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY")
UPBIT_SECRET_KEY = os.getenv("UPBIT_SECRET_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

COIN_TICKER = "KRW-BTC"
TRADE_AMOUNT = int(os.getenv("TRADE_AMOUNT", 10000))
TAKE_PROFIT = float(os.getenv("TAKE_PROFIT", 0.015))
STOP_LOSS = float(os.getenv("STOP_LOSS", -0.01))

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "1234"),
    "database": os.getenv("DB_NAME", "stockauto"),
    "charset": "utf8mb4"
}
