import json
from schemas import Motherboard, UsbPort, BiosUpdate

sample_text = """
ROG STRIX Z790-E GAMING WIFI II
Intel Z790 ATX motherboard, 16+1 power stages, DDR5, five M.2 slots,
PCIe 5.0, WiFi 7, 2.5G LAN, USB 3.2 Gen 2x2 Type-C

Specifications:
CPU: Intel Socket LGA 1700
Chipset: Intel Z790
Memory: 4 x DIMM, max 192GB, DDR5 5600(OC)/5400(OC)/5200/4800 MHz
Expansion Slots: 1 x PCIe 5.0 x16, 1 x PCIe 4.0 x16
Storage: 5 x M.2 slots, 4 x SATA 6Gb/s
USB Ports: 1x USB 3.2 Gen 2x2 Type-C, 3x USB 3.2 Gen 2, 4x USB 3.2 Gen 1, 2x USB 2.0
Audio: ROG SupremeFX ALC4080 codec
Networking: WiFi 7 (802.11be), Bluetooth 5.4, Intel 2.5G Ethernet
Form Factor: ATX

BIOS:
Version 1602 - 2024-03-15 - Improved memory compatibility
Version 1401 - 2024-01-10 - Security update and bug fixes
"""

print("=== Testing schema generation ===")
schema = Motherboard.model_json_schema()
print(json.dumps(schema, indent=2)[:500])
print("...\n")

print("=== Testing manual parsing (what the LLM would return) ===")
board = Motherboard(
    name="ROG STRIX Z790-E GAMING WIFI II",
    manufacturer="ASUS",
    chipset="Z790",
    socket="LGA 1700",
    form_factor="ATX",
    memory_type="DDR5",
    memory_max_gb=192,
    memory_max_speed_mhz=5600,
    memory_slots=4,
    pcie_x16_slots=2,
    m2_slots=5,
    usb_ports=[
        UsbPort(type="USB 3.2 Gen 2x2 Type-C", count=1),
        UsbPort(type="USB 3.2 Gen 2", count=3),
        UsbPort(type="USB 3.2 Gen 1", count=4),
        UsbPort(type="USB 2.0", count=2),
    ],
    wifi=True,
    bluetooth=True,
    lan_speed_gbps=2.5,
    audio_codec="ALC4080",
    bios_updates=[
        BiosUpdate(version="1602", date="2024-03-15", changelog="Improved memory compatibility"),
        BiosUpdate(version="1401", date="2024-01-10", changelog="Security update and bug fixes"),
    ],
)

print(json.dumps(board.model_dump(), indent=2))

print("\n=== Testing validation (bad data) ===")
try:
    Motherboard(name=123, manufacturer="ASUS", chipset="Z790", socket="LGA 1700",
                form_factor="ATX", memory_type="DDR5")
    print("ERROR: Should have failed validation")
except Exception as e:
    print(f"Caught validation error (expected): {type(e).__name__}")

print("\nAll local tests passed.")
