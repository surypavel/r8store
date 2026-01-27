# flake8: noqa
import json
import logging
from datetime import datetime, timezone
from typing import Any

import requests

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
DEFAULT_MATCH_COUNT = 3
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
HUGGINGFACE_API_URL = f"https://router.huggingface.co/hf-inference/models/{EMBEDDING_MODEL}/pipeline/feature-extraction"


def rossum_hook_request_handler(payload: dict) -> dict[str, Any]:
    """
    Supabase/HuggingFace RAG memory provider for memory fields.

    Modes:
    - configure: Returns configuration form
    - learn: Inserts a document with embedding to Supabase
    - retrieve: Searches documents by semantic similarity

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
        "settings": {
            "supabase_url": "https://xxx.supabase.co",
            "table_name": "documents",  # optional, defaults to "documents"
            "match_function": "match_documents",  # optional, defaults to "match_documents"
            "match_count": 3,  # optional, defaults to 3
        },
        "secrets": {
            "supabase_key": "...",
            "huggingface_token": "...",
        },
        "variant": "retrieve" | "learn" | "configure",
    }
    """
    variant = payload.get("variant", "retrieve")
    inner_payload = payload.get("payload", {})
    settings = payload.get("settings", {})
    secrets = payload.get("secrets", {})
    mode = inner_payload.get("mode", variant)

    if mode == "configure":
        return {
            "intent": {
                "settings_form": {
                    "uiSchema": {
                        "type": "VerticalLayout",
                        "elements": [
                            {"type": "Control", "scope": "#/properties/supabase_url"},
                            {"type": "Control", "scope": "#/properties/table_name"},
                            {"type": "Control", "scope": "#/properties/match_function"},
                            {"type": "Control", "scope": "#/properties/match_count"},
                        ],
                    },
                    "schema": {
                        "type": "object",
                        "properties": {
                            "supabase_url": {"type": "string"},
                            "table_name": {"type": "string"},
                            "match_function": {"type": "string"},
                            "match_count": {"type": "integer"},
                        },
                    },
                },
                "secrets_form": {
                    "uiSchema": {
                        "type": "VerticalLayout",
                        "elements": [
                            {"type": "Control", "scope": "#/properties/supabase_key"},
                            {"type": "Control", "scope": "#/properties/huggingface_token"},
                        ],
                    },
                    "schema": {
                        "type": "object",
                        "properties": {
                            "supabase_key": {"type": "string"},
                            "huggingface_token": {"type": "string"},
                        },
                    },
                },
            }
        }

    supabase_url = settings.get("supabase_url")
    supabase_key = secrets.get("supabase_key")
    huggingface_token = secrets.get("huggingface_token")
    table_name = settings.get("table_name", "documents")
    match_function = settings.get("match_function", "match_documents")
    match_count = settings.get("match_count", DEFAULT_MATCH_COUNT)
    memory_key = inner_payload.get("key")

    if not supabase_url or not supabase_key:
        log.warning("Supabase RAG memory: supabase_url or supabase_key not specified")
        return {"value": None, "struct": None, "found": False}

    if not huggingface_token:
        log.warning("Supabase RAG memory: huggingface_token not specified")
        return {"value": None, "struct": None, "found": False}

    if not memory_key:
        log.warning("Supabase RAG memory: key not specified")
        return {"value": None, "struct": None, "found": False}

    if mode == "learn":
        return _learn(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            huggingface_token=huggingface_token,
            table_name=table_name,
            memory_key=memory_key,
            value=inner_payload.get("value"),
            struct=inner_payload.get("struct"),
        )

    return _retrieve(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        huggingface_token=huggingface_token,
        match_function=match_function,
        match_count=match_count,
        memory_key=memory_key,
    )


def _get_embedding(text: str, huggingface_token: str) -> list[float] | None:
    """Get embedding vector from HuggingFace API."""
    try:
        response = requests.post(
            HUGGINGFACE_API_URL,
            headers={
                "Authorization": f"Bearer {huggingface_token}",
                "Content-Type": "application/json",
            },
            json={"inputs": text},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        embedding = response.json()
        # HuggingFace may return nested array [[0.1, 0.2, ...]] - unwrap if needed
        if embedding and isinstance(embedding, list) and isinstance(embedding[0], list):
            embedding = embedding[0]
        return embedding
    except requests.exceptions.RequestException:
        log.exception("HuggingFace embedding request failed")
        return None


def _retrieve(
    supabase_url: str,
    supabase_key: str,
    huggingface_token: str,
    match_function: str,
    match_count: int,
    memory_key: str,
) -> dict[str, Any]:
    """Search documents by semantic similarity using Supabase vector search."""
    try:
        embedding = _get_embedding(memory_key, huggingface_token)
        if embedding is None:
            return {"value": None, "struct": None, "found": False}

        response = requests.post(
            f"{supabase_url}/rest/v1/rpc/{match_function}",
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
            },
            json={
                "query_embedding": embedding,
                "match_count": match_count,
            },
            timeout=DEFAULT_TIMEOUT,
        )

        if response.status_code == 404:
            return {"value": None, "struct": None, "found": False}

        response.raise_for_status()
        results = response.json()
        log.info(
            f"Supabase RAG memory retrieve: key={memory_key}, count={len(results) if results else 0}, results={results}"
        )

        if not results:
            return {"value": None, "struct": None, "found": False}

        top_result = results[0]
        value = top_result.get("content")
        struct = {
            "similarity": top_result.get("similarity"),
        }

        return {
            "value": value,
            "struct": struct,
            "found": True,
        }

    except requests.exceptions.RequestException:
        log.exception(
            "Supabase RAG memory retrieve failed",
            extra={"memory_key": memory_key},
        )
        return {"value": None, "struct": None, "found": False}


def _learn(
    supabase_url: str,
    supabase_key: str,
    huggingface_token: str,
    table_name: str,
    memory_key: str,
    value: Any,
    struct: dict | None,
) -> dict[str, Any]:
    """Store document with embedding to Supabase."""
    try:
        # Embed the key (index formula) for semantic matching
        embedding = _get_embedding(memory_key, huggingface_token)
        if embedding is None:
            return {}

        # Store the value as content to be returned on match
        record = {
            "content": value,
            "embedding": embedding,
            "learned_value": memory_key,
        }

        response = requests.post(
            f"{supabase_url}/rest/v1/{table_name}",
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json=record,
            timeout=DEFAULT_TIMEOUT,
        )

        if not response.ok:
            log.error(
                "Supabase RAG memory learn failed",
                extra={
                    "table_name": table_name,
                    "memory_key": memory_key,
                    "status_code": response.status_code,
                    "response_body": response.text,
                },
            )
        response.raise_for_status()
        log.info(
            "Supabase RAG memory learn successful",
            extra={"table_name": table_name, "memory_key": memory_key},
        )
        return {}

    except requests.exceptions.RequestException:
        log.exception(
            "Supabase RAG memory learn failed",
            extra={"table_name": table_name, "memory_key": memory_key},
        )
        return {}
