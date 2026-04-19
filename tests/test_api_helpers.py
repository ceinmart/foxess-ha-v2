"""
Version: v0.1.4
Created at: 2026-04-19 10:13:52 -03:00
Created by: Codex / OpenAI
Project/Folder: C:\\tmp\\foxess-ha.v2\\foxess-ha-v2
"""

import hashlib

from custom_components.foxess_ha_v2.api import (
    extract_device_detail,
    extract_realtime_by_sn,
    extract_realtime_variable_records,
    extract_scalar_variable_names,
    normalize_variable_catalog_response,
    generate_signature,
    summarize_request_context,
)
from custom_components.foxess_ha_v2.value_mappings import coerce_int_code, map_device_status, map_running_state


def test_generate_signature_matches_reference_string():
    signature = generate_signature("/op/v0/device/list", "token123", "1700000000000")
    assert len(signature) == 32
    assert signature.isalnum()


def test_generate_signature_uses_literal_backslash_rn():
    expected_raw = r"/op/v0/device/list\r\ntoken123\r\n1700000000000"
    expected = hashlib.md5(expected_raw.encode("utf-8")).hexdigest()
    assert generate_signature("/op/v0/device/list", "token123", "1700000000000") == expected


def test_extract_realtime_by_sn_from_list():
    payload = {
        "result": {
            "data": [
                {"sn": "A1", "pvPower": 100},
                {"sn": "A2", "pvPower": 200},
            ]
        }
    }
    by_sn = extract_realtime_by_sn(payload, ["A1", "A2"])
    assert by_sn["A1"]["pvPower"] == 100
    assert by_sn["A2"]["pvPower"] == 200


def test_extract_realtime_by_sn_single_fallback():
    payload = {"result": {"pvPower": 123}}
    by_sn = extract_realtime_by_sn(payload, ["ONLY1"])
    assert by_sn["ONLY1"]["pvPower"] == 123


def test_extract_realtime_by_sn_result_list_with_device_sn():
    payload = {
        "errno": 0,
        "result": [
            {
                "deviceSN": "SN1",
                "time": "2026-01-01 10:00:00",
                "datas": [{"variable": "pvPower", "value": 1.5, "unit": "kW"}],
            }
        ],
    }
    by_sn = extract_realtime_by_sn(payload, ["SN1"])
    assert by_sn["SN1"]["deviceSN"] == "SN1"
    assert by_sn["SN1"]["datas"][0]["variable"] == "pvPower"


def test_extract_scalar_variable_names_nested():
    payload = {"result": {"data": [{"sn": "A1", "pvPower": 100, "nested": {"soc": 90}}]}}
    variables = extract_scalar_variable_names(payload)
    assert "sn" in variables
    assert "pvPower" in variables
    assert "soc" in variables


def test_extract_realtime_variable_records_from_datas():
    payload = {
        "deviceSN": "SN1",
        "time": "2026-01-01 10:00:00",
        "datas": [
            {"variable": "pvPower", "value": 1.2, "unit": "kW", "name": "PV Power"},
            {"variable": "todayYield", "value": 7.5, "unit": "kWh", "name": "Today Yield"},
        ],
    }
    records = extract_realtime_variable_records(payload)
    assert records["pvPower"]["value"] == 1.2
    assert records["pvPower"]["unit"] == "kW"
    assert records["todayYield"]["name"] == "Today Yield"


def test_normalize_variable_catalog_response_list_datas_shape():
    payload = {
        "errno": 0,
        "result": [
            {
                "datas": [
                    {"variable": "pvPower", "unit": "kW", "name": "PV Power"},
                    {"variable": "todayYield", "unit": "kWh", "name": "Today Yield"},
                ]
            }
        ],
    }
    catalog = normalize_variable_catalog_response(payload)
    assert "pvPower" in catalog
    assert catalog["pvPower"]["unit"] == "kW"
    assert catalog["todayYield"]["name"]["en"] == "Today Yield"


def test_summarize_request_context_includes_sn_and_variable_count():
    context = summarize_request_context(
        query={"sn": "SN-DETAIL"},
        body={"sns": ["SN1", "SN2", "SN3", "SN4"], "variables": ["pvPower", "runningState"]},
    )
    assert "sn=SN-DETAIL" in context
    assert "sns=SN1,SN2,SN3,+1" in context
    assert "variables=2" in context


def test_extract_device_detail_returns_result_object():
    payload = {
        "errno": 0,
        "result": {
            "deviceSN": "SN1",
            "deviceType": "Q1-2500-E",
            "masterVersion": "1.22",
            "status": 1,
        },
    }
    detail = extract_device_detail(payload)
    assert detail["deviceSN"] == "SN1"
    assert detail["deviceType"] == "Q1-2500-E"
    assert detail["status"] == 1


def test_map_device_status_translates_numeric_codes():
    assert coerce_int_code("3") == 3
    assert map_device_status(1) == "online"
    assert map_device_status("2") == "breakdown"


def test_map_running_state_translates_numeric_codes():
    assert map_running_state(163) == "on-grid"
    assert map_running_state("170") == "illegal"
