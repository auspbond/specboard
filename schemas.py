from typing import Literal

from pydantic import BaseModel


class PcieSlot(BaseModel):
    type: str
    quantity: int


class M2Slot(BaseModel):
    type: str
    quantity: int


class UsbPort(BaseModel):
    location: Literal["rear", "front"]
    type: str
    quantity: int


class AudioJack(BaseModel):
    location: Literal["rear", "front"]
    type: str
    quantity: int


class VideoPort(BaseModel):
    type: str
    quantity: int


class Accessory(BaseModel):
    name: str
    quantity: int


class Motherboard(BaseModel):
    name: str | None = None
    manufacturer: str | None = None
    chipset: str | None = None
    socket: str | None = None
    form_factor: str | None = None
    video_ports: list[VideoPort] = []
    memory_type: str | None = None
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
    accessories: list[Accessory] = []
