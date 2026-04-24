# SRS Estimator — Technical Documentation

> **SRS-Based Automated Project Timeline and Cost Estimator**  
> A tool that parses Software Requirements Specification documents to extract keywords, estimate effort, compute costs, and generate a project timeline.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Architecture & File Structure](#3-architecture--file-structure)
4. [Backend Implementation](#4-backend-implementation)
   - 4.1 [Keyword Extraction Engine](#41-keyword-extraction-engine)
   - 4.2 [Module Detection](#42-module-detection)
   - 4.3 [Complexity Scoring](#43-complexity-scoring)
   - 4.4 [Cost Calculation](#44-cost-calculation)
   - 4.5 [Timeline / Gantt Builder](#45-timeline--gantt-builder)
   - 4.6 [Team Recommendation](#46-team-recommendation)
5. [API Reference](#5-api-reference)
6. [Frontend Implementation](#6-frontend-implementation)
7. [Data Flow (End-to-End)](#7-data-flow-end-to-end)
8. [How to Start the Project](#8-how-to-start-the-project)
9. [Sample Inputs & Expected Outputs](#9-sample-inputs--expected-outputs)

---

## 1. Project Overview

The SRS Estimator takes raw SRS (Software Requirements Specification) text as input and automatically:

- **Extracts** feature keywords and complexity/technology keywords using NLP
- **Identifies** software modules and classifies their complexity (Low / Medium / High)
- **Calculates** effort in developer-days and hours
- **Estimates** full project cost (labor + infrastructure + contingency)
- **Generates** a Gantt-style timeline in two views: SDLC phases and module schedule
- **Recommends** a team composition based on project size

---

## 2. Tech Stack

### Backend

| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.9+ | Core programming language |
| **FastAPI** | 0.100+ | REST API framework — handles HTTP requests, routing, validation |
| **Uvicorn** | 0.20+ | ASGI server to run the FastAPI application |
| **spaCy** | 3.x | NLP library for noun-chunk extraction and linguistic analysis |
| **spaCy Model** | `en_core_web_sm` | Pre-trained English language model (small) |
| **Pydantic** | v2 | Request body validation and data modelling |
| **Python `re`** | stdlib | Regular expressions for keyword matching and text splitting |
| **Python `math`** | stdlib | `ceil()` for rounding up effort estimates |
| **Python `datetime`** | stdlib | Date arithmetic for building the project timeline |

### Frontend

| Technology | Purpose |
|---|---|
| **HTML5** | Semantic page structure |
| **Vanilla CSS** | All styling — CSS custom properties (variables), no framework |
| **Vanilla JavaScript (ES6+)** | Fetch API, DOM manipulation, IntersectionObserver |
| **Google Fonts (Inter)** | Typography |

### Dev / Infra

| Tool | Purpose |
|---|---|
| **Python venv** | Isolated virtual environment |
| **StaticFiles (FastAPI)** | Serves frontend files from `/static` directory |
| **CORS Middleware** | Allows cross-origin requests during development |

---

## 3. Architecture & File Structure

```
srs-estimator/
│
├── main.py              # FastAPI app — routing, middleware, static file serving
├── estimator.py         # Core estimation engine — all NLP and computation logic
├── requirements.txt     # Python dependencies
│
├── static/
│   ├── index.html       # Frontend HTML — full single-page UI
│   ├── style.css        # All CSS — layout, components, design tokens
│   └── script.js        # All JS — API calls, rendering, interactivity
│
└── venv/                # Python virtual environment (not committed)
```

### Request Flow

```
Browser  ──POST /api/estimate──►  FastAPI (main.py)
                                       │
                                  estimate_project()
                                  (estimator.py)
                                       │
                          ┌────────────┼─────────────────┐
                          │            │                  │
                   extract_keywords  extract_modules  build_gantt_timeline
                   (regex + dict)    (spaCy + regex)  (datetime math)
                          └────────────┼─────────────────┘
                                       │
                                  JSON Response
                                       │
                              Browser renders UI
```

---

## 4. Backend Implementation

All core logic lives in **`estimator.py`**. The main entry point is `estimate_project()`.

---

### 4.1 Keyword Extraction Engine

**Function:** `extract_keywords(text: str) → dict`

Two curated keyword dictionaries are defined at module level:

#### `FEATURE_KEYWORDS` (~50 entries)
Maps feature terms to canonical names.
```python
FEATURE_KEYWORDS = {
    "authentication": "Authentication",
    "login":          "User Login",
    "payment":        "Payment Gateway",
    "dashboard":      "Dashboard",
    "websocket":      "WebSocket / Real-time",
    # ...
}
```
Each keyword is matched with `re.search(r'\b' + keyword + r'\b', text_lower)` — word-boundary anchors prevent partial hits.

#### `COMPLEXITY_KEYWORDS` (~50 entries)
Maps tech terms to `(level, multiplier, category, display_name)`.
```python
COMPLEXITY_KEYWORDS = {
    "machine learning": ("high",   1.30, "ai_ml",       "Machine Learning"),
    "real-time":        ("high",   1.20, "realtime",     "Real-Time"),
    "blockchain":       ("high",   1.35, "distributed",  "Blockchain"),
    "docker":           ("medium", 1.10, "distributed",  "Docker"),
    "ssl":              ("low",    1.05, "security",     "SSL/TLS"),
    # ...
}
```

**Overall complexity score formula (0–100):**
```
score = (max_level / 3) × 60
      + (max_multiplier - 1.0) × 100
      + min(num_features × 3, 20)
      + min(num_complexity_kw × 2, 20)
```

---

### 4.2 Module Detection

**Function:** `extract_modules(text: str) → list[dict]`

**Step 1 — Clause splitting** (`_split_into_clauses`):
Bullet/newline text → commas → split on `,` `;` `.` and conjunctions.

**Step 2 — Named feature mapping** (`_map_to_known_feature`):
Checks clause against `FEATURE_KEYWORDS`; uses canonical label if matched.

**Step 3 — spaCy noun-chunk cleanup** (`_clean_clause`):
spaCy extracts noun chunks; removes determiners/pronouns; picks longest meaningful chunk as module name. Generic stop phrases filtered out.

**Step 4 — Complexity classification** (`_classify_clause`):
Checks clause against `COMPLEXITY_KEYWORDS`, returns `(level, multiplier)`.

**Module output per item:**
```json
{
  "name":       "Payment Gateway",
  "complexity": "high",
  "base_days":  12,
  "multiplier": 1.25,
  "days":       15
}
```

**Base days per complexity tier:**
| Tier | Base Days |
|---|---|
| low | 3 |
| medium | 6 |
| high | 12 |

`days = ceil(base_days × multiplier)`, minimum 1.

---

### 4.3 Complexity Scoring

The `global_multiplier` from keyword extraction is applied to the entire project's hours:
```python
total_hours_adj = ceil(total_hours × global_multiplier)
```
If the SRS mentions AI/ML (multiplier 1.30), total hours scale up 30%.

---

### 4.4 Cost Calculation

```python
total_days          = sum(mod.days for all modules)
total_hours         = total_days × 8          # 8-hr working day
total_hours_adj     = ceil(total_hours × global_multiplier)

labor_cost          = total_hours_adj × hourly_rate
infrastructure_cost = max(5000, total_days × 150)   # scales with size
contingency         = round(labor_cost × 0.10)       # 10% buffer
total_cost          = labor_cost + infrastructure_cost + contingency
```

| Component | Formula |
|---|---|
| Labor | Adjusted hours × hourly rate (₹/hr) |
| Infrastructure | `max(₹5,000, days × ₹150)` |
| Contingency | 10% of labor cost |
| **Total** | Sum of all three |

---

### 4.5 Timeline / Gantt Builder

**Function:** `build_gantt_timeline(modules, total_days, start_date)`

#### SDLC Phase Timeline (6 standard phases)
| Phase | Weight |
|---|---|
| Requirements & Planning | 10% |
| System Design & Architecture | 15% |
| Backend Development | 30% |
| Frontend Development | 25% |
| Testing & QA | 12% |
| Deployment & DevOps | 8% |

Each phase: `days = ceil(total_days × weight)`. Dates computed via `timedelta`.

#### Module Timeline
Modules scheduled sequentially. Each starts after the previous ends. ISO date strings returned for the frontend.

---

### 4.6 Team Recommendation

**Function:** `recommend_team(total_days, num_modules)`

| Size | Days | Total People |
|---|---|---|
| Small | ≤ 30 | 2 (1 Dev + 1 Designer) |
| Medium | ≤ 90 | 5 (2 Dev + 1 Designer + 1 QA + 1 PM) |
| Standard | ≤ 180 | 9 (3 Dev + 2 Designer + 2 QA + 1 DevOps + 1 PM) |
| Large | > 180 | 14 (5 Dev + 2 Designer + 3 QA + 2 DevOps + 2 PM) |

---

## 5. API Reference

### `POST /api/estimate`

**Request body:**
```json
{
  "text":        "The system shall provide...",
  "hourly_rate": 500.0,
  "start_date":  "2026-04-23"
}
```

**Response fields:**
```json
{
  "keywords":     { "feature_keywords": [...], "complexity_keywords": [...],
                    "overall_complexity_score": 85, "global_multiplier": 1.30 },
  "modules":      [{ "name": "...", "complexity": "high", "days": 15, "multiplier": 1.25 }],
  "phase_timeline":  [...],
  "module_timeline": [...],
  "start_date":   "2026-04-23",
  "end_date":     "2026-08-23",
  "total_days":   123,
  "total_hours":  1280,
  "num_modules":  18,
  "labor_cost":   640000,
  "infrastructure_cost": 18450,
  "contingency":  64000,
  "total_cost":   722450,
  "hourly_rate":  500.0,
  "currency":     "INR",
  "team":         { "size": "Standard Team", "total": 9, "developers": 3, ... }
}
```

### `GET /`
Serves `static/index.html`.

---

## 6. Frontend Implementation

### Layout
Two-column layout: **dark sidebar** (220px fixed) + **main content** (flex: 1).

**CSS design tokens in `:root`:**
```css
--bg: #f0f0f0;      /* page background */
--surface: #ffffff;  /* card background */
--accent: #2c5f9e;   /* primary blue */
--border: #d8d8d8;   /* borders */
--text: #1a1a1a;     /* primary text */
```

### Key Components & Behaviour

| Component | Implementation |
|---|---|
| **Stats row** | CSS Grid — 5 equal columns, each a stat box |
| **Keywords section** | Hidden by default; **"Show Keywords"** button toggles `.hidden` class |
| **Keyword tags** | Blue pills (`tag-feature`) and purple pills (`tag-complex`) with inline level badge |
| **Complexity bar** | `width` set to `overall_complexity_score + '%'` via JS |
| **Cost grid** | CSS Grid 4 columns — Labor / Infrastructure / Contingency / Total |
| **Cost bar chart** | JS builds `<div>` rows with `width: pct%` fill using proportional values |
| **Timeline tabs** | `switchTab(tab)` shows/hides two `.timeline-view` divs |
| **Gantt rows** | CSS Grid — Name / Dates / Days / Bar; bar width = `(phase.days / maxDays) × 100%` |
| **Module table** | Standard `<table>` with complexity `<span class="badge badge-{level}">` |
| **Team grid** | Flexbox row of role cards, each showing count + title |

**NavIntersectionObserver:** Each section is observed; when 30% visible, the corresponding sidebar link gains the `.active` class.

---

## 7. Data Flow (End-to-End)

```
User pastes SRS text
        │
        ▼
[Generate Estimate clicked]
        │
        ▼
fetch POST /api/estimate  { text, hourly_rate, start_date }
        │
        ▼
FastAPI validates → estimate_project()
    ├── extract_keywords()   → feature list, complexity list, score, multiplier
    ├── extract_modules()    → modules with days
    ├── cost calculation     → labor, infra, contingency, total
    ├── build_gantt_timeline → phase + module timelines with dates
    └── recommend_team()     → team composition
        │
        ▼
JSON response → browser
        │
        ▼
JS: renderStats / renderKeywords / renderCost / renderTimeline / renderModules / renderTeam
```

---

## 8. How to Start the Project

### Prerequisites
- Python 3.9+ installed
- `pip` available
- Internet connection for first-time spaCy model download

---

### Step 1 — Navigate to the project folder

```bash
cd /path/to/srs-estimator
```

### Step 2 — Create and activate virtual environment

```bash
# Create
python3 -m venv venv

# Activate — macOS / Linux
source venv/bin/activate

# Activate — Windows
venv\Scripts\activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Download spaCy language model

> Only needed once. The app also auto-downloads on first startup.

```bash
python -m spacy download en_core_web_sm
```

### Step 5 — Run the server

```bash
python main.py
```

Or directly with uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 6 — Open in browser

```
http://localhost:8000
```

> **Tip:** `--reload` enables hot-reload on file changes. Stop with `Ctrl+C`. Deactivate venv with `deactivate`.

---

## 9. Sample Inputs & Expected Outputs

---

### Sample 1 — Simple CRUD Web App

**SRS Input:**
```
The system shall provide user authentication with login and logout functionality.
Users should be able to create, read, update, and delete their profile information.
The application must include an admin panel for managing users.
Email notifications shall be sent for account activities.
A search and filter feature should allow users to find content quickly.
```

**Expected Output (approx.):**

| Field | Value |
|---|---|
| Modules Detected | ~5–7 |
| Total Days | ~25–35 |
| Complexity Score | ~30–40 / 100 |
| Total Cost (₹500/hr) | ~₹1,00,000 – ₹1,40,000 |
| Team Recommendation | Small Team (2 people) |

**Features detected:** User Login, Admin Panel, Email Service, Search & Filter  
**Complexity terms:** Secure (medium)

---

### Sample 2 — E-Commerce Platform with Payments

**SRS Input:**
```
The platform shall support secure user registration and authentication using OAuth 2.0 and JWT.
A product catalog with search, filter, and category management shall be implemented.
Payment gateway integration with Razorpay shall handle billing, invoicing, and refunds.
Users shall receive real-time order status notifications via email and SMS.
An admin dashboard with analytics and reporting shall track sales and user activity.
Cloud storage on AWS S3 shall handle product images and documents.
A RESTful API shall be exposed for third-party integrations.
```

**Expected Output (approx.):**

| Field | Value |
|---|---|
| Modules Detected | ~10–13 |
| Total Days | ~60–80 |
| Complexity Score | ~60–70 / 100 |
| Total Cost (₹500/hr) | ~₹2,50,000 – ₹3,50,000 |
| Team Recommendation | Medium Team (5 people) |

**Features detected:** User Registration, Search & Filter, Payment Gateway, Notifications, Dashboard, Reporting, Cloud Storage, REST API  
**Complexity terms:** OAuth (medium), JWT Auth (medium), Real-Time (high), AWS (medium)

---

### Sample 3 — AI-Powered SaaS Analytics Platform

**SRS Input:**
```
The system shall provide secure user authentication using JWT tokens and OAuth 2.0 
with two-factor authentication (2FA). It shall include a real-time analytics dashboard 
for monitoring key performance metrics using WebSocket technology. The platform must 
feature an AI-based recommendation engine powered by machine learning algorithms and 
deep learning models. Payment gateway integration with Razorpay shall handle billing 
and invoicing. An admin panel with role-based access control (RBAC) and audit trail 
shall be provided. The system shall support cloud storage on AWS S3 with CDN integration.
Automated email and SMS notifications shall be sent via third-party APIs. A full-text 
search and filter system must be included. Data must be encrypted at rest and in transit 
(SSL/TLS). A RESTful API shall be exposed for third-party integrations. Automated backup 
and recovery must be included.
```

**Expected Output (approx.):**

| Field | Value |
|---|---|
| Modules Detected | ~16–20 |
| Total Days | ~110–130 |
| Complexity Score | ~95–100 / 100 |
| Total Cost (₹500/hr) | ~₹6,50,000 – ₹8,00,000 |
| Team Recommendation | Standard Team (9 people) |

**Features detected:** Authentication, Dashboard, Recommendation Engine, Payment Gateway, Admin Panel, Role Management, Access Control, Audit Trail, Cloud Storage, CDN Integration, Email Service, SMS Notifications, Search & Filter, Backup & Recovery  
**Complexity terms:** AI (high), Machine Learning (high), Deep Learning (high), Real-Time (high), WebSocket (high), OAuth (med), JWT (med), 2FA (med), Encryption (high), SSL/TLS (low), AWS (med), Payment Gateway (high), Third-Party Integration (med)

---

### Sample 4 — Blockchain-Based Supply Chain System

**SRS Input:**
```
The system shall implement blockchain technology with smart contracts for transparent 
supply chain tracking. A distributed ledger shall record all transactions and goods 
movements immutably. The platform must include real-time monitoring of shipment status 
using WebSocket connections. Geolocation and GPS tracking shall provide live location 
data for shipments. Role-based access control shall manage permissions for suppliers, 
manufacturers, and distributors. A RESTful API shall allow integration with existing 
ERP systems. Advanced analytics and reporting dashboards shall provide visibility into 
supply chain performance. The system shall be deployed on Kubernetes with Docker 
containers for high availability. Data shall be encrypted end-to-end using 
industry-standard encryption protocols. Automated email alerts and SMS notifications 
shall be triggered on key supply chain events.
```

**Expected Output (approx.):**

| Field | Value |
|---|---|
| Modules Detected | ~12–16 |
| Total Days | ~160–210 |
| Complexity Score | ~95–100 / 100 |
| Total Cost (₹500/hr) | ~₹7,00,000 – ₹10,00,000 |
| Team Recommendation | Large Team (14 people) |

**Features detected:** Role Management, REST API, Reporting, Analytics, Email Service, SMS Notifications, Monitoring, Location Services  
**Complexity terms:** Blockchain (high ×1.35), Smart Contracts (high ×1.40), Distributed (high ×1.25), Real-Time (high ×1.20), WebSocket (high ×1.15), Kubernetes (high ×1.20), Docker (med ×1.10), Encryption (high ×1.25), High Availability (high ×1.25)

---

*Document generated: 23 April 2026*  
*Project: SRS-Based Automated Project Timeline and Cost Estimator*
