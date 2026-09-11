from typing import Literal

from pydantic import BaseModel


class UsbPort(BaseModel):
    location: Literal["rear", "front"]
    type: str
    count: int


class BiosUpdate(BaseModel):
    version: str
    date: str | None = None
    changelog: str | None = None


class Motherboard(BaseModel):
    name: str
    manufacturer: str
    chipset: str
    socket: str
    form_factor: str
    memory_type: str
    memory_max_gb: int | None = None
    memory_max_speed_mhz: int | None = None
    memory_slots: int | None = None
    pcie_x16_slots: int | None = None
    m2_slots: int | None = None
    usb_ports: list[UsbPort] = []
    wifi_bluetooth: Literal["built-in", "optional module", "none"] = "none"
    lan_speed_gbps: float | None = None
    audio_codec: str | None = None
    bios_updates: list[BiosUpdate] = []
