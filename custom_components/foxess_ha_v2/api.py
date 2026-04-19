"""
Version: v0.1.4
Created at: 2026-04-19 10:13:52 -03:00
Created by: Codex / OpenAI
Project/Folder: C:\\tmp\\foxess-ha.v2\\foxess-ha-v2

FoxESS Open API helpers and the async client used by the integration runtime.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
import hashlib
import json
import logging
from pathlib import Path
import time
from typing import Any

import aiohttp

from .const import (
    API_BASE_URL,
    API_LANG,
    ENDPOINT_ACCESS_COUNT,
    ENDPOINT_DEVICE_DETAIL,
    ENDPOINT_DEVICE_LIST,
    ENDPOINT_REALTIME_QUERY,
    ENDPOINT_VARIABLE_CATALOG,
    REQUEST_TIMEOUT_SECONDS,
    REQUEST_VERIFY_SSL,
    SCHEMA_BASE_DIR,
    SCHEMA_VERSION_FOLDER,
)

LOGGER = logging.getLogger(__name__)


class FoxessApiError(Exception):
    """Base exception for FoxESS API client."""


class FoxessApiAuthError(FoxessApiError):
    """Raised when authentication appears to be invalid."""


class FoxessApiRequestError(FoxessApiError):
    """Raised when request fails for non-auth reasons."""


def generate_signature(path: str, token: str, timestamp_ms: str) -> str:
    """Build the request signature expected by the FoxESS Open API."""

    # FoxESS expects literal "\r\n" in the signature payload, matching script 020 behavior.
    signature_raw = fr"{path}\r\n{token}\r\n{timestamp_ms}"
    return hashlib.md5(signature_raw.encode("utf-8")).hexdigest()


def _extract_result(payload: dict[str, Any]) -> Any:
    """Return the `result` field when FoxESS wraps payloads, else the payload itself."""

    return payload.get("result", payload)


def summarize_request_context(
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> str:
    """Create a compact trace summary for log lines."""

    parts: list[str] = []

    if query:
        sn = query.get("sn")
        if isinstance(sn, str) and sn.strip():
            parts.append(f"sn={sn.strip()}")

    if body:
        sn = body.get("sn")
        if isinstance(sn, str) and sn.strip():
            parts.append(f"sn={sn.strip()}")

        sns = body.get("sns")
        if isinstance(sns, list):
            visible_sns = [str(item).strip() for item in sns[:3] if str(item).strip()]
            if visible_sns:
                summary = ",".join(visible_sns)
                if len(sns) > len(visible_sns):
                    summary = f"{summary},+{len(sns) - len(visible_sns)}"
                parts.append(f"sns={summary}")
            else:
                parts.append(f"sns_count={len(sns)}")

        variables = body.get("variables")
        if isinstance(variables, list):
            parts.append(f"variables={len(variables)}")

        for key in ("currentPage", "pageSize"):
            value = body.get(key)
            if isinstance(value, (str, int, float)):
                parts.append(f"{key}={value}")

    return " ".join(parts) if parts else "-"


def extract_device_detail(payload: dict[str, Any], *, default_sn: str | None = None) -> dict[str, Any]:
    """Normalize /op/v1/device/detail to a single detail object."""

    result = _extract_result(payload)
    if isinstance(result, dict):
        detail = dict(result)
        if default_sn and not detail.get("deviceSN"):
            detail["deviceSN"] = default_sn
        return detail

    return {"deviceSN": default_sn} if default_sn else {}


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


def extract_realtime_variable_records(device_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Normalize realtime payload into {variable: {value, unit, name, time}}."""

    rows: list[dict[str, Any]] = []
    for key in ("datas", "data", "items", "records", "list"):
        value = device_payload.get(key)
        if isinstance(value, list):
            rows.extend(item for item in value if isinstance(item, dict))

    by_variable: dict[str, dict[str, Any]] = {}
    for row in rows:
        variable = row.get("variable")
        if isinstance(variable, str) and variable.strip():
            by_variable[variable] = {
                "value": row.get("value"),
                "unit": row.get("unit"),
                "name": row.get("name"),
                "time": device_payload.get("time"),
            }

    if by_variable:
        return by_variable

    # Fallback for flatter payload structures.
    for key, value in device_payload.items():
        if key in {"sn", "deviceSN", "deviceSn", "time"}:
            continue
        if isinstance(value, (str, int, float, bool)):
            by_variable[key] = {"value": value, "unit": None, "name": key, "time": device_payload.get("time")}

    return by_variable


def normalize_variable_catalog_response(response_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Normalize /op/v0/device/variable/get to {variable: meta}."""

    result = _extract_result(response_data) if isinstance(response_data, dict) else {}
    catalog: dict[str, dict[str, Any]] = {}

    if isinstance(result, dict):
        for variable, meta in result.items():
            if isinstance(variable, str) and isinstance(meta, dict):
                catalog[variable] = meta

    if isinstance(result, list):
        for entry in result:
            if not isinstance(entry, dict):
                continue

            datas = entry.get("datas")
            if isinstance(datas, list):
                for row in datas:
                    if not isinstance(row, dict):
                        continue
                    variable = row.get("variable")
                    if isinstance(variable, str):
                        catalog[variable] = {
                            "unit": row.get("unit"),
                            "name": {"en": row.get("name")} if row.get("name") else {},
                        }

            # Some payloads may come as { "<variable>": {meta... } } inside list entries.
            for variable, meta in entry.items():
                if isinstance(variable, str) and isinstance(meta, dict):
                    catalog[variable] = meta

    return catalog


def extract_realtime_by_sn(payload: dict[str, Any], sns: Iterable[str]) -> dict[str, dict[str, Any]]:
    """Normalize grouped or single-device realtime responses into a `{sn: payload}` map."""

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
    if not by_sn and len(sns) == 1 and isinstance(result, list) and result and isinstance(result[0], dict):
        by_sn[sns[0]] = result[0]

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
        """Execute one FoxESS API request and normalize API-level errors."""

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
        request_context = summarize_request_context(query, body)
        started = time.perf_counter()
        payload: dict[str, Any] = {}
        response_status: str | int = "n/a"

        try:
            async with self._session.request(
                method=method.upper(),
                url=url,
                params=query,
                json=body,
                headers=headers,
                timeout=timeout,
                ssl=REQUEST_VERIFY_SSL,
            ) as response:
                response_status = response.status
                raw_text = await response.text()
                try:
                    payload = json.loads(raw_text) if raw_text else {}
                except json.JSONDecodeError as exc:
                    LOGGER.debug(
                        "FoxESS API call method=%s path=%s context=%s status=%s errno=%s duration_ms=%s error=%s",
                        method.upper(),
                        path,
                        request_context,
                        response_status,
                        None,
                        int((time.perf_counter() - started) * 1000),
                        "invalid_json",
                    )
                    raise FoxessApiRequestError(
                        f"Invalid JSON response from {path}. status={response_status} body={raw_text[:300]}"
                    ) from exc
                LOGGER.debug(
                    "FoxESS API call method=%s path=%s context=%s status=%s errno=%s duration_ms=%s",
                    method.upper(),
                    path,
                    request_context,
                    response_status,
                    payload.get("errno"),
                    int((time.perf_counter() - started) * 1000),
                )
                if response_status >= 400:
                    raise FoxessApiRequestError(
                        f"HTTP {response_status} calling {path}: {json.dumps(payload, ensure_ascii=True)[:500]}"
                    )
        except aiohttp.ClientError as exc:
            LOGGER.debug(
                "FoxESS API call method=%s path=%s context=%s status=%s errno=%s duration_ms=%s error=%s",
                method.upper(),
                path,
                request_context,
                "client_error",
                payload.get("errno"),
                int((time.perf_counter() - started) * 1000),
                str(exc),
            )
            raise FoxessApiRequestError(f"Request to {path} failed: {exc}") from exc
        except asyncio.TimeoutError as exc:
            LOGGER.debug(
                "FoxESS API call method=%s path=%s context=%s status=%s errno=%s duration_ms=%s error=%s",
                method.upper(),
                path,
                request_context,
                "timeout",
                payload.get("errno"),
                int((time.perf_counter() - started) * 1000),
                "timeout",
            )
            raise FoxessApiRequestError(f"Request to {path} timed out") from exc

        errno = payload.get("errno")
        if errno not in (None, 0):
            message = str(payload.get("msg", "Unknown FoxESS API error"))
            lower_message = message.lower()
            if (
                "token" in lower_message
                or "auth" in lower_message
                or "signature" in lower_message
                or errno == 40256
            ):
                raise FoxessApiAuthError(message)
            raise FoxessApiRequestError(f"FoxESS API error errno={errno}: {message}")

        return payload

    async def async_list_devices(self, page: int = 1, page_size: int = 200) -> dict[str, Any]:
        """Return the raw device list payload plus the normalized device rows."""

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

    async def async_get_device_detail(self, sn: str) -> dict[str, Any]:
        """Return normalized device detail data for one serial number."""

        payload = await self._request("GET", ENDPOINT_DEVICE_DETAIL, query={"sn": sn})
        detail = extract_device_detail(payload, default_sn=sn)
        return {"raw": payload, "detail": detail}

    async def async_get_variable_catalog(self) -> dict[str, Any]:
        """Return the FoxESS variable catalog keyed by variable name."""

        payload = await self._request("GET", ENDPOINT_VARIABLE_CATALOG)
        catalog = normalize_variable_catalog_response(payload)
        return {"raw": payload, "variables": catalog}

    async def async_query_realtime(
        self,
        sns: list[str],
        variables: list[str] | None = None,
    ) -> dict[str, Any]:
        """Return realtime payloads keyed by device serial number."""

        body: dict[str, Any] = {"sns": sns}
        if variables:
            body["variables"] = variables
        payload = await self._request("POST", ENDPOINT_REALTIME_QUERY, body=body)
        by_sn = extract_realtime_by_sn(payload, sns)
        return {"raw": payload, "by_sn": by_sn}

    async def async_get_access_count(self) -> dict[str, Any]:
        """Return the current FoxESS public API quota snapshot."""

        payload = await self._request("GET", ENDPOINT_ACCESS_COUNT)
        result = _extract_result(payload)
        total = None
        remaining = None
        if isinstance(result, dict):
            total = result.get("total")
            remaining = result.get("remaining")
        return {"raw": payload, "total": total, "remaining": remaining}

    def load_local_schema_manifest(self) -> dict[str, Any]:
        """Load the repository's locally versioned FoxESS endpoint inventory, if present."""

        manifest_path = (
            self._integration_dir
            / SCHEMA_BASE_DIR
            / SCHEMA_VERSION_FOLDER
            / "001.foxess.endpoint_inventory.json"
        )
        if not manifest_path.exists():
            return {}
        return json.loads(manifest_path.read_text(encoding="utf-8"))
