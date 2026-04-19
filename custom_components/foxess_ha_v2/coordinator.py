"""
Version: v0.1.4
Created at: 2026-04-19 10:13:52 -03:00
Created by: Codex / OpenAI
Project/Folder: C:\\tmp\\foxess-ha.v2\\foxess-ha-v2

Central coordinator that batches realtime polling and throttles slower API calls.
"""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import FoxessApiAuthError, FoxessApiClient, FoxessApiRequestError
from .const import (
    ACCESS_COUNT_REFRESH_INTERVAL_MINUTES,
    CONF_DEVICES,
    CONF_POLLING_EXPRESSION,
    COORDINATOR_TICK_MINUTES,
    DEFAULT_POLLING_EXPRESSION,
    DEVICE_DETAIL_FALLBACK_REFRESH_INTERVAL_MINUTES,
    DEVICE_DETAIL_REFRESH_INTERVAL_MINUTES,
)
from .polling import is_poll_due, parse_polling_expression

LOGGER = logging.getLogger(__name__)


class FoxessDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that decides device polling per minute."""

    def __init__(self, hass: HomeAssistant, api_client: FoxessApiClient, config_entry) -> None:
        super().__init__(
            hass,
            logger=LOGGER,
            name="FoxESS HA v2 coordinator",
            update_interval=timedelta(minutes=COORDINATOR_TICK_MINUTES),
        )
        self._api_client = api_client
        self._config_entry = config_entry
        self._last_run_by_sn: dict[str, Any] = {}
        self._last_access_refresh = None
        self._last_access_count: dict[str, Any] | None = None
        self._last_realtime_by_sn: dict[str, dict[str, Any]] = {}
        self._last_detail_refresh = None
        self._last_detail_refresh_by_sn: dict[str, Any] = {}
        self._last_device_detail_by_sn: dict[str, dict[str, Any]] = {}

    def _detail_refresh_due(self, now_local, sn: str) -> bool:
        """Return whether a device detail fallback refresh is due for one serial number."""

        last_refresh = self._last_detail_refresh_by_sn.get(sn)
        if last_refresh is None:
            return True
        return now_local - last_refresh >= timedelta(minutes=DEVICE_DETAIL_FALLBACK_REFRESH_INTERVAL_MINUTES)

    async def _async_update_data(self) -> dict[str, Any]:
        """Refresh due realtime payloads plus slower detail and quota snapshots."""

        now_local = dt_util.now()
        devices = self._config_entry.data.get(CONF_DEVICES, {})
        realtime_by_sn: dict[str, dict[str, Any]] = {}
        due_sns: list[str] = []
        detail_targets: set[str] = set()

        for sn, device_cfg in devices.items():
            expression = device_cfg.get(CONF_POLLING_EXPRESSION, DEFAULT_POLLING_EXPRESSION)
            try:
                policy = parse_polling_expression(expression)
            except ValueError:
                policy = parse_polling_expression(DEFAULT_POLLING_EXPRESSION)

            last_run = self._last_run_by_sn.get(sn)
            if is_poll_due(policy, now_local, last_run):
                due_sns.append(sn)

        LOGGER.debug(
            "Coordinator tick entry_id=%s devices=%s due=%s",
            self._config_entry.entry_id,
            len(devices),
            len(due_sns),
        )

        should_refresh_detail_snapshot = False
        if self._last_detail_refresh is None:
            should_refresh_detail_snapshot = True
        else:
            should_refresh_detail_snapshot = now_local - self._last_detail_refresh >= timedelta(
                minutes=DEVICE_DETAIL_REFRESH_INTERVAL_MINUTES
            )
        if should_refresh_detail_snapshot:
            detail_targets.update(devices.keys())

        try:
            if due_sns:
                realtime_payload = await self._api_client.async_query_realtime(due_sns)
                realtime_by_sn = realtime_payload.get("by_sn", {})

                missing_sns = [sn for sn in due_sns if sn not in realtime_by_sn]
                if missing_sns:
                    LOGGER.debug("Coordinator grouped response missing %s devices", len(missing_sns))
                for sn in missing_sns:
                    # Retry missing devices individually because FoxESS grouped responses
                    # can omit one serial number even when the request itself succeeds.
                    single_payload = await self._api_client.async_query_realtime([sn])
                    single_by_sn = single_payload.get("by_sn", {})
                    if sn in single_by_sn:
                        realtime_by_sn[sn] = single_by_sn[sn]
                    elif self._detail_refresh_due(now_local, sn):
                        detail_targets.add(sn)

                for sn in due_sns:
                    self._last_run_by_sn[sn] = now_local

                if realtime_by_sn:
                    self._last_realtime_by_sn.update(realtime_by_sn)
                    LOGGER.debug("Coordinator cached realtime payload for %s devices", len(self._last_realtime_by_sn))

            if detail_targets:
                detail_refresh_success = False
                for sn in sorted(detail_targets):
                    try:
                        detail_payload = await self._api_client.async_get_device_detail(sn)
                    except FoxessApiAuthError:
                        raise
                    except FoxessApiRequestError:
                        LOGGER.debug("Coordinator keeping cached device detail for sn=%s after detail refresh failure", sn)
                        continue

                    detail = detail_payload.get("detail", {})
                    if detail:
                        detail_with_meta = dict(detail)
                        detail_with_meta["_fetched_at"] = now_local.isoformat()
                        self._last_device_detail_by_sn[sn] = detail_with_meta
                        self._last_detail_refresh_by_sn[sn] = now_local
                        detail_refresh_success = True

                if should_refresh_detail_snapshot and detail_refresh_success:
                    self._last_detail_refresh = now_local

            should_refresh_access = False
            if self._last_access_refresh is None:
                should_refresh_access = True
            else:
                delta = now_local - self._last_access_refresh
                should_refresh_access = delta >= timedelta(minutes=ACCESS_COUNT_REFRESH_INTERVAL_MINUTES)

            if should_refresh_access:
                # Quota data changes more slowly than realtime telemetry, so we keep it
                # on its own refresh interval to reduce unnecessary API usage.
                self._last_access_count = await self._api_client.async_get_access_count()
                self._last_access_refresh = now_local
                LOGGER.debug("Coordinator refreshed access count snapshot")
        except FoxessApiAuthError as exc:
            raise ConfigEntryAuthFailed(str(exc)) from exc
        except FoxessApiRequestError as exc:
            raise UpdateFailed(str(exc)) from exc

        return {
            "updated_at": now_local.isoformat(),
            "due_sns": due_sns,
            "realtime_by_sn": dict(self._last_realtime_by_sn),
            "device_detail_by_sn": dict(self._last_device_detail_by_sn),
            "access_count": self._last_access_count or {},
        }
