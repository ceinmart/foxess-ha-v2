"""
Versao: v0.1.0
Data/hora de criacao: 2026-04-14 16:05:00
Criado por: Codex / OpenAI
Projeto/Pasta: C:\\tmp\\foxess-ha.v2
"""

from __future__ import annotations

from collections.abc import Iterable
import hashlib
import json
from pathlib import Path
import time
from typing import Any

import aiohttp

from .const import (
    API_BASE_URL,
    API_LANG,
    ENDPOINT_ACCESS_COUNT,
    ENDPOINT_DEVICE_LIST,
    ENDPOINT_REALTIME_QUERY,
    ENDPOINT_VARIABLE_CATALOG,
    REQUEST_TIMEOUT_SECONDS,
    SCHEMA_BASE_DIR,
    SCHEMA_VERSION_FOLDER,
)


class FoxessApiError(Exception):
    """Base exception for FoxESS API client."""


class FoxessApiAuthError(FoxessApiError):
    """Raised when authentication appears to be invalid."""


class FoxessApiRequestError(FoxessApiError):
    """Raised when request fails for non-auth reasons."""


def generate_signature(path: str, token: str, timestamp_ms: str) -> str:
    signature_raw = f"{path}\r\n{token}\r\n{timestamp_ms}"
    return hashlib.md5(signature_raw.encode("utf-8")).hexdigest()


def _extract_result(payload: dict[str, Any]) -> Any:
    return payload.get("result", payload)


def extract_scalar_variable_names(payload: Any) -> set[str]:
    """Extract variable-like keys with scalar values from nested payloads."""

    found: set[str] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(key, str) and isinstance(value, (str, int, float, bool)):
                    found.add(key)
                elif isinstance(value, (dict, list)):
                    _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(payload)
    return found


def extract_realtime_by_sn(payload: dict[str, Any], sns: Iterable[str]) -> dict[str, dict[str, Any]]:
    sns = list(sns)
    result = _extract_result(payload)
    by_sn: dict[str, dict[str, Any]] = {}

    if isinstance(result, dict):
        for maybe_sn, value in result.items():
            if maybe_sn in sns and isinstance(value, dict):
                by_sn[maybe_sn] = value

    candidates: list[dict[str, Any]] = []
    if isinstance(result, list):
        candidates.extend(item for item in result if isinstance(item, dict))
    if isinstance(result, dict):
        for key in ("data", "datas", "list", "records", "items"):
            value = result.get(key)
            if isinstance(value, list):
                candidates.extend(item for item in value if isinstance(item, dict))

    for item in candidates:
        sn = item.get("sn") or item.get("deviceSN") or item.get("deviceSn")
        if isinstance(sn, str):
            by_sn[sn] = item

    if not by_sn and len(sns) == 1 and isinstance(result, dict):
        by_sn[sns[0]] = result

    return by_sn


class FoxessApiClient:
    """FoxESS async API client with local schema support."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        base_url: str = API_BASE_URL,
        integration_dir: Path | None = None,
    ) -> None:
        self._session = session
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._integration_dir = integration_dir or Path(__file__).resolve().parent

    async def _request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        timestamp_ms = str(int(time.time() * 1000))
        signature = generate_signature(path, self._api_key, timestamp_ms)
        headers = {
            "token": self._api_key,
            "timestamp": timestamp_ms,
            "signature": signature,
            "lang": API_LANG,
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}{path}"
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)

        try:
            async with self._session.request(
                method=method.upper(),
                url=url,
                params=query,
                json=body,
                headers=headers,
                timeout=timeout,
            ) as response:
                payload = await response.json(content_type=None)
                if response.status >= 400:
                    raise FoxessApiRequestError(
                        f"HTTP {response.status} calling {path}: {json.dumps(payload, ensure_ascii=True)[:500]}"
                    )
        except aiohttp.ClientError as exc:
            raise FoxessApiRequestError(f"Request to {path} failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise FoxessApiRequestError(f"Invalid JSON response from {path}") from exc

        errno = payload.get("errno")
        if errno not in (None, 0):
            message = str(payload.get("msg", "Unknown FoxESS API error"))
            if "token" in message.lower() or "auth" in message.lower():
                raise FoxessApiAuthError(message)
            raise FoxessApiRequestError(f"FoxESS API error errno={errno}: {message}")

        return payload

    async def async_list_devices(self, page: int = 1, page_size: int = 200) -> dict[str, Any]:
        payload = await self._request(
            "POST",
            ENDPOINT_DEVICE_LIST,
            body={"currentPage": page, "pageSize": page_size},
        )
        result = _extract_result(payload)
        devices: list[dict[str, Any]] = []
        if isinstance(result, dict):
            maybe_data = result.get("data")
            if isinstance(maybe_data, list):
                devices = [item for item in maybe_data if isinstance(item, dict)]
        elif isinstance(result, list):
            devices = [item for item in result if isinstance(item, dict)]
        return {"raw": payload, "devices": devices}

    async def async_get_variable_catalog(self) -> dict[str, Any]:
        payload = await self._request("GET", ENDPOINT_VARIABLE_CATALOG)
        result = _extract_result(payload)
        catalog: dict[str, dict[str, Any]] = {}
        if isinstance(result, dict):
            for variable, meta in result.items():
                if isinstance(variable, str) and isinstance(meta, dict):
                    catalog[variable] = meta
        return {"raw": payload, "variables": catalog}

    async def async_query_realtime(
        self,
        sns: list[str],
        variables: list[str] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"sns": sns}
        if variables:
            body["variables"] = variables
        payload = await self._request("POST", ENDPOINT_REALTIME_QUERY, body=body)
        by_sn = extract_realtime_by_sn(payload, sns)
        return {"raw": payload, "by_sn": by_sn}

    async def async_get_access_count(self) -> dict[str, Any]:
        payload = await self._request("GET", ENDPOINT_ACCESS_COUNT)
        result = _extract_result(payload)
        total = None
        remaining = None
        if isinstance(result, dict):
            total = result.get("total")
            remaining = result.get("remaining")
        return {"raw": payload, "total": total, "remaining": remaining}

    def load_local_schema_manifest(self) -> dict[str, Any]:
        manifest_path = (
            self._integration_dir
            / SCHEMA_BASE_DIR
            / SCHEMA_VERSION_FOLDER
            / "001.foxess.endpoint_inventory.json"
        )
        if not manifest_path.exists():
            return {}
        return json.loads(manifest_path.read_text(encoding="utf-8"))
