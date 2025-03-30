# app/utils/discord.py

import requests
import json
from config import DISCORD_WEBHOOK_URL

def send_discord_message(content: str):
    """
    Discord Webhook으로 메시지를 전송합니다.
    :param content: 보낼 메시지 내용 (텍스트)
    """
    try:
        payload = {
            "content": content
        }
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(DISCORD_WEBHOOK_URL, data=json.dumps(payload), headers=headers)

        if response.status_code != 204:
            print(f"[Discord 전송 실패] 상태 코드: {response.status_code} / 응답: {response.text}")
    except Exception as e:
        print(f"[Discord 전송 예외] {e}")
