# flake8: noqa
import json
import logging
from typing import Any

import requests

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30

def rossum_hook_request_handler(payload: dict) -> dict[str, Any]:
    """
    Google Sheets Key/Value memory provider.
    
    Modes:
    - configure: Returns configuration form for the Google Web App URL
    - learn: Appends a row [key, value] to the Google Sheet
    - retrieve: Searches for 'key' in Column A and returns Column B
    """
    variant = payload.get("variant", "retrieve")
    inner_payload = payload.get("payload", {})
    settings = payload.get("settings", {})
    mode = inner_payload.get("mode", variant)

    if mode == "configure":
        return {
            "intent": {
                "settings_form": {
                    "uiSchema": {
                        "type": "VerticalLayout",
                        "elements": [
                            {"type": "Control", "scope": "#/properties/google_webapp_url"},
                        ],
                    },
                    "schema": {
                        "type": "object",
                        "properties": {
                            "google_webapp_url": {
                                "type": "string", 
                                "title": "Google Web App URL",
                                "description": "The URL provided after deploying your Apps Script."
                            },
                        },
                    },
                },
            }
        }

    webapp_url = settings.get("google_webapp_url")
    memory_key = inner_payload.get("key")

    if not webapp_url:
        log.warning("Sheets Memory: google_webapp_url not specified")
        return {"value": None, "found": False}

    if not memory_key:
        log.warning("Sheets Memory: key not specified")
        return {"value": None, "found": False}

    if mode == "learn":
        return _learn(
            webapp_url=webapp_url,
            memory_key=memory_key,
            value=inner_payload.get("value")
        )

    return _retrieve(
        webapp_url=webapp_url,
        memory_key=memory_key
    )


def _retrieve(webapp_url: str, memory_key: str) -> dict[str, Any]:
    """Lookup search: Column A -> Column B."""
    try:
        # Google Apps Script doGet(e) handles parameters in the query string
        response = requests.get(
            webapp_url,
            params={"key": memory_key},
            timeout=DEFAULT_TIMEOUT,
            allow_redirects=True  # Important: Google Apps Script redirects to a temp URL
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
            return {
                "value": data.get("value"),
                "found": True,
            }
        
        return {"value": None, "found": False}

    except Exception:
        log.exception("Sheets memory retrieve failed", extra={"key": memory_key})
        return {"value": None, "found": False}


def _learn(webapp_url: str, memory_key: str, value: Any) -> dict[str, Any]:
    """Add a row: [key, value]."""
    try:
        # Google Apps Script doPost(e) handles JSON body
        response = requests.post(
            webapp_url,
            json={"key": memory_key, "value": str(value)},
            timeout=DEFAULT_TIMEOUT,
            allow_redirects=True
        )
        response.raise_for_status()
        return {}

    except Exception:
        log.exception("Sheets memory learn failed", extra={"key": memory_key})
        return {}