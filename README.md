# SRS-Based Automated Project Timeline and Cost Estimator

A complete prototype system that accepts a Software Requirements Specification (SRS) document or project description as input and automatically generates:
1. Module-wise project breakdown (Work Breakdown Structure)
2. Effort estimation per module based on complexity and keywords
3. Total estimated timeline in days
4. Total estimated cost based on labor scale and fixed infrastructure

## 🚀 Features
- **NLP Extraction**: Uses `spaCy` and regular expressions to extract nouns, potential modules, and complexity indicators (e.g., "real-time", "AI", "secure").
- **Dynamic Costing**: Configure developer hourly rate to auto-calculate the overall price of the project.
- **Modern UI**: Clean, minimalistic web dashboard built using modern glassmorphism design.
- **REST API**: Standard JSON output format for timeline and phasing.

## 🛠 Tech Stack
- **Backend:** Python, FastAPI, uvicorn
- **NLP:** spaCy (`en_core_web_sm`)
- **Frontend:** Vanilla HTML5, CSS3, JavaScript

## 📦 Step-by-Step Setup

1. **Navigate to the Directory:**
```bash
cd srs-estimator
```

2. **Create a Virtual Environment (Optional but recommended):**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
```

3. **Install Dependencies:**
```bash
pip install -r requirements.txt
```

4. **Start the Application:**
```bash
python main.py
```
*Note: Upon the first run, the app will automatically download the required spaCy model `en_core_web_sm` if it is not already installed.*

5. **Access the Web UI:**
Open your browser and navigate to: [http://localhost:8000](http://localhost:8000)

## 🧪 Sample Test Input

Paste this exactly into the input box and click **Generate Estimate**:

> *The system should provide user authentication, a real-time analytics dashboard, and AI-based prediction features with secure data handling.*

**Expected Output Visualization:**
- **Modules**: Authentication, Analytics Dashboard, AI Prediction Features (etc.)
- **Timeline**: ~20+ Days (Depends on base logic multipliers)
- **Cost**: Calculated via `8 hours * days * rate` plus base infrastructure cost.

## 🧠 Constraints & Extensibility
This system is minimal but completely functional, explicitly designed not to be over-engineered. Next steps for a production AI-based estimator would involve using an LLM (such as OpenAI or Gemini API) logic in place of the `spaCy` extraction heuristics, which would offer even greater accuracy across complex texts.
