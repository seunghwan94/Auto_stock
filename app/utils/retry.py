# app/utils/retry.py

import time
from functools import wraps

def retry(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"[재시도 {i+1}/{max_retries}] {func.__name__} 실패: {e}")
                    time.sleep(delay)
            raise Exception(f"{func.__name__} 실패 - 최대 재시도 초과")
        return wrapper
    return decorator
