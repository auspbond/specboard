import pytest
from extractor import _parse_json


class TestParseJson:
    def test_plain_json(self):
        raw = '{"name": "Board", "chipset": "Z790"}'
        result = _parse_json(raw)
        assert result["name"] == "Board"
        assert result["chipset"] == "Z790"

    def test_json_in_markdown_fence(self):
        raw = '```json\n{"name": "Board"}\n```'
        result = _parse_json(raw)
        assert result["name"] == "Board"

    def test_fence_without_language(self):
        raw = '```\n{"name": "Board"}\n```'
        result = _parse_json(raw)
        assert result["name"] == "Board"

    def test_json_with_preamble(self):
        raw = 'Here is the extracted data:\n{"name": "Board", "chipset": "Z790"}'
        result = _parse_json(raw)
        assert result["name"] == "Board"

    def test_json_with_trailing_text(self):
        raw = '{"name": "Board"}\nLet me know if you need changes.'
        result = _parse_json(raw)
        assert result["name"] == "Board"

    def test_whitespace_stripped(self):
        raw = '  \n  {"name": "Board"}  \n  '
        result = _parse_json(raw)
        assert result["name"] == "Board"

    def test_invalid_json_raises(self):
        with pytest.raises(Exception):
            _parse_json("not json at all")

    def test_nested_objects(self):
        raw = '{"name": "Board", "pcie_slots": [{"type": "PCIe 5.0 x16", "quantity": 1}]}'
        result = _parse_json(raw)
        assert len(result["pcie_slots"]) == 1
        assert result["pcie_slots"][0]["type"] == "PCIe 5.0 x16"
