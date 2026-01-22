# flake8: noqa
import io
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

import requests

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
KEY_COLUMN = "memory_key"
VALUE_COLUMN = "value"
CREATED_AT_COLUMN = "created_at"


def _get_organization(payload: dict) -> dict:
    response = requests.get(
        f"{payload['base_url']}/api/v1/organizations",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {payload['rossum_authorization_token']}",
        },
    )

    response.raise_for_status()
    return response.json()["results"][0]


def _get_master_data_hub_credentials(payload: dict) -> tuple[str, str | None, str]:
    is_api_develop = payload["base_url"].startswith("https://elis.develop.r8.lol") or payload["base_url"].startswith(
        "https://api.elis.develop.r8.lol"
    )
    is_api_review = bool(re.match(r"^https://review-ac-elis-backend-\d+\.review\.r8\.lol", payload["base_url"]))

    if is_api_develop:
        return ("https://elis.master.r8.lol/svc/master-data-hub/api", payload["rossum_authorization_token"], "true")
    elif is_api_review:
        organization = _get_organization(payload)
        return (
            "https://elis.master.r8.lol/svc/master-data-hub/api",
            organization["metadata"].get("mdh_master_token"),
            "",
        )
    else:
        return (f"{payload['base_url']}/svc/master-data-hub/api", payload["rossum_authorization_token"], "")


def rossum_hook_request_handler(payload: dict) -> dict[str, Any]:
    """
    Master Data Hub memory provider for memory fields.

    Modes:
    - configure: Returns empty intent
    - learn: Upserts a record to the dataset via PATCH with update_or_new=true
    - retrieve: Finds a record in the dataset by memory_key

    Payload structure:
    {
        "base_url": "https://...",
        "rossum_authorization_token": "...",
        "payload": {
            "mode": "retrieve" | "learn",
            "key": "memory_key_value",
            "value": "...",  # only for learn
            "struct": {...},  # only for learn
            "dataset": "dataset_name",  # required
        },
        "variant": "retrieve" | "learn" | "configure",
    }
    """
    variant = payload.get("variant", "retrieve")
    inner_payload = payload.get("payload", {})
    mode = inner_payload.get("mode", variant)

    if mode == "configure":
        return {
            "intent": {
                "form": {
                    "uiSchema": {
                        "type": "VerticalLayout",
                        "elements": [
                            {"type": "Control", "scope": "#/properties/dataset"},
                        ],
                    },
                    "schema": {
                        "type": "object",
                        "properties": {
                            "dataset": {"type": "string"},
                        },
                    },
                },
            }
        }

    url, token, is_dev = _get_master_data_hub_credentials(payload)
    dataset = inner_payload.get("dataset")
    memory_key = inner_payload.get("key")

    if not dataset:
        log.warning("Master Data Hub memory: dataset not specified")
        return {"value": None, "struct": None, "found": False}

    if not memory_key:
        log.warning("Master Data Hub memory: key not specified")
        return {"value": None, "struct": None, "found": False}

    if mode == "learn":
        return _learn(
            mdh_url=url,
            token=token,
            is_dev=is_dev,
            dataset=dataset,
            memory_key=memory_key,
            value=inner_payload.get("value"),
            struct=inner_payload.get("struct"),
        )

    return _retrieve(
        mdh_url=url,
        token=token,
        is_dev=is_dev,
        dataset=dataset,
        memory_key=memory_key,
    )


def _retrieve(
    mdh_url: str,
    token: str | None,
    is_dev: str,
    dataset: str,
    memory_key: str,
) -> dict[str, Any]:
    """Retrieve memory data from Master Data Hub using aggregate query."""
    try:
        aggregate = [
            {"$match": {KEY_COLUMN: {"$eq": memory_key}}},
            {"$limit": 1},
        ]

        response = requests.post(
            f"{mdh_url}/v1/data/aggregate",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "X-ROSSUM-DEV": is_dev,
            },
            json={
                "dataset": dataset,
                "aggregate": aggregate,
                "collation": {},
                "let": {},
                "options": {},
            },
            timeout=DEFAULT_TIMEOUT,
        )

        if response.status_code == 404:
            return {"value": None, "struct": None, "found": False}

        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])

        if not results:
            return {"value": None, "struct": None, "found": False}

        record = results[0]
        value = record.get(VALUE_COLUMN)
        struct = {k: v for k, v in record.items() if k not in (KEY_COLUMN, VALUE_COLUMN, CREATED_AT_COLUMN, "_id")}

        return {
            "value": value,
            "struct": struct if struct else None,
            "found": True,
        }

    except requests.exceptions.RequestException:
        log.exception(
            "Master Data Hub memory retrieve failed",
            extra={"dataset": dataset, "memory_key": memory_key},
        )
        return {"value": None, "struct": None, "found": False}


def _learn(
    mdh_url: str,
    token: str | None,
    is_dev: str,
    dataset: str,
    memory_key: str,
    value: Any,
    struct: dict | None,
) -> dict[str, Any]:
    """Store memory data to Master Data Hub using PATCH with update_or_new."""
    try:
        record = {
            KEY_COLUMN: memory_key,
            VALUE_COLUMN: value,
            CREATED_AT_COLUMN: datetime.now(timezone.utc).isoformat(),
        }
        if struct:
            record.update(struct)

        json_content = json.dumps([record])
        file_obj = io.BytesIO(json_content.encode("utf-8"))

        response = requests.patch(
            f"{mdh_url}/v1/dataset/{dataset}",
            headers={
                "Authorization": f"Bearer {token}",
                "X-ROSSUM-DEV": is_dev,
            },
            files={
                "file": ("memory_data.json", file_obj, "application/json"),
            },
            data={
                "encoding": "utf-8",
                "update_or_new": "true",
                "id_keys": KEY_COLUMN,
            },
            timeout=DEFAULT_TIMEOUT,
        )

        response.raise_for_status()
        log.info(
            "Master Data Hub memory learn successful",
            extra={"dataset": dataset, "memory_key": memory_key},
        )
        return {}

    except requests.exceptions.RequestException:
        log.exception(
            "Master Data Hub memory learn failed",
            extra={"dataset": dataset, "memory_key": memory_key},
        )
        return {}
