# Sentinel SafetyAI / SurakshaSetu (SIH26165)
### AI-Powered Industrial Safety Intelligence Platform for Oil India Limited (OIL)

Sentinel SafetyAI is an industrial safety intelligence and SIF (Serious Injury & Fatality) precursor prevention platform. It processes safety observations, near-misses, and incident narratives to predict accident severity levels (I to V), identify hazardous precursors, calculate compound risk scores, retrieve historical precedents, and enable human-in-the-loop safety officer governance.

---

## 🚀 Quick Setup & Local Run Instructions

### 1. Backend Setup (FastAPI + Python ML)

```bash
# 1. Create and activate a Python 3.10+ virtual environment
python -m venv backend/venv

# On Windows:
backend\venv\Scripts\activate
# On Linux / macOS:
source backend/venv/bin/activate

# 2. Install exact pinned dependencies
pip install -r backend/requirements.txt

# 3. Start the FastAPI backend server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
* **API Documentation (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Backend Health Check**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

### 2. Frontend Setup (Next.js 16 + Tailwind CSS)

```bash
# 1. Install Node.js dependencies
npm install

# 2. Start Next.js development server
npm run dev
```
* **Web Dashboard**: [http://localhost:3000](http://localhost:3000)
* **Analytics & Model Validation**: [http://localhost:3000/analytics-dashboard](http://localhost:3000/analytics-dashboard)
* **Submit Safety Report**: [http://localhost:3000/submit-report](http://localhost:3000/submit-report)

---

### 3. Docker Deployment (Optional)

```bash
docker compose up -d --build
```
* **Frontend**: `http://localhost:3000`
* **Backend API**: `http://localhost:8000`

---

### 4. Cloud Deployment (Vercel + Render / Railway)

For step-by-step production deployment instructions with free hosting on Vercel and Render:
* Refer to [DEPLOYMENT.md](file:///c:/Users/rauna/Downloads/safety-intelligence-platform/DEPLOYMENT.md)
* Automated Render Blueprint: [render.yaml](file:///c:/Users/rauna/Downloads/safety-intelligence-platform/render.yaml)

---

## ⚙️ Environment Configuration

### Frontend (`.env` or environment variables)
```ini
# Base URL for the FastAPI backend service
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```
*In production, set `NEXT_PUBLIC_API_URL` to your deployed backend domain (e.g. `https://api.yourdomain.com`).*

### Backend (`backend/.env` or environment variables)
```ini
PORT=8000
HOST=0.0.0.0
# Allowed frontend origins (comma-separated, or * for open testing)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

---

## 🛡️ Architecture, Roles & Transparency Disclosures

### 1. Role-Based Access Control (RBAC)
* **Employee Role**: Can log in, submit safety observations, attach field photos, execute AI analysis, view historical precedent cases, and view operational analytics. Employees cannot submit or alter safety officer reviews or update officer-restricted action statuses (HTTP 403 Forbidden is strictly enforced by the backend API).
* **Safety Officer Role**: Can submit observations, execute AI analysis, submit authoritative human reviews (Accept/Modify/Reject), initiate corrective action plans, acknowledge/resolve SIF risk alerts, and verify action completions.
* *Note: The current prototype implements session-based role authorization for demonstration. Production enterprise rollout should integrate with corporate SSO/OAuth/SAML providers.*

### 2. Data Persistence
* **JSON File Storage**: The prototype stores active state in `backend/data/` (`alerts_store.json`, `actions_store.json`, `reviews_store.json`) using atomic writes (`.tmp` + `os.replace`) to prevent corruption. Seeded records serve as baseline demonstration data, while live runtime submissions generate genuine records.
* *Note: JSON persistence is engineered for prototype and single-instance deployments. Multi-instance distributed enterprise production should connect to a PostgreSQL database.*

### 3. File Upload & Processing Support
* **Tabular Batch Upload**: Fully supports `.csv`, `.xlsx`, `.xls`, `.parquet`, and `.json` datasets with row-level validation and non-breaking error handling.
* **Field Evidence Images**: Supports `.png`, `.jpeg`, `.jpg`, and `.webp` attachments up to 10MB with PIL integrity validation.
* **Document PDF Support**: Tabular data files are fully supported. Unstructured multi-page document PDF text extraction is documented as a future roadmap enhancement.

### 4. Machine Learning Model & Evaluation Methodology
* **Model Architecture**: Linear Support Vector Machine (Linear SVM) with Platt Scaling calibration, class balancing, and sublinear TF-IDF (1–2 word n-grams).
* **Zero Data Leakage**: Evaluated strictly on an untouched 15% Holdout test partition (62 records) never seen during feature selection, cross-validation, or tuning.
* **Genuine Holdout Performance Metrics**:
  * **Overall Accuracy**: **56.45%** (35 / 62 correct predictions)
  * **Macro Precision**: **48.27%**
  * **Macro Recall**: **50.77%**
  * **Macro F1 Score**: **49.45%**
  * **Weighted F1 Score**: **54.85%**
* *All metrics displayed on the dashboard are read dynamically from `backend/data/evaluation_metrics.json` and generated programmatically without hardcoded fallbacks.*

---

## 🧪 Testing & Validation

```bash
# Run all 121 backend unit & integration tests
python -m unittest discover backend -v

# Run frontend TypeScript type checking
npx tsc --noEmit

# Run Next.js production build validation
npm run build
```
