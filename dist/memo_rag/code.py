from typing import Any

import requests

WEBHOOK_URL = "https://webhook.site/fa24415c-ac46-4217-a223-0a4b15e84210"


def rossum_hook_request_handler(payload: dict) -> dict[str, Any]:
    """
    Testing memory provider for development/debugging.

    Modes:
    - configure: Returns empty intent
    - learn: POSTs value to webhook.site
    - retrieve: Always returns {"value": "Loaded from memory", "found": True}

    Payload structure:
    {
        "base_url": "https://...",
        "rossum_authorization_token": "...",
        "payload": {
            "mode": "retrieve" | "learn",
            "key": "memory_key_value",
            "value": "...",  # only for learn
            "struct": {...},  # only for learn
        },
        "variant": "retrieve" | "learn" | "configure",
    }
    """
    variant = payload.get("variant", "retrieve")
    inner_payload = payload.get("payload", {})
    mode = inner_payload.get("mode", variant)

    if mode == "configure":
        return {"intent": {}}

    if mode == "learn":
        try:
            requests.post(
                WEBHOOK_URL,
                json={
                    "mode": "learn",
                    "key": inner_payload.get("key"),
                    "value": inner_payload.get("value"),
                    "struct": inner_payload.get("struct"),
                },
                timeout=10,
            )
        except Exception:
            pass
        return {}

    return {
        "value": "Loaded from memory",
        "struct": None,
        "found": True,
    }
