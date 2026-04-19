from __future__ import annotations

import asyncio
import logging
import httpx

from agent.core.config import get_settings

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramBotError(Exception):
    """Raised when Telegram integration fails."""


async def send_telegram_message(
    client: httpx.AsyncClient,
    token: str,
    chat_id: int,
    text: str,
) -> None:
    response = await client.post(
        f"{TELEGRAM_API_BASE}/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=20,
    )
    response.raise_for_status()


async def forward_to_command_endpoint(
    client: httpx.AsyncClient,
    command_endpoint: str,
    api_key: str,
    text: str,
) -> str:
    response = await client.post(
        command_endpoint,
        headers={"x-api-key": api_key},
        json={"command": text, "args": {}},
        timeout=60,
    )

    if response.status_code >= 400:
        detail = response.text
        raise TelegramBotError(f"Command request failed ({response.status_code}): {detail}")

    payload = response.json()
    status = payload.get("status", "unknown")
    message = payload.get("message", "")
    data = payload.get("data")

    if data is None:
        return f"Status: {status}\nMessage: {message}"

    return f"Status: {status}\nMessage: {message}\nData: {data}"


async def poll_updates() -> None:
    settings = get_settings()

    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN must be set to run the Telegram bot bridge")

    if not settings.telegram_command_url:
        raise RuntimeError("TELEGRAM_COMMAND_URL must be set to your /command endpoint URL")

    offset = 0

    async with httpx.AsyncClient() as client:
        logger.info("telegram_bridge_started")
        while True:
            try:
                response = await client.get(
                    f"{TELEGRAM_API_BASE}/bot{settings.telegram_bot_token}/getUpdates",
                    params={
                        "timeout": 30,
                        "offset": offset,
                        "allowed_updates": ["message"],
                    },
                    timeout=40,
                )
                response.raise_for_status()
                result = response.json()
            except Exception:
                logger.exception("telegram_get_updates_failed")
                await asyncio.sleep(2)
                continue

            for update in result.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message", {})
                chat = message.get("chat", {})
                text = message.get("text", "").strip()
                chat_id = chat.get("id")

                if not chat_id:
                    continue

                if not text:
                    await send_telegram_message(
                        client,
                        settings.telegram_bot_token,
                        chat_id,
                        "Please send text commands only.",
                    )
                    continue

                try:
                    command_result = await forward_to_command_endpoint(
                        client,
                        settings.telegram_command_url,
                        settings.api_key,
                        text,
                    )
                except Exception as exc:
                    logger.exception("telegram_command_forward_failed")
                    command_result = f"Failed to run command: {exc}"

                try:
                    await send_telegram_message(
                        client,
                        settings.telegram_bot_token,
                        chat_id,
                        command_result,
                    )
                except Exception:
                    logger.exception("telegram_send_message_failed")


if __name__ == "__main__":
    logging.basicConfig(
        level=get_settings().log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(poll_updates())
