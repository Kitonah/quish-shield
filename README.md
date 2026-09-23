# QuishShield 🙅

QuishShield is an AI-powered security scanner to detect multi-vector phishing threats, including malicious URLs, QR code phishing (Quishing), and SMS phishing (Smishing). It combines domain heuristics, browser sandboxing, and deep learning visual similarity checks to identify brand impersonations.

---

## Key Features

- **URL Scanner**: Detects typosquatting, high-entropy strings, raw IP addresses, and young domains.
- **Quishing Detection**: Decodes QR codes and identifies malicious URLs or UPI payment requests.
- **Smishing Defense**: Extracts and resolves hidden links from SMS messages.
- **Multi-layer Analysis**: Combines RDAP/WHOIS lookups, Playwright headless browser sandboxing, and MobileNetV2 visual brand classification.

---

## Project Structure

- `backend/`: FastAPI backend, orchestrator, heuristics, sandbox, and AI model training code.
- `frontend/quishshield-frontend/`: React 19 + Vite + Tailwind CSS web interface.

---

## Quick Start

### 1. Backend Setup

```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload --port 8000
```

The API will run at `http://127.0.0.1:8000` (API documentation at `http://127.0.0.1:8000/docs`).


### 2. Frontend Setup

```bash
cd frontend/quishshield-frontend
npm install
npm run dev
```

Visit the frontend dashboard at `http://localhost:5173`.

---

## Visual Model Training (Optional)

```bash
cd backend
python collect_data.py
python train_model.py
```
