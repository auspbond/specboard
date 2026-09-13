import json
import logging
import subprocess
import sys
import re

log = logging.getLogger("pilot")
log.setLevel(logging.INFO)
if not log.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(_handler)


CASES = [
    {
        "name": "ASRock X670E PG Lightning",
        "command": ["python", "cli.py", "--rendered", "ASROCK X670E PG Lightning"],
        "expect": {
            "manufacturer": "ASRock",
            "socket": "AM5",
            "chipset": "X670E",
            "form_factor": "ATX",
            "memory_type": "DDR5",
        },
    },
]

REQUIRED_FIELDS = [
    "name", "manufacturer", "chipset", "socket", "form_factor",
    "memory_type", "memory_slots", "memory_max_gb",
]

LIST_FIELDS = [
    "pcie_slots", "m2_slots", "usb_ports",
]


def extract_json(output: str) -> dict | None:
    for match in re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", output, re.DOTALL):
        try:
            data = json.loads(match.group())
            if "socket" in data or "chipset" in data:
                return data
        except json.JSONDecodeError:
            continue
    return None


def check_case(case: dict) -> list[str]:
    failures = []

    log.info("Running: %s", " ".join(case["command"]))
    result = subprocess.run(
        case["command"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        failures.append(f"Exit code {result.returncode}")
        if result.stderr:
            failures.append(f"stderr: {result.stderr[:300]}")
        return failures

    data = extract_json(result.stdout)
    if data is None:
        failures.append("No JSON found in output")
        return failures

    for field in REQUIRED_FIELDS:
        if data.get(field) is None:
            failures.append(f"{field}: missing (got null)")

    for field in LIST_FIELDS:
        val = data.get(field)
        if not val:
            failures.append(f"{field}: empty list")

    for field, expected in case.get("expect", {}).items():
        actual = data.get(field)
        if actual is None:
            continue
        if expected.lower() not in str(actual).lower():
            failures.append(f"{field}: expected '{expected}' in '{actual}'")

    return failures


def main():
    passed = 0
    failed = 0

    for case in CASES:
        log.info("\n%s", "=" * 50)
        log.info("SMOKE TEST: %s", case["name"])
        log.info("=" * 50)

        try:
            failures = check_case(case)
        except subprocess.TimeoutExpired:
            failures = ["Timed out after 120s"]
        except Exception as e:
            failures = [f"Unexpected error: {e}"]

        if failures:
            failed += 1
            log.error("\n  FAIL: %s", case["name"])
            for f in failures:
                log.error("    - %s", f)
        else:
            passed += 1
            log.info("\n  PASS: %s", case["name"])

    log.info("\n%s", "=" * 50)
    log.info("Results: %d passed, %d failed", passed, failed)

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
