import json
import logging
import re
from types import SimpleNamespace

import anthropic

log = logging.getLogger("specboard")

import cache
from schemas import Motherboard


# ── Constants ──────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You extract structured motherboard specifications from raw text. "
    "Return ONLY valid JSON matching the provided schema. "
    "No markdown, no explanation, just the JSON object. "
    "If a field cannot be determined from the text, use null.\n\n"
    "Field guidance:\n"
    "- name: The board's model name without the manufacturer "
    "(e.g. 'ROG STRIX Z790-E Gaming WiFi', not 'ASUS ROG STRIX Z790-E Gaming WiFi'). "
    "The manufacturer goes in the manufacturer field.\n"
    "- socket: Just the socket type itself, no extra words "
    "(e.g. 'LGA1700', 'AM5', 'LGA1851'). Not 'Socket AM5' or 'Intel LGA1700'.\n"
    "- chipset: Manufacturer followed by chipset number "
    "(e.g. 'Intel Z790', 'AMD X670', 'AMD B650', 'Intel B760'). "
    "Always include the manufacturer.\n"
    "- memory_type: Just the speed category "
    "(e.g. 'DDR5', 'DDR4'). No speeds, frequencies, or other details.\n"
    "- audio_codec: Manufacturer followed by chip model "
    "(e.g. 'Realtek ALC4080', 'ESS ES9038Q2M'). Realtek chips start with 'ALC', "
    "ESS chips start with 'ES'. Always include the manufacturer. "
    "Do NOT guess the chip model — if the spec only says 'Realtek' or 'ESS' "
    "without a specific model number, just write 'Realtek' or 'ESS'.\n"
    "- video_ports: List each video output port as type and version only "
    "(e.g. 'HDMI 2.1', 'DisplayPort 1.4', 'VGA', 'DVI-D', 'USB4', "
    "'USB 20Gbps Type-C'). No resolution, refresh rate, alt mode notes, "
    "or other parenthetical details.\n"
    "- pcie_slots: List each distinct PCIe slot type with its count. "
    "Include the PCIe generation, physical slot size, and actual bandwidth mode "
    "when they differ. A slot that is physically x16 but electrically wired at x4 "
    "should be 'PCIe 4.0 x16 (x4 mode)'. Slots that share bandwidth or change "
    "mode depending on other slot usage should note that too, e.g. "
    "'PCIe 4.0 x16 (x8/x4 mode)'. A full-bandwidth slot is just 'PCIe 5.0 x16'.\n"
    "- m2_slots: List each distinct M.2 slot type with its count. "
    "Use the verbal generation format: 'M.2 2280 Gen5x4', 'M.2 2280 Gen4x4'. "
    "If a slot supports SATA, append it: 'M.2 2280 Gen4x4/SATA'. "
    "Always use Gen<number>x<lanes> (e.g. Gen5x4, Gen4x4, Gen3x2), not 'PCIe 5.0 x4'. "
    "Always include the form factor (22110, 2280, 2260, 2242, 2230). If a slot "
    "supports multiple form factors, list only the largest numeric one "
    "(e.g. 22110 > 2280 > 2242 > 2230). "
    "Include M.2 Key E WiFi/BT slots too — they are typically 2230 form factor "
    "(e.g. 'M.2 2230 Key E').\n"
    "- usb_ports: Only include rear panel (back I/O) USB ports. "
    "Ignore front panel headers and internal connectors entirely. "
    "Only include the connector type if it is NOT Type-A. Type-A is the "
    "default — omit it (e.g. 'USB 3.2 Gen2', not 'USB 3.2 Gen2 Type-A'). "
    "Always include Type-C when it is Type-C (e.g. 'USB 3.2 Gen2x2 Type-C'). "
    "Do NOT guess the USB generation. If the spec gives a bandwidth "
    "(e.g. '5Gbps', '10Gbps', '20Gbps') but not a generation, record the "
    "bandwidth instead (e.g. 'USB 5Gbps', 'USB 10Gbps Type-C'). Only use "
    "Gen labels (Gen1, Gen2, Gen2x2) when the spec explicitly states them. "
    "USB 2 ports are always written as 'USB 2.0'.\n"
    "- audio_jacks: Only include rear panel (back I/O) audio jacks. "
    "Ignore front panel audio headers and internal connectors entirely. "
    "Use the jack function as the type (e.g. 'Line Out', 'Line In', "
    "'Mic In', 'Center/Subwoofer', 'Rear Speaker', 'S/PDIF Out'). "
    "The main rear speaker output is 'Line Out', not 'Front Speaker' "
    "or 'Speaker Out'. "
    "If the spec only gives a total count without specifying individual jack "
    "types (e.g. '5 audio jacks'), use type 'Audio Jack' with that quantity.\n"
    "- wifi_bluetooth: 'built-in' means the board ships with a specific onboard "
    "WiFi/Bluetooth chip (the spec will name the chip, e.g. Intel AX211, "
    "MediaTek MT7922). 'optional module' means the board has a slot that "
    "accepts a wireless card but does not include one — look for an M.2 Key E "
    "socket, a CNVi slot, or any mention of WiFi/BT module support without a "
    "specific chip listed as included (e.g. 'M.2 Socket (Key E), supports "
    "type 2230 WiFi/BT module'). 'none' means no wireless support at all — "
    "no Key E slot, no WiFi mention anywhere in the spec."
)


# ── Public API ─────────────────────────────────────────────────

def extract(text: str) -> tuple[Motherboard, anthropic.types.Usage]:
    schema = json.dumps(Motherboard.model_json_schema(), indent=2)

    cached = cache.get_extraction(_SYSTEM_PROMPT, schema, text)
    if cached is not None:
        log.info("  (cached extraction, 0 tokens)")
        board = Motherboard(**cached["board"])
        usage = SimpleNamespace(**cached["usage"])
        return board, usage

    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        extra_body={"temperature": 0},
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Extract motherboard specs from this text into JSON "
                    f"matching this schema:\n\n{schema}\n\n"
                    f"--- PAGE TEXT ---\n{text}"
                ),
            }
        ],
    )

    data = _parse_json(response.content[0].text)
    board = Motherboard(**data)

    cache.set_extraction(_SYSTEM_PROMPT, schema, text, {
        "board": board.model_dump(),
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    })

    return board, response.usage


# ── Helpers ────────────────────────────────────────────────────

def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    fence = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end + 1])
        log.error("LLM response was not JSON:\n%s", raw[:500])
        raise
