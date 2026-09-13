from schemas import Motherboard, PcieSlot, UsbPort, VideoPort
from comparator import _fmt, _entry_label, _compare_list


class TestFmt:
    def test_none_becomes_dash(self):
        assert _fmt(None) == "-"

    def test_string_passthrough(self):
        assert _fmt("Z790") == "Z790"

    def test_int_to_string(self):
        assert _fmt(4) == "4"

    def test_float_to_string(self):
        assert _fmt(2.5) == "2.5"


class TestEntryLabel:
    def test_type_and_quantity(self):
        entry = {"type": "PCIe 5.0 x16", "quantity": 1}
        assert _entry_label(entry) == "PCIe 5.0 x16 x1"

    def test_with_location(self):
        entry = {"location": "rear", "type": "USB 3.2 Gen2", "quantity": 2}
        assert _entry_label(entry) == "rear USB 3.2 Gen2 x2"

    def test_front_location(self):
        entry = {"location": "front", "type": "Headphone", "quantity": 1}
        assert _entry_label(entry) == "front Headphone x1"


class TestCompareList:
    def test_common_entries(self, caplog):
        import logging
        log = logging.getLogger("specboard")
        log.setLevel(logging.INFO)
        if not log.handlers:
            log.addHandler(logging.StreamHandler())

        list_a = [{"type": "HDMI 2.1", "quantity": 1}]
        list_b = [{"type": "HDMI 2.1", "quantity": 1}]
        key_fn = lambda e: (e["type"], e["quantity"])

        with caplog.at_level(logging.INFO, logger="specboard"):
            _compare_list("Video Ports", list_a, list_b, key_fn, "Board A", "Board B")

        output = caplog.text
        assert "Both:" in output
        assert "(identical)" in output

    def test_only_a_entries(self, caplog):
        import logging
        log = logging.getLogger("specboard")
        log.setLevel(logging.INFO)
        if not log.handlers:
            log.addHandler(logging.StreamHandler())

        list_a = [{"type": "HDMI 2.1", "quantity": 1}]
        list_b = []
        key_fn = lambda e: (e["type"], e["quantity"])

        with caplog.at_level(logging.INFO, logger="specboard"):
            _compare_list("Video Ports", list_a, list_b, key_fn, "Board A", "Board B")

        output = caplog.text
        assert "Board A:" in output

    def test_both_empty(self, caplog):
        import logging
        log = logging.getLogger("specboard")
        log.setLevel(logging.INFO)
        if not log.handlers:
            log.addHandler(logging.StreamHandler())

        key_fn = lambda e: (e["type"], e["quantity"])

        with caplog.at_level(logging.INFO, logger="specboard"):
            _compare_list("Video Ports", [], [], key_fn, "Board A", "Board B")

        assert "none on either board" in caplog.text
