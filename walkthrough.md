# SIH26165 Final Walkthrough: Safety Intelligence Platform
**Oil India Limited (Problem Statement #165)**
*AI/NLP Engine to Detect Serious Injury & Fatality (SIF) Precursors in Unsafe-Act/Unsafe-Condition and Near-Miss Reports*

---

## 🌟 Executive Summary

The Safety Intelligence Platform provides an end-to-end industrial safety intelligence architecture specifically adapted to Oil India Limited exploration and production operations. The platform transforms unstructured text observations into real-time hazard signals, calibrated severity predictions, transparent risk scores, historical vector precedents, and evidence-based corrective actions, with mandatory Human-in-the-Loop Safety Officer sign-off.

---

## 🧭 Visual 8-Stage Intelligence Pipeline

The frontend and backend communicate the following 8-stage decision support flow:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. INPUT                                                                │
│    • Free-text field observation, location, department, reporter role   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. NLP UNDERSTANDING                                                    │
│    • Acronym expansion (BOP, LEL, SCBA, PTW, PSI)                       │
│    • Contextual negation window (prevents "no leak" false positives)    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. SIF PRECURSOR DETECTION                                              │
│    • 11-category domain taxonomy (High Pressure, Gas Leak, PPE, etc.)  │
│    • Direct text evidence extraction & attribution                      │
└────────────────────────────────────┬────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. SEVERITY PREDICTION                                                  │
│    • Linear SVM with balanced TF-IDF (Levels I to V)                   │
│    • Hyperplane margin confidence & zero false-alarm rule calibration   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. RISK ASSESSMENT                                                      │
│    • Transparent explainable SIF score ($0 \le \text{Score} \le 100$)             │
│    • Additive base precursor points + multi-hazard compounding synergy  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. HISTORICAL EVIDENCE                                                  │
│    • Sublinear TF-IDF + Cosine similarity over 425 historical cases     │
│    • Strictly bounded ($0.0 \le \text{sim} \le 1.0$) with 10% cutoff threshold  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 7. RECOMMENDED ACTION                                                   │
│    • Prescriptive controls: immediate control, physical verification    │
│    • Assigned field safety role, escalation condition, follow-up MOC    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 8. HUMAN SAFETY REVIEW                                                  │
│    • Safety officer authoritative review deck (Accept / Modify / Reject)│
│    • Separate immutable audit archive & OISD compliance tracking        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Summary of Tasks Completed

| Task # | Module / Feature Area | Key Deliverables & Validation |
| :--- | :--- | :--- |
| **Task 1** | **Technical Codebase Audit** | Full audit of 425-report dataset, Linear SVM severity model, TF-IDF cosine retrieval, and API schema mapping. |
| **Task 2** | **Safety Data Pipeline** | `SafetyDataPipeline` (`backend/services/data_pipeline.py`) preserving original 425 records with non-destructive normalization and deduplication. |
| **Task 3** | **SIF Precursor Taxonomy** | 11-category domain taxonomy (`SIF_TAXONOMY`) with regex, keywords, consequences, and severity weights. |
| **Task 4** | **Hybrid NLP Detection Engine** | Context-aware regex matching + active negation window filtering (`"no gas leak"` $\to$ no false alarm). |
| **Task 5** | **Severity Model Evaluation** | Reproducible evaluation script (`backend/evaluate_model.py`) reporting 91.94% accuracy, 92.76% Macro-F1 on zero-leakage holdout test set. |
| **Task 6** | **Explainable Risk Scoring** | Centralized `RiskScoringConfig` with mathematical formula attribution and compounding multi-hazard boost. |
| **Task 7** | **Historical Incident Retrieval** | Cosine similarity normalization ($0.0 \le \text{sim} \le 1.0$), 10% minimum thresholding, authentic case matching. |
| **Task 8** | **Evidence-Based Actions** | Hierarchical corrective actions with immediate containment, verification step, responsible role, and escalation triggers. |
| **Task 9** | **Human-in-the-Loop Safety Review** | Safety Officer Review deck (`ReviewService`, `/review/submit`, interactive Accept/Modify/Reject controls, audit persistence). |
| **Task 10** | **Analytics & Validation Module** | `SafetyAnalyticsService` with separated Operational Analytics vs Zero-Leakage ML Model Validation (5x5 confusion matrix, per-class recall). |
| **Task 11** | **End-to-End System Validation** | Comprehensive 9-scenario test suite (`backend/test_e2e.py`) verifying full pipeline flow and schema consistency. |
| **Task 12** | **Final Demo Polish** | Visual 8-stage progress tracker, high-contrast industrial UI, live simulator, and interactive review decks. |

---

## 🧪 Comprehensive Automated Test Results

The backend contains **38 automated unit and end-to-end tests across 7 test suites**, all passing cleanly:

```bash
......................................
----------------------------------------------------------------------
Ran 38 tests in 10.312s

OK (All 38 Tests Passed)
```

- **`test_pipeline.py`** (6 tests): Data ingestion, text cleaning, acronym expansion, stratified holdout splits.
- **`test_risk.py`** (6 tests): Taxonomy rules, negation filtering, explainable scoring tiers.
- **`test_similarity.py`** (5 tests): Cosine bounds, authentic case matching, threshold cutoffs.
- **`test_actions.py`** (5 tests): Hierarchy of controls, evidence traceability, role assignments.
- **`test_review.py`** (4 tests): Review submission, acceptance, modification, rejection, and audit log retrieval.
- **`test_analytics.py`** (3 tests): Operational distributions, ML performance metrics, confusion matrix.
- **`test_e2e.py`** (9 tests): All 9 end-to-end operational scenarios.
- **TypeScript Compilation**: `npx tsc --noEmit` exited with code `0` (Zero errors).

---

## 🚀 How to Run the Platform Locally

### 1. Start the FastAPI Backend
```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

### 2. Start the Next.js Frontend
```bash
npm run dev
```
Open **`http://localhost:3000`** in your browser.

### 3. Key URLs for Demo
* **Live Landing Page & Simulator**: `http://localhost:3000/`
* **Observation Submission Portal**: `http://localhost:3000/submit-report`
* **SIF Analysis & Officer Review Deck**: `http://localhost:3000/analysis`
* **Model Analytics & Validation**: `http://localhost:3000/analytics-dashboard`
* **FastAPI Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`
