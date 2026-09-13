import logging

from schemas import Motherboard

log = logging.getLogger("specboard")

_SCALAR_FIELDS = [
    ("name", "Name"),
    ("manufacturer", "Manufacturer"),
    ("chipset", "Chipset"),
    ("socket", "Socket"),
    ("form_factor", "Form Factor"),
    ("memory_type", "Memory Type"),
    ("memory_slots", "Memory Slots"),
    ("memory_max_gb", "Max Memory (GB)"),
    ("memory_max_speed_mhz", "Max Speed (MHz)"),
    ("wifi_bluetooth", "WiFi/BT"),
    ("lan_speed_gbps", "LAN (Gbps)"),
    ("audio_codec", "Audio Codec"),
]

_LIST_FIELDS = [
    ("video_ports", "Video Ports", lambda e: (e["type"], e["quantity"])),
    ("pcie_slots", "PCIe Slots", lambda e: (e["type"], e["quantity"])),
    ("m2_slots", "M.2 Slots", lambda e: (e["type"], e["quantity"])),
    ("usb_ports", "USB Ports", lambda e: (e["location"], e["type"], e["quantity"])),
    ("audio_jacks", "Audio Jacks", lambda e: (e["location"], e["type"], e["quantity"])),
]


def compare(a: Motherboard, b: Motherboard):
    da = a.model_dump()
    db = b.model_dump()

    name_a = da.get("name") or "Board A"
    name_b = db.get("name") or "Board B"

    col = max(len(name_a), len(name_b), 20)
    header = f"{'':22s}  {name_a:<{col}s}  {name_b}"
    log.info("\n%s", header)
    log.info("%s", "-" * len(header))

    for field, label in _SCALAR_FIELDS:
        va = _fmt(da.get(field))
        vb = _fmt(db.get(field))
        marker = "" if va == vb else "  *"
        log.info("%-22s  %-{col}s  %s%s".replace("{col}", str(col)), label, va, vb, marker)

    for field, label, key_fn in _LIST_FIELDS:
        _compare_list(label, da.get(field, []), db.get(field, []), key_fn, name_a, name_b)


def _fmt(val) -> str:
    if val is None:
        return "-"
    return str(val)


def _entry_label(entry: dict) -> str:
    parts = []
    if "location" in entry:
        parts.append(entry["location"])
    parts.append(entry["type"])
    parts.append(f"x{entry['quantity']}")
    return " ".join(parts)


def _compare_list(label: str, list_a: list[dict], list_b: list[dict],
                  key_fn, name_a: str, name_b: str):
    set_a = {key_fn(e) for e in list_a}
    set_b = {key_fn(e) for e in list_b}

    common = set_a & set_b
    only_a = set_a - set_b
    only_b = set_b - set_a

    log.info("\n%s:", label)

    if not set_a and not set_b:
        log.info("  (none on either board)")
        return

    if common:
        entries = [_entry_label(e) for e in list_a if key_fn(e) in common]
        for e in entries:
            log.info("  Both:      %s", e)
    if only_a:
        entries = [_entry_label(e) for e in list_a if key_fn(e) in only_a]
        for e in entries:
            log.info("  %-10s %s", name_a + ":", e)
    if only_b:
        entries = [_entry_label(e) for e in list_b if key_fn(e) in only_b]
        for e in entries:
            log.info("  %-10s %s", name_b + ":", e)
    if not only_a and not only_b:
        log.info("  (identical)")
