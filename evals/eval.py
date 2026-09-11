import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fetcher import fetch_text, fetch_rendered
from extractor import extract


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
        if key == "usb_ports":
            exp_set = {(p["location"], p["type"], p["count"]) for p in exp_val}
            act_set = {(p["location"], p["type"], p["count"]) for p in (act_val or [])}
            if exp_set != act_set:
                mismatches.append((key, str(exp_val), str(act_val)))
        elif key in ("pcie_slots", "m2_slots"):
            exp_set = {(p["type"], p["count"]) for p in exp_val}
            act_set = {(p["type"], p["count"]) for p in (act_val or [])}
            if exp_set != act_set:
                mismatches.append((key, str(exp_val), str(act_val)))
        elif exp_val != act_val:
            mismatches.append((key, str(exp_val), str(act_val)))
    return mismatches


def run_eval():
    cases = load_cases()
    if not cases:
        print("No ground truth files found.")
        return

    total_fields = 0
    total_correct = 0

    for case in cases:
        label = case["file"].replace(".json", "").replace("_", " ").title()
        expected = case["expected"]

        empty_fields = [k for k, v in expected.items()
                        if v == "" or v == []]
        if empty_fields:
            print(f"\n{label}: SKIPPED (unfilled fields: {', '.join(empty_fields)})")
            continue

        print(f"\n{label}:")

        url = case.get("url")
        rendered = case.get("rendered", False)

        if url:
            print(f"  Fetching: {url}")
            text = fetch_rendered(url) if rendered else fetch_text(url)
        else:
            from fetcher import search
            urls = search(case["query"])
            from cli import _fetch_with_fallback
            url, text = _fetch_with_fallback(urls, rendered)

        print("  Extracting...")
        board, usage = extract(text)
        actual = board.model_dump()

        num_fields = len(expected)
        mismatches = compare(expected, actual)
        correct = num_fields - len(mismatches)

        total_fields += num_fields
        total_correct += correct

        print(f"  Score: {correct}/{num_fields} fields correct")
        for field, exp, act in mismatches:
            print(f"    {field}: expected {exp}, got {act}")
        print(f"  Tokens — input: {usage.input_tokens}, output: {usage.output_tokens}")

    print(f"\n{'=' * 40}")
    print(f"Overall: {total_correct}/{total_fields} ({100 * total_correct / total_fields:.1f}%)")


if __name__ == "__main__":
    run_eval()
