"""
Versao: v0.1.0
Data/hora de criacao: 2026-04-14 16:05:00
Criado por: Codex / OpenAI
Projeto/Pasta: C:\\tmp\\foxess-ha.v2
"""

import hashlib

from custom_components.foxess_ha_v2.api import (
    extract_realtime_by_sn,
    extract_realtime_variable_records,
    extract_scalar_variable_names,
    normalize_variable_catalog_response,
    generate_signature,
)


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
