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
            "If a field cannot be determined from the text, use null."
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
