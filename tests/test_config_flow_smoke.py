"""
Version: v0.1.4
Created at: 2026-04-19 10:13:52 -03:00
Created by: Codex / OpenAI
Project/Folder: C:\\tmp\\foxess-ha.v2\\foxess-ha-v2
"""

import pytest

homeassistant = pytest.importorskip("homeassistant")

from custom_components.foxess_ha_v2.__init__ import _get_remaining_calls_entity_id_update
from custom_components.foxess_ha_v2.const import (
    LEGACY_REMAINING_CALLS_ENTITY_ID,
    REMAINING_CALLS_ENTITY_ID,
)
from custom_components.foxess_ha_v2.config_flow import _field_name_for_device, _field_poll_for_device


def test_dynamic_field_names():
    assert _field_name_for_device("SN123") == "device_name__SN123"
    assert _field_poll_for_device("SN123") == "device_poll__SN123"


def test_remaining_calls_entity_id_update_for_legacy_entity():
    assert _get_remaining_calls_entity_id_update(
        LEGACY_REMAINING_CALLS_ENTITY_ID,
        target_entity_exists=False,
    ) == {"new_entity_id": REMAINING_CALLS_ENTITY_ID}


def test_remaining_calls_entity_id_update_skips_when_target_exists():
    assert (
        _get_remaining_calls_entity_id_update(
            LEGACY_REMAINING_CALLS_ENTITY_ID,
            target_entity_exists=True,
        )
        is None
    )


def test_remaining_calls_entity_id_update_skips_non_legacy_entity():
    assert _get_remaining_calls_entity_id_update(
        REMAINING_CALLS_ENTITY_ID,
        target_entity_exists=False,
    ) is None
