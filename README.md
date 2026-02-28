# Lab Report Intelligence Agent

An AI-powered system that converts complex medical and diagnostic lab
reports into clear, patient-friendly explanations.

------------------------------------------------------------------------

## Problem Statement

Medical lab reports are often difficult for patients to understand.\
They contain complex terminology, medical ranges, abbreviations, and
values that can cause confusion or anxiety.

This project aims to:

-   Parse structured and scanned lab reports
-   Compare values with medical benchmarks
-   Highlight abnormal readings clearly
-   Generate simple explanations in plain language
-   Track trends across previous reports

------------------------------------------------------------------------

## Key Features

-   Structured PDF parsing using PDFPlumber
-   OCR extraction for scanned reports using Gemini Vision
-   Data normalization and benchmark mapping
-   RAG-based medical explanation retrieval
-   Persistent patient history using ChromaDB
-   Human-friendly AI-generated summaries
-   Trend comparison with previous reports
-   Secure authentication with SQLite

------------------------------------------------------------------------

## System Architecture

### 1. File Upload & Smart Detection

-   Structured PDFs → Parsed using **PDFPlumber**
-   Scanned/Image-based reports → Extracted using **Gemini Vision (OCR +
    understanding)**

Output is standardized into JSON format:

``` json
{
  "test_name": "",
  "value": "",
  "unit": "",
  "reference_range": "",
  "patient_info": "",
  "date": ""
}
```

------------------------------------------------------------------------

### 2. Data Normalization & Benchmark Mapping

-   Unit standardization (mg/dL vs mmol/L)
-   Test name normalization (Hb, HGB, Hemoglobin)
-   Reference range alignment

Each test is labeled as: - Normal - Borderline - High - Low

------------------------------------------------------------------------

### 3. RAG-Based Knowledge Retrieval

Using LangChain RAG pipeline to retrieve: - Simplified medical
explanations - Contextual meaning of lab tests - Trusted medical
reference notes - Relevant patient history

------------------------------------------------------------------------

### 4. Patient Memory & Trend Tracking (ChromaDB)

-   Persistent user history
-   Fast retrieval of past reports
-   Trend analysis (e.g., increasing HbA1c)
-   Longitudinal health insights

------------------------------------------------------------------------

### 5. AI-Powered Summary Generation

Combines: - Current lab values - Benchmark comparison - Retrieved
medical context - Previous reports

Generates: - Plain-language summary - Highlighted abnormal values -
"What this means" explanations - Previous vs current comparison - Safe
next-step suggestions

------------------------------------------------------------------------

## Tech Stack

-   Python
-   PDFPlumber
-   Gemini Vision
-   LangChain
-   ChromaDB
-   LLM Integration (Gemini / OpenAI)
-   SQLite
-   Streamlit

------------------------------------------------------------------------

## Installation

### Clone Repository

``` bash
git clone https://github.com/your-username/lab-report-intelligence-agent.git
cd lab-report-intelligence-agent
```

### Create Virtual Environment

``` bash
conda create -n labagent python=3.10
conda activate labagent
```

### Install Dependencies

``` bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file:

    GEMINI_API_KEY=your_api_key
    OPENAI_API_KEY=your_api_key

------------------------------------------------------------------------

## Run the Application

``` bash
streamlit run app.py
```

------------------------------------------------------------------------

## Project Structure

    .
    ├── app.py
    ├── parser.py
    ├── agent.py
    ├── benchmark_db/
    ├── chroma_db/
    ├── requirements.txt
    └── README.md

------------------------------------------------------------------------

## Demo

Live Application:\
https://mohdabdulrah-lab-report-intelligence-agent-app-i5fjju.streamlit.app/?session=34d55487f2ed4e4e5f45648cdff7e8eb3b47cdff47f54c2592739a6feb2e9e1a



------------------------------------------------------------------------



## Disclaimer

This system provides informational explanations only.\
It does not provide medical diagnosis.\
Users should consult healthcare professionals for clinical decisions.

------------------------------------------------------------------------

## License

Add an appropriate open-source license (MIT recommended).
