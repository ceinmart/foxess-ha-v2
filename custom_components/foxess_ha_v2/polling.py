"""
Version: v0.1.4
Created at: 2026-04-19 10:13:52 -03:00
Created by: Codex / OpenAI
Project/Folder: C:\\tmp\\foxess-ha.v2\\foxess-ha-v2

Helpers for parsing FoxESS polling expressions and deciding when a device is due.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re


_POLLING_PATTERN = re.compile(r"^\s*(\d{1,2})h-(\d{1,2})h:(\d{1,4})m;(\d{1,4})m\s*$")


@dataclass(frozen=True)
class PollingPolicy:
    """Normalized representation of a per-device polling schedule."""

    start_hour: int
    end_hour: int
    inside_every_min: int
    outside_every_min: int


def parse_polling_expression(expression: str) -> PollingPolicy:
    """Parse the `5h-19h:1m;5m` syntax used by the integration options."""

    if not expression:
        raise ValueError("Empty polling expression")

    match = _POLLING_PATTERN.match(expression)
    if not match:
        raise ValueError("Invalid polling expression format")

    start_hour = int(match.group(1))
    end_hour = int(match.group(2))
    inside_every_min = int(match.group(3))
    outside_every_min = int(match.group(4))

    if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
        raise ValueError("Polling hour must be between 0 and 23")
    if start_hour == end_hour:
        raise ValueError("Polling window start and end hour cannot be equal")
    if inside_every_min < 1 or outside_every_min < 1:
        raise ValueError("Polling intervals must be >= 1 minute")

    return PollingPolicy(
        start_hour=start_hour,
        end_hour=end_hour,
        inside_every_min=inside_every_min,
        outside_every_min=outside_every_min,
    )


def _is_in_window(policy: PollingPolicy, now: datetime) -> bool:
    """Return whether `now` is inside the fast-polling time window."""

    hour = now.hour
    if policy.start_hour < policy.end_hour:
        return policy.start_hour <= hour < policy.end_hour
    return hour >= policy.start_hour or hour < policy.end_hour


def estimate_calls_per_day(policy: PollingPolicy) -> int:
    """Estimate the maximum number of polls per 24 hours for a policy."""

    if policy.start_hour < policy.end_hour:
        window_hours = policy.end_hour - policy.start_hour
    else:
        window_hours = (24 - policy.start_hour) + policy.end_hour

    window_minutes = window_hours * 60
    outside_minutes = 24 * 60 - window_minutes

    inside_calls = window_minutes // policy.inside_every_min
    outside_calls = outside_minutes // policy.outside_every_min
    return inside_calls + outside_calls


def _minute_bucket_start(when: datetime) -> datetime:
    """Normalize datetime to the start of its minute bucket."""
    return when.replace(second=0, microsecond=0)


def is_poll_due(policy: PollingPolicy, now_local: datetime, last_run_local: datetime | None) -> bool:
    """Return whether a device should be queried on the current coordinator tick."""

    interval = policy.inside_every_min if _is_in_window(policy, now_local) else policy.outside_every_min
    if last_run_local is None:
        return True
    # Compare minute buckets instead of raw seconds so a 1-minute policy does not
    # miss a due poll because the coordinator tick happened a few seconds early.
    now_bucket = _minute_bucket_start(now_local)
    last_bucket = _minute_bucket_start(last_run_local)
    elapsed_minutes = int((now_bucket - last_bucket).total_seconds() // 60)
    return elapsed_minutes >= interval
