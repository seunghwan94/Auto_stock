# app/utils/db_connect.py

import pymysql
from config import DB_CONFIG
import sys

def get_connection():
    try:
        conn = pymysql.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            charset=DB_CONFIG["charset"],
            autocommit=True
        )
        return conn
    except Exception as e:
        print(f"[DB 연결 오류] {e}", file=sys.stderr)
        return None
