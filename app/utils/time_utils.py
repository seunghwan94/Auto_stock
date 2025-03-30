# app/utils/time_utils.py

from datetime import datetime, timedelta
import pytz

def get_kst_now():
    return datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.timezone("Asia/Seoul"))

def format_datetime(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")
