"""Feishu bot webhook integration.

The route in this module is deliberately isolated from the existing REST
routes.  It accepts Feishu events, delegates text messages to the existing
RecruitmentAgent, and sends the generated answer back through Feishu's Open
API.  Feishu credentials are optional configuration, so importing this module
does not change the behaviour of non-Feishu deployments.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import re
import time
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.config import get_settings
from app.dependencies import get_recruitment_agent


logger = logging.getLogger(__name__)
router = APIRouter()

_FEISHU_MESSAGE_EVENT = "im.message.receive_v1"
_FEISHU_TOKEN_PATH = "/open-apis/auth/v3/tenant_access_token/internal"
_FEISHU_SEND_MESSAGE_PATH = "/open-apis/im/v1/messages"
_MENTION_TAG_RE = re.compile(r"<at\b[^>]*>.*?</at>", re.IGNORECASE | re.DOTALL)
_MAX_REPLY_LENGTH = 30_000

# A process-local cache is sufficient to prevent immediate duplicate retries.
# Feishu may retry a callback when it does not receive a successful response;
# the set is intentionally bounded and is reset on process restart.
_seen_event_ids: set[str] = set()
_seen_event_ids_lock = asyncio.Lock()

_tenant_access_token: str | None = None
_tenant_access_token_expires_at = 0.0
_tenant_access_token_lock = asyncio.Lock()


def _configured(value: str | None) -> bool:
    return bool(value and value.strip())


def _validate_verification_token(received: str | None, expected: str | None) -> None:
    """Validate Feishu's URL/event token when one is configured.

    Keeping the setting optional preserves the existing application's local
    quickstart.  A production Feishu deployment should always set it.
    """

    if expected and received != expected:
        raise HTTPException(status_code=403, detail="Invalid Feishu verification token")
    if not expected:
        logger.warning(
            "FEISHU_VERIFICATION_TOKEN is not configured; Feishu callback token "
            "validation is disabled"
        )


def _decrypt_payload(encrypted: str, encrypt_key: str) -> dict[str, Any]:
    """Decrypt a Feishu encrypted callback payload.

    Feishu derives an AES-256-CBC key from the configured Encrypt Key.  The
    cryptography import is lazy so existing deployments that do not receive
    encrypted Feishu events do not pay any import cost at application startup.
    """

    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    except ImportError as exc:  # pragma: no cover - requirements install this
        raise RuntimeError(
            "Encrypted Feishu events require the 'cryptography' package"
        ) from exc

    key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
    encrypted_bytes = base64.b64decode(encrypted)
    decryptor = Cipher(
        algorithms.AES(key),
        modes.CBC(key[:16]),
    ).decryptor()
    plaintext = decryptor.update(encrypted_bytes) + decryptor.finalize()

    padding_length = plaintext[-1]
    if not 1 <= padding_length <= 16:
        raise ValueError("Invalid Feishu encrypted payload padding")
    if plaintext[-padding_length:] != bytes([padding_length]) * padding_length:
        raise ValueError("Invalid Feishu encrypted payload padding")

    payload = json.loads(plaintext[:-padding_length].decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Decrypted Feishu payload must be a JSON object")
    return payload


def _verify_request_signature(
    request: Request,
    raw_body: bytes,
    encrypt_key: str,
) -> None:
    """Verify Feishu's signature for an encrypted event request."""

    timestamp = request.headers.get("X-Lark-Request-Timestamp")
    nonce = request.headers.get("X-Lark-Request-Nonce")
    signature = request.headers.get("X-Lark-Signature")
    if not (timestamp and nonce and signature):
        raise HTTPException(
            status_code=400,
            detail="Missing Feishu encrypted-event signature headers",
        )

    expected = hashlib.sha256(
        f"{timestamp}{nonce}{encrypt_key}".encode("utf-8") + raw_body
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=403, detail="Invalid Feishu request signature")


async def _read_payload(request: Request, settings: Any) -> dict[str, Any]:
    """Read plaintext or encrypted Feishu JSON and normalize it."""

    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Feishu payload must be a JSON object")

    encrypted = payload.get("encrypt")
    if encrypted:
        if not _configured(settings.feishu_encrypt_key):
            raise HTTPException(
                status_code=503,
                detail="FEISHU_ENCRYPT_KEY is required for encrypted Feishu events",
            )
        _verify_request_signature(request, raw_body, settings.feishu_encrypt_key)
        try:
            return _decrypt_payload(encrypted, settings.feishu_encrypt_key)
        except (ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=400,
                detail="Unable to decrypt Feishu event payload",
            ) from exc

    return payload


def _extract_text(message: dict[str, Any]) -> str:
    """Extract plain text from a Feishu text message payload."""

    content = message.get("content") or ""
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            # A few test tools send the text directly instead of using
            # Feishu's JSON-encoded ``content`` field.
            return content.strip()

    if not isinstance(content, dict):
        return ""

    text = str(content.get("text") or "")
    # Group messages commonly include the bot's mention as an <at> tag.  The
    # mention is metadata, not part of the user's query.
    return _MENTION_TAG_RE.sub("", text).strip()


def _sender_open_id(event: dict[str, Any]) -> str | None:
    sender = event.get("sender") or {}
    sender_id = sender.get("sender_id") or {}
    value = sender_id.get("open_id") or sender_id.get("user_id")
    return str(value) if value else None


def _message_context(event: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    message = event.get("message") or {}
    chat_id = message.get("chat_id")
    message_id = message.get("message_id")
    sender_id = _sender_open_id(event)
    return (
        str(chat_id) if chat_id else None,
        str(message_id) if message_id else None,
        sender_id,
    )


async def _mark_event_seen(event_id: str | None) -> bool:
    """Return False when an event was already scheduled for processing."""

    if not event_id:
        return True

    async with _seen_event_ids_lock:
        if event_id in _seen_event_ids:
            return False
        _seen_event_ids.add(event_id)
        # Keep memory bounded in a long-running process.  This is only a
        # duplicate guard; durable idempotency belongs in a shared store.
        if len(_seen_event_ids) > 10_000:
            _seen_event_ids.clear()
    return True


async def _get_tenant_access_token(
    client: httpx.AsyncClient,
    *,
    force_refresh: bool = False,
) -> str:
    """Fetch and cache a Feishu tenant access token."""

    global _tenant_access_token, _tenant_access_token_expires_at

    settings = get_settings()
    if not _configured(settings.feishu_app_id) or not _configured(settings.feishu_app_secret):
        raise RuntimeError(
            "FEISHU_APP_ID and FEISHU_APP_SECRET are required to send messages"
        )

    now = time.monotonic()
    if (
        not force_refresh
        and _tenant_access_token
        and now < _tenant_access_token_expires_at
    ):
        return _tenant_access_token

    async with _tenant_access_token_lock:
        now = time.monotonic()
        if (
            not force_refresh
            and _tenant_access_token
            and now < _tenant_access_token_expires_at
        ):
            return _tenant_access_token

        response = await client.post(
            f"{settings.feishu_api_base_url.rstrip('/')}{_FEISHU_TOKEN_PATH}",
            json={
                "app_id": settings.feishu_app_id,
                "app_secret": settings.feishu_app_secret,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code", 0) != 0 or not payload.get("tenant_access_token"):
            raise RuntimeError(
                f"Feishu token request failed: {payload.get('msg', 'unknown error')}"
            )

        _tenant_access_token = str(payload["tenant_access_token"])
        # Refresh one minute before Feishu's advertised expiry.
        expires_in = max(60, int(payload.get("expire", 7200)))
        _tenant_access_token_expires_at = time.monotonic() + expires_in - 60
        return _tenant_access_token


async def _send_text_message(chat_id: str, text: str) -> None:
    """Send a text response to a Feishu chat."""

    settings = get_settings()
    text = (text or "I couldn't generate a response.").strip()
    if len(text) > _MAX_REPLY_LENGTH:
        text = text[:_MAX_REPLY_LENGTH] + "\n\n(回复内容过长，已截断)"

    async with httpx.AsyncClient(timeout=15.0) as client:
        token = await _get_tenant_access_token(client)
        response = await client.post(
            f"{settings.feishu_api_base_url.rstrip('/')}{_FEISHU_SEND_MESSAGE_PATH}",
            params={"receive_id_type": "chat_id"},
            headers={"Authorization": f"Bearer {token}"},
            json={
                "receive_id": chat_id,
                "msg_type": "text",
                "content": json.dumps({"text": text}, ensure_ascii=False),
            },
        )

        # A stale cached token can produce an authorization error.  Refresh
        # once and retry; all other API failures are surfaced to the log.
        if response.status_code in {401, 403}:
            token = await _get_tenant_access_token(client, force_refresh=True)
            response = await client.post(
                f"{settings.feishu_api_base_url.rstrip('/')}{_FEISHU_SEND_MESSAGE_PATH}",
                params={"receive_id_type": "chat_id"},
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "receive_id": chat_id,
                    "msg_type": "text",
                    "content": json.dumps({"text": text}, ensure_ascii=False),
                },
            )

        response.raise_for_status()
        payload = response.json()
        if payload.get("code", 0) != 0:
            raise RuntimeError(
                f"Feishu send message failed: {payload.get('msg', 'unknown error')}"
            )


async def _handle_message_event(event: dict[str, Any]) -> None:
    """Process one text event outside the webhook response deadline."""

    message = event.get("message") or {}
    if message.get("message_type") != "text":
        logger.info("Ignoring unsupported Feishu message type: %s", message.get("message_type"))
        return

    # Ignore messages emitted by an app/bot to prevent reply loops.
    sender = event.get("sender") or {}
    if sender.get("sender_type") == "app":
        return

    query = _extract_text(message)
    chat_id, _, sender_id = _message_context(event)
    if not query or not chat_id:
        logger.info("Ignoring Feishu message without text or chat_id")
        return

    settings = get_settings()
    if not _configured(settings.feishu_app_id) or not _configured(settings.feishu_app_secret):
        logger.error(
            "Cannot process Feishu message: FEISHU_APP_ID/FEISHU_APP_SECRET are not configured"
        )
        return

    try:
        agent = get_recruitment_agent()
        result = await agent.process_query(
            query=query,
            chat_history=[],
            session_id=f"feishu:{chat_id}",
            user_id=f"feishu:{sender_id}" if sender_id else None,
        )
        response_text = result.get("response") or "暂时无法生成回复，请稍后再试。"
        await _send_text_message(chat_id, response_text)
    except Exception:
        logger.exception("Failed to process Feishu message event")


@router.post("/feishu/events")
async def receive_feishu_event(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Receive Feishu URL-verification and message events.

    The endpoint acknowledges supported events immediately.  AI processing
    and the outbound Feishu API call run as a background task because model
    responses can take longer than Feishu's webhook acknowledgement window.
    """

    settings = get_settings()
    payload = await _read_payload(request, settings)

    # Feishu sends this request while saving the event subscription URL.
    if payload.get("type") == "url_verification":
        _validate_verification_token(payload.get("token"), settings.feishu_verification_token)
        challenge = payload.get("challenge")
        if not challenge:
            raise HTTPException(status_code=400, detail="Missing Feishu challenge")
        return {"challenge": challenge}

    header = payload.get("header") or {}
    _validate_verification_token(
        header.get("token") or payload.get("token"),
        settings.feishu_verification_token,
    )

    event = payload.get("event")
    event_type = header.get("event_type") or payload.get("event_type")
    # Older Feishu callback payloads do not include the v2 header.  A message
    # object is unambiguous for this integration, so accept that shape too.
    if (
        not event_type
        and isinstance(event, dict)
        and isinstance(event.get("message"), dict)
    ):
        event_type = _FEISHU_MESSAGE_EVENT
    if event_type != _FEISHU_MESSAGE_EVENT:
        # Acknowledge events we do not currently use so Feishu does not retry.
        return {"code": 0}

    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="Missing Feishu event body")

    event_id = (
        header.get("event_id")
        or payload.get("event_id")
        or (event.get("message") or {}).get("message_id")
    )
    if not await _mark_event_seen(str(event_id) if event_id else None):
        return {"code": 0}

    background_tasks.add_task(_handle_message_event, event)
    return {"code": 0}
