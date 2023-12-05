from httpx import AsyncClient
from fastapi import FastAPI, HTTPException, Depends
from typing import Dict
from pusher_push_notifications import PushNotifications
from config import Config

beams_client = PushNotifications(
    instance_id=Config.PUSHER_INSTANCE_ID,
    secret_key=Config.PUSHER_SECRET,
)


async def send_push_notification(instance_id: str, secret_key: str, payload: Dict):
    url = f"https://{instance_id}.pushnotifications.pusher.com/publish_api/v1/instances/{instance_id}/publishes/interests"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {secret_key}"
    }

    async with AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()

