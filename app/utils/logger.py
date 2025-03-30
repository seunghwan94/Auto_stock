# app/utils/logger.py

import logging
import os
from datetime import datetime

# 로그 디렉토리 설정
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# 로그 파일 이름: logs/2025-03-30.log (오늘 날짜 기준)
log_filename = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d')}.log")

# 로거 생성
logger = logging.getLogger("AutoTraderLogger")
logger.setLevel(logging.INFO)

# 중복 핸들러 방지
if not logger.handlers:
    # 콘솔 출력 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 파일 출력 핸들러
    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    # 포맷 설정
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # 핸들러 등록
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

# 외부에서 import해서 사용
def get_logger():
    return logger
