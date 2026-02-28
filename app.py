"""
app.py - Streamlit UI for the Lab Report Intelligence Agent
Session persistence via query params + Dual-path extraction pipeline.
"""

import streamlit as st
import os
from auth import login, signup, validate_session, logout as db_logout
from parser import pdfplumber_parse, gemini_extract_from_pdf, gemini_evaluate_results, generate_report_comparison
from agent import (
    compare_with_benchmarks,
    load_benchmark_db,
    get_summary_stats,
    get_abnormal_tests,
    generate_patient_summary_fallback,
    generate_clinical_summary_fallback,
)
from vector_db.store_report import store_report
from vector_db.search_reports import get_user_reports

# ---------------------------------------------------------------------------
# Page Config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Lab Report Intelligence Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# Session State Defaults
# ---------------------------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None
if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"

# ---------------------------------------------------------------------------
# Restore session from query params (survives page refresh)
# ---------------------------------------------------------------------------
if not st.session_state.logged_in:
    params = st.query_params
    saved_token = params.get("session", None)
    if saved_token:
        user = validate_session(saved_token)
        if user:
            st.session_state.logged_in = True
            st.session_state.user = user

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }

    .main-header {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        padding: 2rem 2.5rem; border-radius: 16px; margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.15);
    }
    .main-header h1 { color: #ffffff; font-size: 2.2rem; font-weight: 700; margin: 0; }
    .main-header p { color: #94d2bd; font-size: 1.05rem; margin-top: 0.5rem; font-weight: 300; }

    .auth-container {
        max-width: 460px; margin: 3rem auto;
        background: linear-gradient(135deg, #0f2027, #203a43);
        padding: 2.5rem; border-radius: 20px;
        box-shadow: 0 12px 40px rgba(0,0,0,0.3);
        border: 1px solid rgba(255,255,255,0.08);
    }
    .auth-container h2 {
        color: #ffffff; text-align: center; font-weight: 700;
        font-size: 1.6rem; margin-bottom: 0.3rem;
    }
    .auth-container .subtitle {
        color: #94d2bd; text-align: center; font-size: 0.95rem;
        margin-bottom: 1.5rem; font-weight: 300;
    }

    .stat-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border-radius: 14px; padding: 1.5rem; text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 1px solid rgba(255,255,255,0.05);
    }
    .stat-card .number { font-size: 2.5rem; font-weight: 700; margin: 0.3rem 0; }
    .stat-card .label { font-size: 0.85rem; font-weight: 500; text-transform: uppercase; letter-spacing: 1px; }
    .stat-normal .number { color: #52b788; } .stat-normal .label { color: #95d5b2; }
    .stat-high .number { color: #e63946; } .stat-high .label { color: #f4a0a8; }
    .stat-low .number { color: #4895ef; } .stat-low .label { color: #90c4f9; }
    .stat-total .number { color: #f4a261; } .stat-total .label { color: #f4c89a; }

    .result-row {
        padding: 0.8rem 1rem; border-radius: 10px; margin-bottom: 0.5rem;
        display: flex; align-items: center; justify-content: space-between;
    }
    .result-normal { background: rgba(82, 183, 136, 0.1); border-left: 4px solid #52b788; }
    .result-high { background: rgba(230, 57, 70, 0.1); border-left: 4px solid #e63946; }
    .result-low { background: rgba(72, 149, 239, 0.1); border-left: 4px solid #4895ef; }
    .result-unknown { background: rgba(200, 200, 200, 0.1); border-left: 4px solid #adb5bd; }

    .badge { padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
    .badge-normal { background: #52b788; color: white; }
    .badge-high { background: #e63946; color: white; }
    .badge-low { background: #4895ef; color: white; }
    .badge-unknown { background: #adb5bd; color: white; }

    .method-badge {
        display: inline-block; padding: 8px 20px; border-radius: 20px;
        font-size: 0.9rem; font-weight: 600; margin: 0.5rem 0;
    }
    .method-pdfplumber { background: #52b788; color: white; }
    .method-gemini { background: #7c3aed; color: white; }
    .method-both { background: #f4a261; color: white; }

    [data-testid="stSidebar"] { background: linear-gradient(180deg, #0f2027, #203a43); }

    .footer {
        text-align: center; padding: 1.5rem; color: #6c757d;
        font-size: 0.85rem; margin-top: 3rem; border-top: 1px solid rgba(255,255,255,0.05);
    }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
#  AUTHENTICATION PAGES
# ═══════════════════════════════════════════════════════════════════════════

def show_login():
    """Render the login page."""
    st.markdown("""
    <div class="main-header" style="text-align:center;">
        <h1>🔬 Lab Report Intelligence Agent</h1>
        <p>AI-Powered Lab Report Analysis for Healthcare</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown('<h2>Welcome Back</h2>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Log in to analyze your lab reports</p>', unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submit = st.form_submit_button("Login", use_container_width=True, type="primary")

        if submit:
            success, result = login(email, password)
            if success:
                st.session_state.logged_in = True
                st.session_state.user = result
                # Store token in query params for persistence
                st.query_params["session"] = result["token"]
                st.rerun()
            else:
                st.error(result)

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<p style='text-align:center; color: #94d2bd;'>Don't have an account?</p>", unsafe_allow_html=True)
        if st.button("Create Account", use_container_width=True):
            st.session_state.auth_page = "signup"
            st.rerun()


def show_signup():
    """Render the signup page."""
    st.markdown("""
    <div class="main-header" style="text-align:center;">
        <h1>🔬 Lab Report Intelligence Agent</h1>
        <p>AI-Powered Lab Report Analysis for Healthcare</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown('<h2>Create Account</h2>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Sign up to get started</p>', unsafe_allow_html=True)

    with st.form("signup_form", clear_on_submit=False):
        full_name = st.text_input("Full Name", placeholder="John Doe")
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="Min 6 characters")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
        submit = st.form_submit_button("Sign Up", use_container_width=True, type="primary")

        if submit:
            if password != confirm_password:
                st.error("Passwords do not match.")
            else:
                success, message = signup(full_name, email, password)
                if success:
                    st.success(message)
                    st.session_state.auth_page = "login"
                    st.rerun()
                else:
                    st.error(message)

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<p style='text-align:center; color: #94d2bd;'>Already have an account?</p>", unsafe_allow_html=True)
        if st.button("Back to Login", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
#  AUTH GATE
# ═══════════════════════════════════════════════════════════════════════════

if not st.session_state.logged_in:
    if st.session_state.auth_page == "signup":
        show_signup()
    else:
        show_login()
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════
#  DASHBOARD (only accessible after login)
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
    <h1>🔬 Lab Report Intelligence Agent</h1>
    <p>Upload your lab report PDF — works with both structured tables AND unstructured/scanned reports</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    user = st.session_state.user
    st.markdown(f"### 👤 {user['full_name']}")
    st.caption(user['email'])
    if st.button("Logout", use_container_width=True):
        # Remove session from DB
        token = user.get("token")
        db_logout(token)
        # Clear query params
        st.query_params.clear()
        # Clear session state
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.auth_page = "login"
        st.rerun()

    st.markdown("---")
    st.markdown("### Settings")
    if "gemini_key" not in st.session_state:
        st.session_state.gemini_key = ""
    
    api_key = st.text_input(
        "Google Gemini API Key",
        type="password",
        value=st.session_state.gemini_key
    )
    
    if api_key:
        st.session_state.gemini_key = api_key
        os.environ["GOOGLE_API_KEY"] = api_key
        st.success("API Key configured")
    else:
        st.warning("No API key — only structured PDFs will work.")

    st.markdown("---")
    st.markdown("### How It Works")
    st.markdown("""
    **Step 1:** Try pdfplumber (tables + regex)
    
    **Step 2:** If that fails → send PDF to **Gemini Vision**
    
    **Step 3:** Compare results with medical benchmarks
    
    **Step 4:** Generate AI summaries
    """)

    st.markdown("---")
    st.markdown("### Benchmark Database")
    try:
        benchmarks = load_benchmark_db()
        st.success(f"{len(benchmarks)} tests loaded")
        categories = sorted(set(b["category"] for b in benchmarks))
        selected_cat = st.selectbox("Browse:", ["All"] + categories)
        display = benchmarks if selected_cat == "All" else [b for b in benchmarks if b["category"] == selected_cat]
        with st.expander(f"View {len(display)} tests"):
            for b in display:
                st.markdown(f"**{b['test_name']}** ({b['unit']}): {b['low']} - {b['high']}")
    except Exception as e:
        st.error(f"Error: {e}")

# ---------------------------------------------------------------------------
# Demo Data
# ---------------------------------------------------------------------------
DEMO_DATA = [
    {"test_name": "Hemoglobin", "value": 10.2, "unit": "g/dL", "ref_range_text": "12.0 - 17.5"},
    {"test_name": "White Blood Cell Count", "value": 12500, "unit": "cells/uL", "ref_range_text": "4000 - 11000"},
    {"test_name": "Platelet Count", "value": 250000, "unit": "cells/uL", "ref_range_text": "150000 - 400000"},
    {"test_name": "Red Blood Cell Count", "value": 4.5, "unit": "million/uL", "ref_range_text": "4.0 - 6.0"},
    {"test_name": "Hematocrit", "value": 38.0, "unit": "%", "ref_range_text": "36.0 - 54.0"},
    {"test_name": "MCV", "value": 78.0, "unit": "fL", "ref_range_text": "80.0 - 100.0"},
    {"test_name": "Fasting Blood Sugar", "value": 132, "unit": "mg/dL", "ref_range_text": "70 - 100"},
    {"test_name": "HbA1c", "value": 6.8, "unit": "%", "ref_range_text": "4.0 - 5.7"},
    {"test_name": "Total Cholesterol", "value": 245, "unit": "mg/dL", "ref_range_text": "< 200"},
    {"test_name": "HDL Cholesterol", "value": 35, "unit": "mg/dL", "ref_range_text": "40 - 60"},
    {"test_name": "LDL Cholesterol", "value": 165, "unit": "mg/dL", "ref_range_text": "< 100"},
    {"test_name": "Triglycerides", "value": 180, "unit": "mg/dL", "ref_range_text": "< 150"},
    {"test_name": "Creatinine", "value": 0.9, "unit": "mg/dL", "ref_range_text": "0.6 - 1.2"},
    {"test_name": "Blood Urea Nitrogen", "value": 15, "unit": "mg/dL", "ref_range_text": "7 - 20"},
    {"test_name": "ALT", "value": 28, "unit": "U/L", "ref_range_text": "7 - 56"},
    {"test_name": "AST", "value": 32, "unit": "U/L", "ref_range_text": "10 - 40"},
    {"test_name": "TSH", "value": 2.5, "unit": "uIU/mL", "ref_range_text": "0.4 - 4.0"},
    {"test_name": "Vitamin D", "value": 18, "unit": "ng/mL", "ref_range_text": "30 - 100"},
    {"test_name": "Vitamin B12", "value": 350, "unit": "pg/mL", "ref_range_text": "200 - 900"},
    {"test_name": "Sodium", "value": 140, "unit": "mEq/L", "ref_range_text": "136 - 145"},
    {"test_name": "Potassium", "value": 4.2, "unit": "mEq/L", "ref_range_text": "3.5 - 5.0"},
]

# ---------------------------------------------------------------------------
# Upload Section
# ---------------------------------------------------------------------------
col_upload, col_demo = st.columns([3, 1])

with col_upload:
    st.markdown("### Upload Your Lab Report")
    uploaded_file = st.file_uploader(
        "Choose a PDF file (any format - structured, scanned, handwritten)",
        type=["pdf"],
    )

with col_demo:
    st.markdown("### Or Try Demo")
    use_demo = st.button("Run Demo", use_container_width=True, type="primary")

# ---------------------------------------------------------------------------
# PROCESSING
# ---------------------------------------------------------------------------
extracted_data = None
extraction_method = "demo"

if uploaded_file is not None:
    pdf_bytes = uploaded_file.read()

    st.markdown("---")
    with st.spinner("Step 1: Trying pdfplumber extraction (structured PDF)..."):
        import io
        plumber_results = pdfplumber_parse(io.BytesIO(pdf_bytes))

    if len(plumber_results) >= 3:
        extracted_data = plumber_results
        extraction_method = "pdfplumber"
        st.markdown('<span class="method-badge method-pdfplumber">Extracted using pdfplumber (structured PDF)</span>', unsafe_allow_html=True)
        st.success(f"pdfplumber extracted **{len(extracted_data)}** test results!")
    else:
        if plumber_results:
            st.warning(f"pdfplumber only found {len(plumber_results)} test(s) - not enough. Trying Gemini Vision...")
        else:
            st.warning("pdfplumber could not extract unstructured data. Trying Gemini Vision...")

        if not api_key:
            st.error("**No Gemini API key!** This PDF appears to be unstructured. "
                     "Please enter your Google Gemini API key in the sidebar.")
            st.info("Get a free API key from [Google AI Studio](https://aistudio.google.com/apikey)")
        else:
            with st.spinner("Step 2: Sending PDF to Gemini Vision for extraction..."):
                gemini_results, gemini_error = gemini_extract_from_pdf(pdf_bytes, api_key)

            if gemini_results:
                if plumber_results:
                    existing = {r['test_name'].lower() for r in plumber_results}
                    merged = list(plumber_results)
                    for gr in gemini_results:
                        if gr['test_name'].lower() not in existing:
                            merged.append(gr)
                    extracted_data = merged
                    extraction_method = "pdfplumber+gemini"
                    st.markdown('<span class="method-badge method-both">Extracted using pdfplumber + Gemini Vision</span>', unsafe_allow_html=True)
                else:
                    extracted_data = gemini_results
                    extraction_method = "gemini"
                    st.markdown('<span class="method-badge method-gemini">Extracted using Gemini Vision (unstructured PDF)</span>', unsafe_allow_html=True)

                st.success(f"Successfully extracted **{len(extracted_data)}** test results!")
            else:
                st.error(f"Gemini extraction failed: {gemini_error}")
                st.info("Please check your API key and try again.")

elif use_demo:
    extracted_data = DEMO_DATA
    extraction_method = "demo"
    st.info("**Demo Mode:** Using sample data with intentional abnormalities.")

# ---------------------------------------------------------------------------
# VECTOR DB — Store report + Retrieve past reports
# ---------------------------------------------------------------------------
report_text_for_db = None
past_reports = []

if extracted_data and uploaded_file is not None:
    # Build text representation of extracted data
    report_text_for_db = "\n".join(
        f"{r['test_name']}: {r['value']} {r['unit']} (Ref: {r.get('ref_range_text', 'N/A')})"
        for r in extracted_data
    )
    user_id = str(st.session_state.user["id"])
    report_name = uploaded_file.name

    # Store current report
    try:
        with st.spinner("Storing report in memory..."):
            rid = store_report(user_id, report_text_for_db, report_name)
        st.success(f"Report saved to memory (ID: {rid[:20]}...)")
    except Exception as e:
        st.warning(f"Could not save to memory: {e}")

    # Retrieve past reports (excluding the one we just stored)
    try:
        with st.spinner("Searching for your previous reports..."):
            all_past = get_user_reports(user_id, report_text_for_db, n_results=6)
            # Filter out the report we just stored (same text)
            past_reports = [r for r in all_past if r["document"].strip() != report_text_for_db.strip()]
            past_reports = past_reports[:5]
        if past_reports:
            st.info(f"Found **{len(past_reports)}** previous report(s) for comparison!")
    except Exception as e:
        st.warning(f"Could not search memory: {e}")

# ---------------------------------------------------------------------------
# ANALYSIS & DISPLAY
# ---------------------------------------------------------------------------
if extracted_data:
    with st.spinner("Comparing with medical benchmarks..."):
        benchmarks = load_benchmark_db()
        compared = compare_with_benchmarks(extracted_data, benchmarks)
        stats = get_summary_stats(compared)

    st.markdown("---")
    st.markdown("### Results Dashboard")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-card stat-total"><div class="label">Total Tests</div><div class="number">{stats["total"]}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card stat-normal"><div class="label">Normal</div><div class="number">{stats["normal"]}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card stat-high"><div class="label">Above Range</div><div class="number">{stats["high"]}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card stat-low"><div class="label">Below Range</div><div class="number">{stats["low"]}</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Detailed Test Results")

    categories = {}
    for r in compared:
        cat = r.get("category", "Uncategorized")
        categories.setdefault(cat, []).append(r)

    for cat, tests in categories.items():
        with st.expander(f"{cat} ({len(tests)} tests)", expanded=True):
            for t in tests:
                status = t["status"]
                emoji = {"NORMAL": "🟢", "HIGH": "🔴", "LOW": "🔵"}.get(status, "⚪")
                css_class = f"result-{status.lower()}"
                badge_class = f"badge-{status.lower()}"
                ref_display = f"{t['benchmark_low']} - {t['benchmark_high']}" if t["benchmark_low"] is not None else t.get("ref_range_text", "N/A")

                st.markdown(f"""
                <div class="result-row {css_class}">
                    <div>
                        <strong>{emoji} {t['test_name']}</strong><br>
                        <small style="color: #adb5bd;">{t.get('description', '')[:100]}</small>
                    </div>
                    <div style="text-align: right;">
                        <strong>{t['value']} {t['unit']}</strong><br>
                        <small>Ref: {ref_display} {t['unit']}</small><br>
                        <span class="badge {badge_class}">{status}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### AI-Generated Summaries")

    tab_names = ["Patient Summary", "Clinical Summary"]
    if past_reports:
        tab_names.append("Report History & Comparison")

    tabs = st.tabs(tab_names)

    with tabs[0]:
        if st.button("Generate Patient Summary", key="pat_btn", use_container_width=True, type="primary"):
            with st.spinner("Generating patient-friendly summary..."):
                patient_summary = None
                if api_key:
                    patient_summary, _ = gemini_evaluate_results(compared, api_key)
                if not patient_summary:
                    patient_summary = generate_patient_summary_fallback(compared)
                st.markdown(patient_summary)
                st.download_button("Download", patient_summary, "patient_summary.md", "text/markdown")

    with tabs[1]:
        if st.button("Generate Clinical Summary", key="clin_btn", use_container_width=True):
            with st.spinner("Generating clinical summary..."):
                clinical_summary = None
                if api_key:
                    _, clinical_summary = gemini_evaluate_results(compared, api_key)
                if not clinical_summary:
                    clinical_summary = generate_clinical_summary_fallback(compared)
                st.markdown(clinical_summary)
                st.download_button("Download", clinical_summary, "clinical_summary.md", "text/markdown")

    if past_reports:
        with tabs[2]:
            st.markdown("#### Previous Reports Found")
            for i, rpt in enumerate(past_reports, 1):
                with st.expander(f"Report {i}: {rpt['report_name']} ({rpt['upload_date']})"):
                    st.text(rpt["document"][:2000])

            st.markdown("---")
            if st.button("Generate Trend Comparison", key="compare_btn", use_container_width=True, type="primary"):
                if not api_key:
                    st.error("Gemini API key required for AI comparison.")
                else:
                    with st.spinner("Comparing with previous reports using Gemini AI..."):
                        comparison = generate_report_comparison(
                            report_text_for_db, past_reports, api_key
                        )
                    if comparison:
                        st.markdown(comparison)
                        st.download_button(
                            "Download Comparison", comparison,
                            "report_comparison.md", "text/markdown"
                        )
                    else:
                        st.warning("Could not generate comparison. Try again.")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("""
<div class="footer">
    <p><strong>Lab Report Intelligence Agent</strong> — Healthcare Hackathon Project</p>
    <p>For educational purposes only. Not a substitute for professional medical advice.</p>
    <p>Built with Streamlit, pdfplumber, Google Gemini AI</p>
</div>
""", unsafe_allow_html=True)
