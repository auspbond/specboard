from schemas import Motherboard, PcieSlot, M2Slot, UsbPort, AudioJack, VideoPort
from spec_merger import has_gaps, merge, _entry_key, _union_lists


class TestHasGaps:
    def test_no_gaps(self):
        board = Motherboard(
            name="Test Board",
            manufacturer="ASUS",
            chipset="Z790",
            socket="LGA1700",
            form_factor="ATX",
            memory_type="DDR5",
            memory_max_gb=128,
            memory_max_speed_mhz=7200,
            memory_slots=4,
            wifi_bluetooth="built-in",
            lan_speed_gbps=2.5,
            audio_codec="ALC4080",
            video_ports=[VideoPort(type="HDMI 2.1", quantity=1)],
            pcie_slots=[PcieSlot(type="PCIe 5.0 x16", quantity=1)],
            m2_slots=[M2Slot(type="M.2 2280 Gen5x4", quantity=1)],
            usb_ports=[UsbPort(location="rear", type="USB 3.2 Gen2", quantity=2)],
            audio_jacks=[AudioJack(location="rear", type="Line Out", quantity=1)],
        )
        assert has_gaps(board) == []

    def test_null_fields_are_gaps(self):
        board = Motherboard(name="Test", chipset=None, socket=None)
        gaps = has_gaps(board)
        assert "chipset" in gaps
        assert "socket" in gaps

    def test_empty_lists_are_gaps(self):
        board = Motherboard(name="Test")
        gaps = has_gaps(board)
        assert "pcie_slots" in gaps
        assert "usb_ports" in gaps

    def test_name_present_not_a_gap(self):
        board = Motherboard(name="Test Board")
        assert "name" not in has_gaps(board)


class TestEntryKey:
    def test_usb_ports_location_keyed(self):
        entry = {"location": "rear", "type": "USB 3.2 Gen2", "quantity": 2}
        assert _entry_key("usb_ports", entry) == ("rear", "USB 3.2 Gen2", 2)

    def test_audio_jacks_location_keyed(self):
        entry = {"location": "front", "type": "Headphone", "quantity": 1}
        assert _entry_key("audio_jacks", entry) == ("front", "Headphone", 1)

    def test_pcie_slots_type_keyed(self):
        entry = {"type": "PCIe 5.0 x16", "quantity": 1}
        assert _entry_key("pcie_slots", entry) == ("PCIe 5.0 x16", 1)

    def test_m2_slots_type_keyed(self):
        entry = {"type": "M.2 2280 Gen5x4", "quantity": 2}
        assert _entry_key("m2_slots", entry) == ("M.2 2280 Gen5x4", 2)

    def test_video_ports_type_keyed(self):
        entry = {"type": "HDMI 2.1", "quantity": 1}
        assert _entry_key("video_ports", entry) == ("HDMI 2.1", 1)


class TestUnionLists:
    def test_no_overlap(self):
        base = [{"type": "PCIe 5.0 x16", "quantity": 1}]
        other = [{"type": "PCIe 4.0 x4", "quantity": 1}]
        result = _union_lists("pcie_slots", base, other)
        assert len(result) == 2

    def test_exact_dedup(self):
        entry = {"type": "HDMI 2.1", "quantity": 1}
        result = _union_lists("video_ports", [entry], [entry])
        assert len(result) == 1

    def test_different_quantity_not_deduped(self):
        base = [{"type": "HDMI 2.1", "quantity": 1}]
        other = [{"type": "HDMI 2.1", "quantity": 2}]
        result = _union_lists("video_ports", base, other)
        assert len(result) == 2

    def test_location_matters_for_usb(self):
        rear = {"location": "rear", "type": "USB 3.2 Gen2", "quantity": 2}
        front = {"location": "front", "type": "USB 3.2 Gen2", "quantity": 2}
        result = _union_lists("usb_ports", [rear], [front])
        assert len(result) == 2

    def test_preserves_base_order(self):
        base = [
            {"type": "PCIe 5.0 x16", "quantity": 1},
            {"type": "PCIe 4.0 x16", "quantity": 1},
        ]
        other = [{"type": "PCIe 3.0 x1", "quantity": 2}]
        result = _union_lists("pcie_slots", base, other)
        assert result[0]["type"] == "PCIe 5.0 x16"
        assert result[1]["type"] == "PCIe 4.0 x16"
        assert result[2]["type"] == "PCIe 3.0 x1"


class TestMerge:
    def test_fills_null_from_second(self):
        a = Motherboard(name="Board", chipset=None)
        b = Motherboard(chipset="Z790")
        result = merge([a, b])
        assert result.name == "Board"
        assert result.chipset == "Z790"

    def test_first_value_wins_for_scalars(self):
        a = Motherboard(chipset="Z790")
        b = Motherboard(chipset="X870")
        result = merge([a, b])
        assert result.chipset == "Z790"

    def test_none_overwritten_by_wifi(self):
        a = Motherboard(wifi_bluetooth="none")
        b = Motherboard(wifi_bluetooth="built-in")
        result = merge([a, b])
        assert result.wifi_bluetooth == "built-in"

    def test_none_not_overwritten_by_none(self):
        a = Motherboard(wifi_bluetooth="none")
        b = Motherboard(wifi_bluetooth="none")
        result = merge([a, b])
        assert result.wifi_bluetooth == "none"

    def test_lists_unioned(self):
        a = Motherboard(
            pcie_slots=[PcieSlot(type="PCIe 5.0 x16", quantity=1)]
        )
        b = Motherboard(
            pcie_slots=[
                PcieSlot(type="PCIe 5.0 x16", quantity=1),
                PcieSlot(type="PCIe 4.0 x4", quantity=2),
            ]
        )
        result = merge([a, b])
        assert len(result.pcie_slots) == 2

    def test_three_way_merge(self):
        a = Motherboard(name="Board", chipset=None, socket=None)
        b = Motherboard(chipset="Z790", socket=None)
        c = Motherboard(socket="LGA1700")
        result = merge([a, b, c])
        assert result.name == "Board"
        assert result.chipset == "Z790"
        assert result.socket == "LGA1700"
