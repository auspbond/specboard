import json
import re

import anthropic

from schemas import Motherboard


def parse_json(raw: str) -> dict:
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
        print(f"LLM response was not JSON:\n{raw[:500]}")
        raise


def extract(text: str) -> tuple[Motherboard, anthropic.types.Usage]:
    client = anthropic.Anthropic()

    schema = json.dumps(Motherboard.model_json_schema(), indent=2)

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        system=(
            "You extract structured motherboard specifications from raw text. "
            "Return ONLY valid JSON matching the provided schema. "
            "No markdown, no explanation, just the JSON object. "
            "If a field cannot be determined from the text, use null.\n\n"
            "Field guidance:\n"
            "- pcie_slots: List each distinct PCIe slot type with its count. "
            "Use the exact slot designation from the spec page (e.g. 'PCIe 5.0 x16', "
            "'PCIe 4.0 x4', 'PCIe 3.0 x1'). Include the PCIe generation and lane width.\n"
            "- usb_ports: Separate rear panel (back I/O) ports from front panel "
            "(internal header) ports. Rear ports are on the back I/O panel. Front "
            "ports connect via internal headers on the motherboard (often labeled "
            "'Front Panel USB', 'onboard header', or 'internal connector'). Use "
            "location 'rear' or 'front' for each entry.\n"
            "- wifi_bluetooth: 'built-in' means the board ships with an onboard WiFi/Bluetooth "
            "chip (e.g. Intel AX211, MediaTek MT7922). 'optional module' means the board "
            "has an M.2 Key E or CNVi slot that accepts a wireless card but does not "
            "include one. 'none' means no wireless support at all. Look for keywords "
            "like 'onboard', 'integrated', 'included' vs 'supports module', 'Key E slot', "
            "'sold separately'."
        ),
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

    data = parse_json(response.content[0].text)
    board = Motherboard(**data)

    return board, response.usage
