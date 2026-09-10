import json

import anthropic

from schemas import Motherboard


def extract(text: str) -> tuple[Motherboard, anthropic.types.Usage]:
    client = anthropic.Anthropic()

    schema = json.dumps(Motherboard.model_json_schema(), indent=2)

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        system=(
            "You extract structured motherboard specifications from raw text. "
            "Return ONLY valid JSON matching the provided schema. "
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

    data = json.loads(response.content[0].text)
    board = Motherboard(**data)

    return board, response.usage
