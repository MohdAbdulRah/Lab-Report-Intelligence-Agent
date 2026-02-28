"""
agent.py — Lab Report Intelligence Agent
Compares extracted lab data against benchmark database, flags abnormalities,
and generates patient-friendly and clinical summaries.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BENCHMARK_DB_PATH = Path(__file__).parent / "benchmark_db.json"


def load_benchmark_db():
    """Load the medical benchmark database from JSON."""
    with open(BENCHMARK_DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["tests"]


def _normalize_name(name):
    """Normalize a test name for matching: remove dots, dashes, extra spaces, 'total' prefix."""
    import re
    n = name.lower().strip()
    n = re.sub(r'[.\-_/,\(\)]', ' ', n)     # dots, dashes, parens → spaces
    n = re.sub(r'\s+', ' ', n).strip()       # collapse spaces
    n = re.sub(r'^total\s+', '', n)           # remove "total" prefix
    return n


def find_benchmark(test_name, benchmarks):
    """Find a matching benchmark (exact, alias, normalized, fuzzy)."""
    test_lower = test_name.lower().strip()
    test_norm = _normalize_name(test_name)

    # Pass 1: Exact match on name or alias
    for bench in benchmarks:
        if bench["test_name"].lower() == test_lower:
            return bench
        if test_lower in [a.lower() for a in bench.get("aliases", [])]:
            return bench

    # Pass 2: Normalized match (removes dots, dashes, "total" prefix)
    for bench in benchmarks:
        if _normalize_name(bench["test_name"]) == test_norm:
            return bench
        for alias in bench.get("aliases", []):
            if _normalize_name(alias) == test_norm:
                return bench

    # Pass 3: Fuzzy substring match
    for bench in benchmarks:
        bn = _normalize_name(bench["test_name"])
        if bn in test_norm or test_norm in bn:
            return bench
        for alias in bench.get("aliases", []):
            an = _normalize_name(alias)
            if an in test_norm or test_norm in an:
                return bench

    return None


def _parse_ref_range(ref_text):
    """Parse reference range text into (low, high) numeric values."""
    import re
    if not ref_text:
        return None, None
    ref_text = str(ref_text).strip()

    # "low - high" pattern
    m = re.search(r'(\d+\.?\d*)\s*[-\u2013\u2014]+\s*(\d+\.?\d*)', ref_text)
    if m:
        return float(m.group(1)), float(m.group(2))

    # "< upper" or "Up to upper"
    m = re.search(r'(?:<|[Uu]p\s*to)\s*(\d+\.?\d*)', ref_text)
    if m:
        return None, float(m.group(1))

    # "> lower"
    m = re.search(r'>\s*(\d+\.?\d*)', ref_text)
    if m:
        return float(m.group(1)), None

    return None, None


def compare_with_benchmarks(extracted_tests, benchmarks=None):
    """Compare each test against benchmarks. Returns enriched list."""
    if benchmarks is None:
        benchmarks = load_benchmark_db()

    results = []
    for test in extracted_tests:
        test_name = test.get("test_name", "")
        value = test.get("value")
        unit = test.get("unit", "")
        ref_text = test.get("ref_range_text", "")

        bench = find_benchmark(test_name, benchmarks)

        enriched = {
            "test_name": test_name,
            "value": value,
            "unit": unit,
            "ref_range_text": ref_text,
            "status": "NORMAL",
            "benchmark": None,
            "benchmark_low": None,
            "benchmark_high": None,
            "category": "Uncategorized",
            "description": ""
        }

        low = None
        high = None

        if bench:
            low = bench.get("low")
            high = bench.get("high")
            enriched["benchmark"] = bench["test_name"]
            enriched["benchmark_low"] = low
            enriched["benchmark_high"] = high
            enriched["category"] = bench.get("category", "Uncategorized")
            enriched["description"] = bench.get("description", "")
        elif ref_text and value is not None:
            # No benchmark match — parse the extracted reference range text
            low, high = _parse_ref_range(ref_text)
            enriched["benchmark_low"] = low
            enriched["benchmark_high"] = high

        if value is not None and low is not None and high is not None:
            if value < low:
                enriched["status"] = "LOW"
            elif value > high:
                enriched["status"] = "HIGH"
            else:
                enriched["status"] = "NORMAL"
        elif value is not None and high is not None and low is None:
            # e.g. "< 200"
            enriched["status"] = "HIGH" if value > high else "NORMAL"
        elif value is not None and low is not None and high is None:
            # e.g. "> 40"
            enriched["status"] = "LOW" if value < low else "NORMAL"
        else:
            enriched["status"] = "NORMAL"

        results.append(enriched)
    return results


def get_abnormal_tests(compared_results):
    return [r for r in compared_results if r["status"] in ("LOW", "HIGH")]


def get_summary_stats(compared_results):
    stats = {"total": len(compared_results), "normal": 0, "low": 0, "high": 0, "unknown": 0}
    for r in compared_results:
        k = r["status"].lower()
        if k in stats:
            stats[k] += 1
        else:
            stats["unknown"] += 1
    return stats


def generate_patient_summary_fallback(compared_results):
    """Template-based patient summary (no API key needed)."""
    stats = get_summary_stats(compared_results)
    abnormal = get_abnormal_tests(compared_results)

    lines = ["# Your Lab Report Summary\n",
             f"We analyzed **{stats['total']} tests** from your report.\n"]

    if stats["low"] == 0 and stats["high"] == 0:
        lines.append("**Great news!** All your test results fall within the normal reference ranges.\n")
    else:
        if stats["normal"] > 0:
            lines.append(f"**{stats['normal']} test(s)** are within normal range - that's good news!\n")
        if abnormal:
            lines.append(f"**{len(abnormal)} test(s)** are outside the normal range:\n")
            for t in abnormal:
                direction = "lower" if t["status"] == "LOW" else "higher"
                label = "Below Range" if t["status"] == "LOW" else "Above Range"
                lines.append(f"### {t['test_name']}: {t['value']} {t['unit']} ({label})")
                if t["benchmark_low"] is not None and t["benchmark_high"] is not None:
                    lines.append(f"- **Normal range:** {t['benchmark_low']} - {t['benchmark_high']} {t['unit']}")
                    lines.append(f"- Your value is {direction} than the typical range.")
                if t["description"]:
                    lines.append(f"- **What this measures:** {t['description']}")
                lines.append("")

    if stats["unknown"] > 0:
        lines.append(f"\n**{stats['unknown']} test(s)** could not be matched to our reference database.\n")

    lines.append("\n---")
    lines.append("**Disclaimer:** This is for educational purposes only. Not a medical diagnosis. "
                 "Please consult your doctor for interpretation.")
    return "\n".join(lines)


def generate_clinical_summary_fallback(compared_results):
    """Template-based clinical summary (no API key needed)."""
    stats = get_summary_stats(compared_results)
    abnormal = get_abnormal_tests(compared_results)

    lines = ["# Clinical Lab Report Summary\n",
             f"**Parameters:** {stats['total']} | **Normal:** {stats['normal']} | "
             f"**Low:** {stats['low']} | **High:** {stats['high']} | **Unmatched:** {stats['unknown']}\n"]

    categories = {}
    for r in compared_results:
        cat = r.get("category", "Uncategorized")
        categories.setdefault(cat, []).append(r)

    for cat, tests in categories.items():
        lines.append(f"\n## {cat}\n")
        lines.append("| Parameter | Result | Unit | Reference | Status |")
        lines.append("|-----------|--------|------|-----------|--------|")
        for t in tests:
            ref = f"{t['benchmark_low']} - {t['benchmark_high']}" if t['benchmark_low'] is not None else t.get('ref_range_text', 'N/A')
            lines.append(f"| {t['test_name']} | {t['value']} | {t['unit']} | {ref} | {t['status']} |")

    if abnormal:
        lines.append("\n## Abnormal Findings\n")
        for t in abnormal:
            lines.append(f"- **{t['test_name']}**: {t['status']}")

    lines.append("\n---")
    lines.append("*AI-generated summary for reference only. Clinical correlation advised.*")
    return "\n".join(lines)
