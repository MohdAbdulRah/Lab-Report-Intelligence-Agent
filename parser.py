"""
parser.py — Universal Lab Report Extractor (Table + Text + OCR + Gemini AI)

Dual-path extraction:
  1. STRUCTURED: pdfplumber for tables/text + regex
  2. UNSTRUCTURED: Gemini Flash directly reads the PDF file
"""

import re
import json
import os
import traceback
import pdfplumber
from dotenv import load_dotenv

load_dotenv()


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

KNOWN_UNITS = [
    "million/uL", "million/cumm",
    "mill/cumm", "mil/cmm", "mil/cumm",
    "cells/uL", "cells/cumm",
    "thou/uL", "thou/cumm",
    "x10^3/uL", "x10^6/uL",
    "mIU/mL", "uIU/mL", "mIU/L",
    "mL/min/1.73m2", "mL/min",
    "mEq/L", "meq/l",
    "mmol/L", "umol/L", "nmol/L", "pmol/L",
    "mg/dL", "mg/dl", "mg/L",
    "g/dL", "g/dl", "g/L",
    "gm/dL", "gm/dl", "gm%",
    "ng/mL", "ng/ml", "ng/dL", "ng/dl",
    "pg/mL", "pg/ml",
    "ug/dL", "ug/dl",
    "U/L", "u/l", "IU/L", "IU/mL",
    "mm/hr", "mm/1st hr",
    "fL", "fl", "pg",
    "sec", "%",
]

UNIT_PATTERN = "|".join(re.escape(u) for u in KNOWN_UNITS)

SKIP_PATTERNS = [
    re.compile(r'^\s*(page|report|date|time|patient|doctor|dr\.|lab|hospital|clinic|specimen|sample|collected|received|printed|barcode|accession)', re.I),
    re.compile(r'^\s*(test\s*name|investigation|parameter|analyte)\s+(result|value|observed)', re.I),
    re.compile(r'^\s*(name|age|sex|gender|id|uhid|mrn)\s*[:/]', re.I),
    re.compile(r'^\s*[-=_*]{5,}\s*$'),
    re.compile(r'^\s*$'),
    re.compile(r'^\s*(end\s*of\s*report|signature|pathologist|technician|verified|approved)', re.I),
    re.compile(r'^\s*(note|disclaimer|this\s*report|please\s*consult|address|phone|nabl|iso)', re.I),
]

INVALID_NAMES = {
    'test', 'name', 'result', 'value', 'unit', 'reference', 'range',
    'normal', 'parameter', 'investigation', 'method', 'remarks', 'status',
}


# ═══════════════════════════════════════════════════════════════════════════
# PDFPLUMBER-BASED EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════

def _should_skip(line):
    if len(line.strip()) < 3:
        return True
    for pat in SKIP_PATTERNS:
        if pat.search(line):
            return True
    return False


LINE_PATTERNS = [
    re.compile(
        r'^(?P<name>[A-Za-z][A-Za-z0-9\s\(\)\-\.\,/\']+?)'
        r'\s{2,}(?P<value>\d+\.?\d*)\s+'
        r'(?P<unit>' + UNIT_PATTERN + r')\s+'
        r'(?P<ref>\d+\.?\d*\s*[-\u2013\u2014]+\s*\d+\.?\d*'
        r'(?:\s*(?:' + UNIT_PATTERN + r'))?)', re.I),
    re.compile(
        r'^(?P<name>[A-Za-z][A-Za-z0-9\s\(\)\-\.\,/\']+?)'
        r'\s{2,}(?P<value>\d+\.?\d*)\s+'
        r'(?P<unit>' + UNIT_PATTERN + r')\s+'
        r'(?P<ref>(?:[<>]|[Uu]p\s*to)\s*\d+\.?\d*)', re.I),
    re.compile(
        r'^(?P<name>[A-Za-z][A-Za-z0-9\s\(\)\-\.\,/\']+?)'
        r'\s{2,}(?P<value>\d+\.?\d*)\s+'
        r'(?P<unit>' + UNIT_PATTERN + r')', re.I),
    re.compile(
        r'^(?P<name>[A-Za-z][A-Za-z0-9\s\(\)\-\.\,/\']+?)'
        r'\s*[:=]\s*(?P<value>\d+\.?\d*)\s*'
        r'(?P<unit>' + UNIT_PATTERN + r')?\s*[\(\[]*\s*(?:[Rr]ef[:\.]?\s*)?'
        r'(?P<ref>\d+\.?\d*\s*[-\u2013]+\s*\d+\.?\d*)?', re.I),
    re.compile(
        r'^(?P<name>[A-Za-z][A-Za-z0-9\s\(\)\-\.\,/\']{2,}?)'
        r'\s+(?P<value>\d+\.?\d*)\s+'
        r'(?P<unit>' + UNIT_PATTERN + r')\s+'
        r'(?P<ref>\d+\.?\d*\s*[-\u2013]+\s*\d+\.?\d*)', re.I),
]


def pdfplumber_parse(pdf_file):
    """Try pdfplumber table + text extraction. Returns list of dicts."""
    results = []
    seen = set()

    # --- Table extraction ---
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if not tables:
                    continue
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    header = None
                    data_start = 0
                    for i, row in enumerate(table):
                        if row and any(cell and any(k in str(cell).lower()
                                     for k in ['test', 'parameter', 'investigation', 'name', 'analyte'])
                                     for cell in row if cell):
                            header = row
                            data_start = i + 1
                            break
                    if header is None:
                        header = table[0]
                        data_start = 1

                    col = {'name': 0, 'value': 1, 'unit': 2, 'ref': 3}
                    for idx, cell in enumerate(header):
                        if not cell:
                            continue
                        cl = str(cell).lower()
                        if any(k in cl for k in ['test', 'parameter', 'investigation', 'name', 'analyte']):
                            col['name'] = idx
                        elif any(k in cl for k in ['result', 'value', 'observed']):
                            col['value'] = idx
                        elif 'unit' in cl:
                            col['unit'] = idx
                        elif any(k in cl for k in ['reference', 'range', 'normal', 'ref']):
                            col['ref'] = idx

                    for row in table[data_start:]:
                        if not row:
                            continue
                        try:
                            def safe(lst, i, d=''):
                                return str(lst[i]).strip() if i < len(lst) and lst[i] else d
                            name = safe(row, col['name'])
                            val_str = safe(row, col['value'])
                            unit = safe(row, col['unit'])
                            ref = safe(row, col['ref'])
                            if len(name) < 2:
                                continue
                            val_m = re.search(r'(\d+\.?\d*)', val_str)
                            if not val_m:
                                continue
                            key = name.lower().strip()
                            if key not in seen and key not in INVALID_NAMES:
                                seen.add(key)
                                results.append({
                                    'test_name': name,
                                    'value': float(val_m.group(1)),
                                    'unit': unit, 'ref_range_text': ref,
                                })
                        except (IndexError, TypeError, ValueError):
                            continue
    except Exception:
        pass

    # --- Text extraction ---
    try:
        if hasattr(pdf_file, 'seek'):
            pdf_file.seek(0)
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"

        if text:
            text = re.sub(r'[|]', ' ', text)
            text = re.sub(r'\t', '  ', text)
            text = re.sub(r'[ ]{3,}', '  ', text)
            lines = text.split('\n')
            # Merge multi-line
            merged = []
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if (i + 1 < len(lines) and line and not re.search(r'\d', line)
                        and len(line) > 2 and not _should_skip(line)):
                    nxt = lines[i + 1].strip()
                    if re.search(r'\d+\.?\d*', nxt):
                        merged.append(line + '  ' + nxt)
                        i += 2
                        continue
                merged.append(line)
                i += 1

            for line in merged:
                if _should_skip(line):
                    continue
                for pat in LINE_PATTERNS:
                    m = pat.search(line)
                    if not m:
                        continue
                    g = m.groupdict()
                    name = re.sub(r'\s+', ' ', g.get('name', '')).strip().rstrip(':= ')
                    val_s = g.get('value', '')
                    unit = (g.get('unit') or '').strip()
                    ref = (g.get('ref') or '').strip()
                    if len(name) < 2 or name.lower() in INVALID_NAMES:
                        continue
                    try:
                        val = float(val_s)
                    except (ValueError, TypeError):
                        continue
                    key = name.lower().strip()
                    if key not in seen:
                        seen.add(key)
                        results.append({
                            'test_name': name, 'value': val,
                            'unit': unit, 'ref_range_text': ref,
                        })
                    break
    except Exception:
        pass

    return results


# ═══════════════════════════════════════════════════════════════════════════
# GEMINI-BASED EXTRACTION (for unstructured/scanned PDFs)
# ═══════════════════════════════════════════════════════════════════════════

GEMINI_EXTRACTION_PROMPT = """You are a medical lab report data extraction expert. 
Analyze this lab report PDF and extract ALL lab test entries you can find.

For EACH test found, extract:
1. test_name: The name of the lab test (e.g., "Hemoglobin", "Fasting Blood Sugar")
2. value: The numeric result value (just the number, as float or int)
3. unit: The unit of measurement (e.g., "g/dL", "mg/dL", "%")
4. ref_range_text: The reference/normal range as shown (e.g., "13.0 - 17.0" or "< 200")

Return ONLY valid JSON array. No explanations, no markdown code fences, just the JSON array.
Example:
[
  {"test_name": "Hemoglobin", "value": 9.1, "unit": "g/dL", "ref_range_text": "13.0 - 17.0"},
  {"test_name": "Fasting Blood Sugar", "value": 132, "unit": "mg/dL", "ref_range_text": "70 - 100"}
]

RULES:
- Extract EVERY test you can find
- Convert result to a number (float or int)
- If unit is not visible, use "unknown"
- If reference range is not visible, use ""
- Do NOT invent tests or values not present in the document
- Return ONLY the JSON array
"""

GEMINI_EVALUATION_PROMPT = """You are a medical lab report intelligence agent. Analyze the following lab test results and generate TWO outputs.

Here are the lab results:
{results_json}

Here is the benchmark comparison data:
{benchmark_json}

Generate TWO sections clearly separated:

=== PATIENT SUMMARY ===
Write a clear, compassionate, simple-language explanation for a patient with NO medical background.
RULES:
- NEVER diagnose diseases or prescribe treatment
- Use calm, reassuring language
- Use phrases like "may be associated with", "could indicate", "can sometimes be seen in"
- Explain what each abnormal test measures in simple words
- Prioritize abnormal values first
- End with a disclaimer that this is educational only

=== CLINICAL SUMMARY ===
Write a structured clinical summary for healthcare professionals.
RULES:
- Use proper medical terminology
- Organize by test category
- Present as a table: Parameter | Result | Unit | Reference | Status
- Highlight abnormal values
- Use "findings consistent with", "suggestive of", "may warrant further evaluation"
- End with disclaimer
"""


def gemini_extract_from_pdf(pdf_file_bytes, api_key):
    """
    Send PDF bytes directly to Gemini Flash for AI-based extraction.
    Uses inline bytes — no file upload needed.
    
    Args:
        pdf_file_bytes: Raw PDF bytes
        api_key: Google Gemini API key
        
    Returns: (results_list, error_message)
        - results_list: list of dicts or empty list
        - error_message: None on success, string on failure
    """
    if not api_key:
        return [], "No Gemini API key provided."

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        # Send PDF bytes inline (no file upload needed!)
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_bytes(data=pdf_file_bytes, mime_type="application/pdf"),
                        types.Part.from_text(text=GEMINI_EXTRACTION_PROMPT),
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=8192,
            )
        )

        response_text = response.text.strip()

        # Remove markdown code fences if present
        if response_text.startswith("```"):
            response_text = re.sub(r'^```(?:json)?\s*\n?', '', response_text)
            response_text = re.sub(r'\n?```\s*$', '', response_text)

        data = json.loads(response_text)

        results = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get('test_name', '')).strip()
            val = entry.get('value')
            unit = str(entry.get('unit', '')).strip()
            ref = str(entry.get('ref_range_text', '')).strip()

            if not name or val is None:
                continue
            try:
                val = float(val)
            except (ValueError, TypeError):
                continue

            results.append({
                'test_name': name,
                'value': val,
                'unit': unit if unit else 'unknown',
                'ref_range_text': ref,
            })

        if not results:
            return [], "Gemini could not identify any lab test entries in this PDF."

        return results, None

    except json.JSONDecodeError as e:
        return [], f"Gemini returned invalid JSON: {str(e)}"
    except Exception as e:
        error_detail = traceback.format_exc()
        return [], f"Gemini extraction error: {str(e)}\n{error_detail}"


def gemini_evaluate_results(compared_results, api_key):
    """
    Send benchmarked results to Gemini for full AI evaluation.
    Returns (patient_summary, clinical_summary) or (None, None).
    """
    if not api_key:
        return None, None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        results_data = []
        benchmark_data = []
        for r in compared_results:
            results_data.append({
                'test_name': r['test_name'],
                'value': r['value'],
                'unit': r['unit'],
                'status': r['status'],
            })
            benchmark_data.append({
                'test_name': r['test_name'],
                'value': r['value'],
                'unit': r['unit'],
                'status': r['status'],
                'benchmark_low': r.get('benchmark_low'),
                'benchmark_high': r.get('benchmark_high'),
                'category': r.get('category', 'Uncategorized'),
                'description': r.get('description', ''),
            })

        prompt = GEMINI_EVALUATION_PROMPT.format(
            results_json=json.dumps(results_data, indent=2),
            benchmark_json=json.dumps(benchmark_data, indent=2),
        )

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=4096,
            )
        )

        full_text = response.text.strip()

        if "=== PATIENT SUMMARY ===" in full_text and "=== CLINICAL SUMMARY ===" in full_text:
            parts = full_text.split("=== CLINICAL SUMMARY ===")
            patient = parts[0].replace("=== PATIENT SUMMARY ===", "").strip()
            clinical = parts[1].strip() if len(parts) > 1 else ""
        else:
            patient = full_text
            clinical = full_text

        return patient, clinical

    except Exception as e:
        return None, None


# ═══════════════════════════════════════════════════════════════════════════
# GEMINI — Compare Current Report with Past Reports
# ═══════════════════════════════════════════════════════════════════════════
def generate_report_comparison(current_text, past_reports, api_key):
    """
    Send current + past reports to Gemini for trend comparison.

    Args:
        current_text: Text of the current report
        past_reports: List of dicts with keys: document, report_name, upload_date
        api_key: Google Gemini API key

    Returns: comparison_text (str) or None
    """
    if not api_key or not past_reports:
        return None

    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        # Build the prompt
        past_section = ""
        for i, rpt in enumerate(past_reports, 1):
            past_section += f"\n--- Report {i}: {rpt['report_name']} (Date: {rpt['upload_date']}) ---\n"
            past_section += rpt["document"][:3000] + "\n"

        prompt = f"""You are a medical lab report comparison expert.

PREVIOUS REPORTS:
{past_section}

CURRENT REPORT:
{current_text[:3000]}

INSTRUCTIONS:
Compare the current report with the previous reports. Identify:

1. **Improvements** — values that have gotten better
2. **Worsening Values** — values that have deteriorated
3. **Trends Over Time** — patterns you notice across reports
4. **Important Medical Changes** — any clinically significant changes

Then provide clear, actionable **Suggestions** based on the comparison.

Format your response in clean markdown with headers and bullet points.
Keep it patient-friendly and easy to understand.
"""

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt
        )

        return response.text.strip() if response.text else None

    except Exception as e:
        return None
