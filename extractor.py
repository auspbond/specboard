import json
import logging
import re
from types import SimpleNamespace

import anthropic

log = logging.getLogger("pilot")

import cache
from schemas import Motherboard


# ── Constants ──────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You extract structured motherboard specifications from raw text. "
    "Return ONLY valid JSON matching the provided schema. "
    "No markdown, no explanation, just the JSON object. "
    "If a field cannot be determined from the text, use null.\n\n"
    "Field guidance:\n"
    "- video_ports: List each video output port type and count (e.g. 'HDMI 2.1', "
    "'DisplayPort 1.4', 'VGA', 'DVI-D'). Include the version if specified.\n"
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
    "Always include the form factor (2280, 2242, etc.). If a slot supports "
    "multiple form factors including 2280, list only 2280. If a slot does not "
    "support 2280, list its actual form factor (e.g. 'M.2 2242 Gen4x4').\n"
    "- usb_ports: Separate rear panel (back I/O) ports from front panel "
    "(internal header) ports. Rear ports are on the back I/O panel. Front "
    "ports connect via internal headers on the motherboard (often labeled "
    "'Front Panel USB', 'onboard header', or 'internal connector'). Use "
    "location 'rear' or 'front' for each entry.\n"
    "- audio_jacks: Separate rear panel jacks from front panel (internal header) "
    "jacks. Use the jack function as the type (e.g. 'Line Out', 'Line In', "
    "'Mic In', 'Center/Subwoofer', 'Rear Speaker', 'S/PDIF Out', 'Headphone', "
    "'Mic'). Front panel audio typically comes from an 'HD Audio Header' or "
    "'Front Panel Audio Connector'. Use location 'rear' or 'front'.\n"
    "- wifi_bluetooth: 'built-in' means the board ships with an onboard WiFi/Bluetooth "
    "chip (e.g. Intel AX211, MediaTek MT7922). 'optional module' means the board "
    "has an M.2 Key E or CNVi slot that accepts a wireless card but does not "
    "include one. 'none' means no wireless support at all. Look for keywords "
    "like 'onboard', 'integrated', 'included' vs 'supports module', 'Key E slot', "
    "'sold separately'."
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
