"""
Versao: v0.1.0
Data/hora de criacao: 2026-04-14 16:05:00
Criado por: Codex / OpenAI
Projeto/Pasta: C:\\tmp\\foxess-ha.v2
"""

from datetime import datetime, timedelta

import pytest

from custom_components.foxess_ha_v2.polling import (
    estimate_calls_per_day,
    is_poll_due,
    parse_polling_expression,
)


def test_parse_polling_expression_valid():
    policy = parse_polling_expression("5h-19h:1m;5m")
    assert policy.start_hour == 5
    assert policy.end_hour == 19
    assert policy.inside_every_min == 1
    assert policy.outside_every_min == 5


def test_parse_polling_expression_invalid():
    with pytest.raises(ValueError):
        parse_polling_expression("abc")


def test_estimate_calls_per_day():
    policy = parse_polling_expression("5h-19h:1m;5m")
    assert estimate_calls_per_day(policy) == 960


def test_is_poll_due():
    policy = parse_polling_expression("5h-19h:1m;5m")
    now = datetime(2026, 4, 14, 10, 0, 0)
    assert is_poll_due(policy, now, None)
    assert not is_poll_due(policy, now, now - timedelta(seconds=20))
    assert is_poll_due(policy, now, now - timedelta(minutes=2))


def test_is_poll_due_uses_minute_bucket_to_avoid_subsecond_skip():
    policy = parse_polling_expression("5h-19h:1m;5m")
    last_run = datetime(2026, 4, 17, 13, 35, 52, 107000)
    now = datetime(2026, 4, 17, 13, 36, 52, 99000)
    assert is_poll_due(policy, now, last_run)


def test_is_poll_due_respects_outside_window_interval_with_minute_bucket():
    policy = parse_polling_expression("5h-19h:1m;5m")
    now = datetime(2026, 4, 14, 22, 10, 5)
    assert not is_poll_due(policy, now, datetime(2026, 4, 14, 22, 6, 59))
    assert is_poll_due(policy, now, datetime(2026, 4, 14, 22, 5, 59))
