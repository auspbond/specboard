from typing import Literal

from pydantic import BaseModel


class PcieSlot(BaseModel):
    type: str
    count: int


class M2Slot(BaseModel):
    type: str
    count: int


class UsbPort(BaseModel):
    location: Literal["rear", "front"]
    type: str
    count: int


class AudioJack(BaseModel):
    location: Literal["rear", "front"]
    type: str
    count: int


class VideoPort(BaseModel):
    type: str
    count: int


class Motherboard(BaseModel):
    name: str
    manufacturer: str
    chipset: str
    socket: str
    form_factor: str
    graphics_chip: str | None = None
    video_ports: list[VideoPort] = []
    memory_type: str
    memory_max_gb: int | None = None
    memory_max_speed_mhz: int | None = None
    memory_slots: int | None = None
    pcie_slots: list[PcieSlot] = []
    m2_slots: list[M2Slot] = []
    usb_ports: list[UsbPort] = []
    wifi_bluetooth: Literal["built-in", "optional module", "none"] = "none"
    audio_jacks: list[AudioJack] = []
    lan_speed_gbps: float | None = None
    audio_codec: str | None = None
