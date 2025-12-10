# 🤖 Smart Recruiter AI  
### A RAG-Based Agentic Resume Screener (v2.0)

**Status:** Completed  
**Tech Stack:** Python, Docling, OpenSearch, Google Gemini, Streamlit

---

## 1. Executive Summary

### The Problem  
Traditional Applicant Tracking Systems (ATS) rely on brittle keyword matching. They often reject qualified candidates due to issues such as:

- Inconsistent resume formats (columns, tables).  
- Synonyms or non-standard terminology (e.g., rejecting “Team Lead” for “Manager”).  
- Slow, manual screening prone to unconscious bias.

### The Solution  
**Smart Recruiter AI** is an intelligent resume screening agent that reads and interprets resumes like a human. It uses:

- **Docling** for layout-aware parsing,  
- **OpenSearch** for hybrid search (Vectors + Keywords),  
- **Gemini 1.5 Flash** for reasoning and evaluation.

It generates candidate fit scores, computes experience mathematically, removes bias via “Blind Mode,” and provides full explainability.

---

## 2. System Architecture

The solution follows a modern **RAG (Retrieval-Augmented Generation)** pipeline enhanced with **Agentic Reasoning**.

### Components

| Component | Technology | Role |
|----------|------------|------|
| **Ingestion Engine** | Docling (IBM) | Parses complex PDFs into structured Markdown |
| **Vector Database** | OpenSearch | Stores chunked resumes; performs hybrid (k-NN + BM25) search |
| **Reasoning Engine** | Gemini 1.5 Flash | Extracts JD criteria, evaluates candidates, drafts emails |
| **Frontend UI** | Streamlit | HR dashboard for JD uploads and candidate analysis |
| **Containerization** | Docker | Runs OpenSearch single-node cluster |

### Data Pipeline Flow

**Ingestion (ETL):**  
PDF Resume → Docling Layout Analysis → Semantic Chunking → Gemini Embedding → OpenSearch Index

**Retrieval (RAG):**  
JD Upload → Criteria Extraction → Hybrid Query → Top-K Resume Retrieval

**Inference (Agent):**  
Retrieved Chunks → Gemini Evaluation (Fit Score, Strengths, Weaknesses) → Streamlit UI

---

## 3. Key Technical Features

### A. Semantic Chunking (Precision Upgrade)
Traditional fixed-size chunking breaks context.  
This project implements a **Markdown header–aware custom splitter** based on Docling output.

**Benefit:**  
Searches for skills like “Python” map directly to the *Technical Skills* section rather than scattered references.

---

### B. Hybrid Search (Recall Upgrade)
Combines:

- **k-NN vector search** for conceptual similarity  
- **BM25 keyword scoring** for exact skill matches  

Additionally, a deduplication step aggregates similar chunks and returns a single best candidate representation.

---

### C. Agentic “Blind Mode” (Bias Removal)
Supports DE&I initiatives.

- Automatically redacts PII (Names, Addresses, Universities)
- Replaces identifiers with “Candidate X”
- Ensures neutral, unbiased evaluation

---

### D. Mathematical Reasoning
The system **calculates** experience using explicit date ranges.

Example:  
If a candidate lists “2018–2020” and “2021–Present,” the agent computes total years and compares it against JD requirements.

---

## 4. Project Directory Structure

```
smart-recruiter-v2/
├── data/                  # PDF resumes
├── docker-compose.yml     # OpenSearch infrastructure
├── requirements.txt       # Dependencies
├── .env                   # API keys and environment variables
├── ingest.py              # ETL: Parse & index resumes
├── backend.py             # Core logic: Search, scoring, comparison
└── app.py                 # Streamlit UI
```

---

## 5. Installation & Setup Guide

### Prerequisites
- Python 3.10+
- Docker Desktop (running)
- Google AI Studio API Key

### Step 1: Environment Setup
```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Database Initialization
```bash
docker compose up -d
```
Verify access:  
Visit `http://localhost:5601`.

### Step 3: Configuration
Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_actual_api_key_here
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
```

### Step 4: Data Ingestion
Add PDF resumes to `data/` and run:

```bash
python ingest.py
```

### Step 5: Launch Application
```bash
streamlit run app.py
```

---

## 6. Usage Walkthrough

1. **Upload Job Description:** Add a JD in PDF format through the sidebar.  
2. **Automatic Parsing:** AI extracts key skills and mandatory criteria.  
3. **Candidate Scoring:**  
   - Fit Score ranges from 0–100%.  
   - Green (80+), Orange (60–79), Red (<60).  
4. **Deep Dive:**  
   - Expand sections for detailed strengths and weaknesses.  
   - Generate candidate-specific interview questions.  
5. **Comparison:**  
   - Select two candidates for a side-by-side comparison table.  
6. **Action:**  
   - Generate personalized rejection email drafts.

---

## 7. Future Roadmap

- GPU Acceleration: Enable CUDA-powered parsing for faster Docling OCR.  
- Cloud Deployment: Package Streamlit + OpenSearch for AWS/Azure.  
- Feedback Loop: Add a recruiter rating mechanism for continuous learning.

---

## Author

**Gaurav Singh**  
Advanced Data Science Associate | ZS Associates  | NIT Trichy '24
Specialization: GenAI, RAG, and Large-Scale Data Processing
