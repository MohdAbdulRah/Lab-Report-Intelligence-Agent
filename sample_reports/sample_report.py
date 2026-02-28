"""
sample_report.py — Generate a sample PDF lab report for demo purposes.
Uses fpdf2 to create a realistic-looking lab report with intentional abnormalities.
Run this script directly to generate 'sample_lab_report.pdf'.
"""

from fpdf import FPDF
from datetime import datetime
import os


class LabReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(0, 80, 120)
        self.cell(0, 10, "HealthFirst Diagnostics", ln=True, align="C")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, "NABL Accredited | ISO 15189:2012 Certified", ln=True, align="C")
        self.cell(0, 5, "123 Medical Avenue, Healthcare City - 500001 | Ph: +91-9876543210", ln=True, align="C")
        self.line(10, self.get_y() + 3, 200, self.get_y() + 3)
        self.ln(8)

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, "This report is generated for demonstration purposes only.", ln=True, align="C")
        self.cell(0, 5, f"Page {self.page_no()}/{{nb}}", align="C")


def generate_sample_report(output_path=None):
    """Generate a sample lab report PDF with realistic test data."""
    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), "..", "sample_lab_report.pdf")

    pdf = LabReportPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    # ---- Patient Information ----
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(230, 240, 250)
    pdf.cell(0, 8, "  PATIENT INFORMATION", ln=True, fill=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(50, 50, 50)

    info = [
        ("Patient Name", "Rahul Sharma"),
        ("Age / Gender", "35 Years / Male"),
        ("Patient ID", "HF-2026-04521"),
        ("Referred By", "Dr. Priya Mehta"),
        ("Sample Collected", datetime.now().strftime("%d-%b-%Y, %I:%M %p")),
        ("Report Date", datetime.now().strftime("%d-%b-%Y")),
    ]

    for label, value in info:
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(45, 6, f"  {label}:", align="L")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, value, ln=True)

    pdf.ln(5)

    # ---- Helper: Add Test Section ----
    def add_section(title, tests):
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(0, 80, 120)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, f"  {title}", ln=True, fill=True)
        pdf.set_text_color(50, 50, 50)
        pdf.ln(1)

        # Table header
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(240, 245, 250)
        pdf.cell(65, 7, "  Test Name", border=1, fill=True)
        pdf.cell(30, 7, "Result", border=1, align="C", fill=True)
        pdf.cell(30, 7, "Unit", border=1, align="C", fill=True)
        pdf.cell(55, 7, "Reference Range", border=1, align="C", fill=True)
        pdf.ln()

        # Data rows
        pdf.set_font("Helvetica", "", 9)
        for test_name, value, unit, ref_range, is_abnormal in tests:
            if is_abnormal:
                pdf.set_text_color(200, 30, 30)
                pdf.set_font("Helvetica", "B", 9)
            else:
                pdf.set_text_color(50, 50, 50)
                pdf.set_font("Helvetica", "", 9)

            pdf.cell(65, 6, f"  {test_name}", border=1)
            pdf.cell(30, 6, str(value), border=1, align="C")
            pdf.cell(30, 6, unit, border=1, align="C")
            pdf.set_text_color(100, 100, 100)
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(55, 6, ref_range, border=1, align="C")
            pdf.ln()
            pdf.set_text_color(50, 50, 50)

        pdf.ln(5)

    # ---- Test Data (with intentional abnormalities) ----

    add_section("COMPLETE BLOOD COUNT (CBC)", [
        ("Hemoglobin", "10.2", "g/dL", "12.0 - 17.5", True),          # LOW
        ("Red Blood Cell Count", "4.5", "million/uL", "4.0 - 6.0", False),
        ("White Blood Cell Count", "12500", "cells/uL", "4000 - 11000", True),  # HIGH
        ("Platelet Count", "250000", "cells/uL", "150000 - 400000", False),
        ("Hematocrit", "38.0", "%", "36.0 - 54.0", False),
        ("MCV", "78.0", "fL", "80.0 - 100.0", True),                  # LOW
        ("MCH", "29.5", "pg", "27.0 - 33.0", False),
        ("MCHC", "33.8", "g/dL", "32.0 - 36.0", False),
        ("ESR", "25", "mm/hr", "0 - 20", True),                       # HIGH
    ])

    add_section("LIVER FUNCTION TEST (LFT)", [
        ("Total Bilirubin", "0.8", "mg/dL", "0.1 - 1.2", False),
        ("Direct Bilirubin", "0.2", "mg/dL", "0.0 - 0.3", False),
        ("ALT (SGPT)", "28", "U/L", "7 - 56", False),
        ("AST (SGOT)", "32", "U/L", "10 - 40", False),
        ("Alkaline Phosphatase", "95", "U/L", "44 - 147", False),
        ("Albumin", "4.2", "g/dL", "3.5 - 5.5", False),
        ("Total Protein", "7.1", "g/dL", "6.0 - 8.3", False),
    ])

    add_section("KIDNEY FUNCTION TEST (KFT)", [
        ("Creatinine", "0.9", "mg/dL", "0.6 - 1.2", False),
        ("Blood Urea Nitrogen", "15", "mg/dL", "7 - 20", False),
        ("Uric Acid", "5.5", "mg/dL", "3.0 - 7.0", False),
    ])

    add_section("LIPID PANEL", [
        ("Total Cholesterol", "245", "mg/dL", "Up to 200", True),      # HIGH
        ("HDL Cholesterol", "35", "mg/dL", "40 - 60", True),           # LOW
        ("LDL Cholesterol", "165", "mg/dL", "Up to 100", True),        # HIGH
        ("Triglycerides", "180", "mg/dL", "Up to 150", True),          # HIGH
        ("VLDL Cholesterol", "36", "mg/dL", "2 - 30", True),           # HIGH
    ])

    pdf.add_page()

    add_section("DIABETES / METABOLIC", [
        ("Fasting Blood Sugar", "132", "mg/dL", "70 - 100", True),     # HIGH
        ("HbA1c", "6.8", "%", "4.0 - 5.7", True),                     # HIGH
    ])

    add_section("THYROID PANEL", [
        ("TSH", "2.5", "uIU/mL", "0.4 - 4.0", False),
        ("Free T3", "3.1", "pg/mL", "2.0 - 4.4", False),
        ("Free T4", "1.2", "ng/dL", "0.8 - 1.8", False),
    ])

    add_section("ELECTROLYTES", [
        ("Sodium", "140", "mEq/L", "136 - 145", False),
        ("Potassium", "4.2", "mEq/L", "3.5 - 5.0", False),
        ("Calcium", "9.5", "mg/dL", "8.5 - 10.5", False),
    ])

    add_section("VITAMINS & IRON STUDIES", [
        ("Vitamin D", "18", "ng/mL", "30 - 100", True),               # LOW
        ("Vitamin B12", "350", "pg/mL", "200 - 900", False),
        ("Ferritin", "45", "ng/mL", "12 - 300", False),
        ("Serum Iron", "85", "ug/dL", "60 - 170", False),
    ])

    # ---- Pathologist Signature ----
    pdf.ln(15)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(0, 80, 120)
    pdf.cell(0, 6, "Dr. Arun Kapoor, MD (Pathology)", ln=True, align="R")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "Chief Pathologist | Reg. No: MCI-78542", ln=True, align="R")
    pdf.cell(0, 5, "HealthFirst Diagnostics", ln=True, align="R")

    # ---- End Disclaimer ----
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.multi_cell(0, 4,
        "Note: This report is for informational and demonstration purposes only. "
        "All values, patient data, and facility details are fictitious. "
        "Do not use this report for any clinical decision-making."
    )

    # Save
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    pdf.output(output_path)
    return os.path.abspath(output_path)


if __name__ == "__main__":
    path = generate_sample_report(os.path.join(os.path.dirname(__file__), "..", "sample_lab_report.pdf"))
    print(f"✅ Sample lab report generated: {path}")
