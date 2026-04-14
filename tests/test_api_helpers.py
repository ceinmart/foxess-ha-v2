"""
Versao: v0.1.0
Data/hora de criacao: 2026-04-14 16:05:00
Criado por: Codex / OpenAI
Projeto/Pasta: C:\\tmp\\foxess-ha.v2
"""

from custom_components.foxess_ha_v2.api import (
    extract_realtime_by_sn,
    extract_scalar_variable_names,
    generate_signature,
)


def test_generate_signature_matches_reference_string():
    signature = generate_signature("/op/v0/device/list", "token123", "1700000000000")
    assert len(signature) == 32
    assert signature.isalnum()


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


def test_extract_scalar_variable_names_nested():
    payload = {"result": {"data": [{"sn": "A1", "pvPower": 100, "nested": {"soc": 90}}]}}
    variables = extract_scalar_variable_names(payload)
    assert "sn" in variables
    assert "pvPower" in variables
    assert "soc" in variables
