import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fetcher import fetch_text, fetch_rendered
from extractor import extract

log = logging.getLogger("pilot")
if not log.handlers:
    log.setLevel(logging.INFO)
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(_handler)


GROUND_TRUTH_DIR = Path(__file__).parent / "ground_truth"


def load_cases() -> list[dict]:
    cases = []
    for f in sorted(GROUND_TRUTH_DIR.glob("*.json")):
        with open(f) as fh:
            case = json.load(fh)
            case["file"] = f.name
            cases.append(case)
    return cases


def compare(expected: dict, actual: dict) -> list[tuple[str, str, str]]:
    mismatches = []
    for key, exp_val in expected.items():
        act_val = actual.get(key)
        if key in ("usb_ports", "audio_jacks"):
            exp_set = {(p["location"], p["type"], p["quantity"]) for p in exp_val}
            act_set = {(p["location"], p["type"], p["quantity"]) for p in (act_val or [])}
            if exp_set != act_set:
                mismatches.append((key, str(exp_val), str(act_val)))
        elif key in ("pcie_slots", "m2_slots", "video_ports"):
            exp_set = {(p["type"], p["quantity"]) for p in exp_val}
            act_set = {(p["type"], p["quantity"]) for p in (act_val or [])}
            if exp_set != act_set:
                mismatches.append((key, str(exp_val), str(act_val)))
        elif exp_val != act_val:
            mismatches.append((key, str(exp_val), str(act_val)))
    return mismatches


def run_eval():
    cases = load_cases()
    if not cases:
        log.info("No ground truth files found.")
        return

    total_fields = 0
    total_correct = 0

    for case in cases:
        label = case["file"].replace(".json", "").replace("_", " ").title()
        expected = case["expected"]

        empty_fields = [k for k, v in expected.items()
                        if v == "" or v == []]
        if empty_fields:
            log.info("\n%s: SKIPPED (unfilled fields: %s)", label, ", ".join(empty_fields))
            continue

        log.info("\n%s:", label)

        url = case.get("url")
        rendered = case.get("rendered", False)

        if url:
            log.info("  Fetching: %s", url)
            text = fetch_rendered(url) if rendered else fetch_text(url)
        else:
            from fetcher import search
            urls = search(case["query"])
            from cli import fetch_with_fallback
            url, text = fetch_with_fallback(urls, rendered)

        log.info("  Extracting...")
        board, usage = extract(text)
        actual = board.model_dump()

        num_fields = len(expected)
        mismatches = compare(expected, actual)
        correct = num_fields - len(mismatches)

        total_fields += num_fields
        total_correct += correct

        log.info("  Score: %d/%d fields correct", correct, num_fields)
        for field, exp, act in mismatches:
            log.info("    %s: expected %s, got %s", field, exp, act)
        log.info("  Tokens — input: %d, output: %d", usage.input_tokens, usage.output_tokens)

    log.info("\n%s", "=" * 40)
    log.info("Overall: %d/%d (%.1f%%)", total_correct, total_fields, 100 * total_correct / total_fields)


if __name__ == "__main__":
    run_eval()
