"""
estimator.py — SRS Parsing & Estimation Engine.

Pipeline:
  1. Extract important keywords (feature, complexity, tech stack).
  2. Split SRS into feature clauses via comma/conjunction splitting.
  3. Use spaCy noun-chunk cleanup to name each feature module.
  4. Score complexity via keyword matching → effort days.
  5. Build Gantt-style timeline with calendar phases.
  6. Compute full cost breakdown (labor, infrastructure, contingency).
"""

import spacy
import re
import math
from datetime import date, timedelta
from typing import List, Dict, Any, Tuple
import subprocess
import sys

# ---------------------------------------------------------------------------
# Load spaCy model (auto-download on first run)
# ---------------------------------------------------------------------------
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading spacy model 'en_core_web_sm'...")
    subprocess.check_call(
        [sys.executable, "-m", "spacy", "download", "en_core_web_sm"]
    )
    nlp = spacy.load("en_core_web_sm")


# ---------------------------------------------------------------------------
# Keyword Dictionaries
# ---------------------------------------------------------------------------

# Feature keywords → canonical module name
FEATURE_KEYWORDS: Dict[str, str] = {
    "authentication": "Authentication",
    "login": "User Login",
    "logout": "User Login",
    "signup": "User Registration",
    "registration": "User Registration",
    "dashboard": "Dashboard",
    "analytics": "Analytics",
    "reporting": "Reporting",
    "report": "Reporting",
    "notification": "Notifications",
    "alert": "Notifications",
    "payment": "Payment Gateway",
    "billing": "Payment Gateway",
    "invoice": "Payment Gateway",
    "chat": "Chat / Messaging",
    "messaging": "Chat / Messaging",
    "search": "Search",
    "filter": "Search & Filter",
    "profile": "User Profile",
    "settings": "Settings",
    "preferences": "Settings",
    "admin": "Admin Panel",
    "api": "API Integration",
    "rest api": "REST API",
    "graphql": "GraphQL API",
    "prediction": "Prediction Engine",
    "recommendation": "Recommendation Engine",
    "monitoring": "System Monitoring",
    "logging": "Logging",
    "file upload": "File Upload",
    "upload": "File Upload",
    "export": "Data Export",
    "import": "Data Import",
    "map": "Maps Integration",
    "geolocation": "Geolocation",
    "location": "Location Services",
    "calendar": "Calendar",
    "scheduling": "Scheduling",
    "email": "Email Service",
    "sms": "SMS Notifications",
    "otp": "OTP Verification",
    "two-factor": "Two-Factor Auth",
    "2fa": "Two-Factor Auth",
    "role": "Role Management",
    "permission": "Role Management",
    "access control": "Access Control",
    "audit": "Audit Trail",
    "backup": "Backup & Recovery",
    "cache": "Caching Layer",
    "queue": "Task Queue",
    "websocket": "WebSocket / Real-time",
    "real-time": "Real-time Updates",
    "realtime": "Real-time Updates",
    "database": "Database Design",
    "storage": "Cloud Storage",
    "cdn": "CDN Integration",
}

# Complexity / tech-stack keywords → (level, multiplier, category, display_name)
COMPLEXITY_KEYWORDS: Dict[str, Tuple[str, float, str, str]] = {
    # AI / ML
    "ai":                  ("high",   1.30, "ai_ml",     "AI"),
    "ai-based":            ("high",   1.30, "ai_ml",     "AI-Based"),
    "artificial intelligence": ("high", 1.30, "ai_ml",  "Artificial Intelligence"),
    "ml":                  ("high",   1.30, "ai_ml",     "Machine Learning"),
    "machine learning":    ("high",   1.30, "ai_ml",     "Machine Learning"),
    "deep learning":       ("high",   1.40, "ai_ml",     "Deep Learning"),
    "neural network":      ("high",   1.40, "ai_ml",     "Neural Network"),
    "nlp":                 ("high",   1.35, "ai_ml",     "NLP"),
    "computer vision":     ("high",   1.40, "ai_ml",     "Computer Vision"),
    # Real-time
    "real-time":           ("high",   1.20, "realtime",  "Real-Time"),
    "realtime":            ("high",   1.20, "realtime",  "Real-Time"),
    "real time":           ("high",   1.20, "realtime",  "Real-Time"),
    "websocket":           ("high",   1.15, "realtime",  "WebSocket"),
    "live":                ("medium", 1.10, "realtime",  "Live Data"),
    # Security
    "secure":              ("medium", 1.20, "security",  "Secure"),
    "security":            ("medium", 1.20, "security",  "Security"),
    "encryption":          ("high",   1.25, "security",  "Encryption"),
    "oauth":               ("medium", 1.15, "security",  "OAuth"),
    "jwt":                 ("medium", 1.10, "security",  "JWT Auth"),
    "ssl":                 ("low",    1.05, "security",  "SSL/TLS"),
    "gdpr":                ("medium", 1.20, "security",  "GDPR Compliance"),
    # Blockchain / Distributed
    "blockchain":          ("high",   1.35, "distributed","Blockchain"),
    "smart contract":      ("high",   1.40, "distributed","Smart Contracts"),
    "distributed":         ("high",   1.25, "distributed","Distributed System"),
    "microservice":        ("high",   1.25, "distributed","Microservices"),
    "kubernetes":          ("high",   1.20, "distributed","Kubernetes"),
    "docker":              ("medium", 1.10, "distributed","Docker"),
    # Cloud / Infrastructure
    "cloud":               ("medium", 1.10, "infra",     "Cloud"),
    "aws":                 ("medium", 1.10, "infra",     "AWS"),
    "azure":               ("medium", 1.10, "infra",     "Azure"),
    "gcp":                 ("medium", 1.10, "infra",     "GCP"),
    "serverless":          ("medium", 1.15, "infra",     "Serverless"),
    "scalable":            ("medium", 1.15, "infra",     "Scalable"),
    "high availability":   ("high",   1.25, "infra",     "High Availability"),
    # Performance
    "performance":         ("medium", 1.10, "perf",      "Performance"),
    "optimization":        ("medium", 1.10, "perf",      "Optimization"),
    "caching":             ("medium", 1.10, "perf",      "Caching"),
    # API / Integration
    "api":                 ("medium", 1.10, "integration","API"),
    "rest":                ("low",    1.05, "integration","REST"),
    "graphql":             ("medium", 1.15, "integration","GraphQL"),
    "payment gateway":     ("high",   1.25, "integration","Payment Gateway"),
    "third-party":         ("medium", 1.15, "integration","Third-Party Integration"),
    "integration":         ("medium", 1.10, "integration","Integration"),
}

# Base effort per complexity tier (developer-days)
BASE_DAYS: Dict[str, int] = {"low": 3, "medium": 6, "high": 12}

# Standard project phases with weights (fraction of total effort)
STANDARD_PHASES = [
    {"name": "Requirements & Planning",    "weight": 0.10, "emoji": "📋"},
    {"name": "System Design & Architecture","weight": 0.15, "emoji": "🏗️"},
    {"name": "Backend Development",         "weight": 0.30, "emoji": "⚙️"},
    {"name": "Frontend Development",        "weight": 0.25, "emoji": "🎨"},
    {"name": "Testing & QA",               "weight": 0.12, "emoji": "🧪"},
    {"name": "Deployment & DevOps",        "weight": 0.08, "emoji": "🚀"},
]

STOP_PHRASES = {
    "the system", "system", "the user", "user", "users",
    "features", "feature", "data", "it", "they", "we",
    "software", "application", "app", "project", "module",
    "requirement", "requirements", "constraint", "constraints",
    "handling", "data handling", "secure data handling",
    "input", "output", "srs", "shall", "should", "must",
    "provide", "support", "include", "allow", "enable",
}


# ---------------------------------------------------------------------------
# Keyword Extraction
# ---------------------------------------------------------------------------

def extract_keywords(text: str) -> Dict[str, Any]:
    """
    Scan the SRS text and return:
    - feature_keywords: matched feature names
    - complexity_keywords: matched complexity/tech terms with metadata
    - overall_complexity_score: 0-100
    """
    text_lower = text.lower()

    # Feature matches
    found_features: List[str] = []
    for kw, label in FEATURE_KEYWORDS.items():
        if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
            if label not in found_features:
                found_features.append(label)

    # Complexity / tech keyword matches
    found_complexity: List[Dict[str, str]] = []
    seen_display = set()
    best_multiplier = 1.0
    complexity_level_score = 0

    level_score = {"low": 1, "medium": 2, "high": 3}

    for kw, (level, mult, category, display) in COMPLEXITY_KEYWORDS.items():
        if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
            if display not in seen_display:
                seen_display.add(display)
                found_complexity.append({
                    "keyword": display,
                    "level": level,
                    "category": category,
                    "multiplier": mult,
                })
                best_multiplier = max(best_multiplier, mult)
                complexity_level_score = max(
                    complexity_level_score, level_score.get(level, 1)
                )

    # Overall score: 0-100
    overall_score = min(100, int(
        (complexity_level_score / 3.0) * 60
        + (best_multiplier - 1.0) * 100
        + min(len(found_features) * 3, 20)
        + min(len(found_complexity) * 2, 20)
    ))

    return {
        "feature_keywords": found_features,
        "complexity_keywords": found_complexity,
        "overall_complexity_score": overall_score,
        "global_multiplier": round(best_multiplier, 2),
    }


# ---------------------------------------------------------------------------
# Module Extraction
# ---------------------------------------------------------------------------

def _split_into_clauses(text: str) -> List[str]:
    text = re.sub(r'[\n\r]+\s*[-•●▪]\s*', ', ', text)
    parts = re.split(r'[,;.]\s*|\band\b', text, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p and len(p.strip()) > 3]


def _clean_clause(clause: str) -> str:
    doc = nlp(clause)
    chunks = []
    for chunk in doc.noun_chunks:
        words = [tok.text for tok in chunk if tok.pos_ not in ("DET", "PRON")]
        cleaned = " ".join(words).strip()
        if cleaned.lower() not in STOP_PHRASES and len(cleaned) > 2:
            chunks.append(cleaned)

    if chunks:
        return max(chunks, key=len).title()

    fallback = re.sub(
        r'^(should|shall|must|will|provide|include|support|offer|have|allow|enable)\s+',
        '', clause, flags=re.IGNORECASE,
    ).strip()
    fallback = re.sub(r'^(a|an|the)\s+', '', fallback, flags=re.IGNORECASE).strip()
    if fallback.lower() not in STOP_PHRASES and len(fallback) > 3:
        return fallback.title()
    return ''


def _classify_clause(clause_lower: str) -> Tuple[str, float]:
    best_complexity = 'low'
    best_multiplier = 1.0
    level_order = {'low': 0, 'medium': 1, 'high': 2}

    for kw, (level, mult, _, _display) in COMPLEXITY_KEYWORDS.items():
        if re.search(r'\b' + re.escape(kw) + r'\b', clause_lower):
            if level_order.get(level, 0) > level_order.get(best_complexity, 0):
                best_complexity = level
            best_multiplier = max(best_multiplier, mult)

    return best_complexity, best_multiplier


def _map_to_known_feature(clause_lower: str) -> str:
    """Return canonical feature name if a feature keyword is present."""
    for kw, label in FEATURE_KEYWORDS.items():
        if re.search(r'\b' + re.escape(kw) + r'\b', clause_lower):
            return label
    return ''


def extract_modules(text: str) -> List[Dict[str, Any]]:
    clauses = _split_into_clauses(text)
    modules: List[Dict[str, Any]] = []
    seen_names: set = set()

    for clause in clauses:
        clause_lower = clause.lower()

        # Prefer known feature label
        name = _map_to_known_feature(clause_lower)
        if not name:
            name = _clean_clause(clause)
        if not name or name.lower() in STOP_PHRASES:
            continue
        if name in seen_names:
            continue
        seen_names.add(name)

        complexity, multiplier = _classify_clause(clause_lower)

        if complexity == 'low' and len(name.split()) >= 3:
            complexity = 'medium'

        base_days = BASE_DAYS[complexity]
        adjusted_days = max(1, math.ceil(base_days * multiplier))

        modules.append({
            'name': name,
            'complexity': complexity,
            'base_days': base_days,
            'multiplier': round(multiplier, 2),
            'days': adjusted_days,
        })

    # Fallback
    if not modules:
        parts = re.split(r'[,.]', text)
        for part in parts:
            part = part.strip()
            if len(part) > 5:
                modules.append({
                    'name': part.title(),
                    'complexity': 'medium',
                    'base_days': 5,
                    'multiplier': 1.0,
                    'days': 5,
                })

    return modules


# ---------------------------------------------------------------------------
# Timeline Builder
# ---------------------------------------------------------------------------

def build_gantt_timeline(
    modules: List[Dict[str, Any]],
    total_days: int,
    start_date: date,
) -> List[Dict[str, Any]]:
    """
    Generates a Gantt-style timeline with two views:
    1. Phase-based (standard SDLC phases with day ranges)
    2. Module-based (per extracted module with sequential schedule)
    """
    # --- Phase-based timeline ---
    phase_timeline = []
    cursor = 0
    for phase in STANDARD_PHASES:
        phase_days = max(1, round(total_days * phase['weight']))
        phase_timeline.append({
            'name': phase['name'],
            'emoji': phase['emoji'],
            'start_day': cursor + 1,
            'end_day': cursor + phase_days,
            'days': phase_days,
            'start_date': (start_date + timedelta(days=cursor)).isoformat(),
            'end_date': (start_date + timedelta(days=cursor + phase_days - 1)).isoformat(),
        })
        cursor += phase_days

    # --- Module-based timeline ---
    module_timeline = []
    cursor = 0
    for mod in modules:
        module_timeline.append({
            'name': mod['name'],
            'complexity': mod['complexity'],
            'start_day': cursor + 1,
            'end_day': cursor + mod['days'],
            'days': mod['days'],
            'start_date': (start_date + timedelta(days=cursor)).isoformat(),
            'end_date': (start_date + timedelta(days=cursor + mod['days'] - 1)).isoformat(),
        })
        cursor += mod['days']

    return phase_timeline, module_timeline


# ---------------------------------------------------------------------------
# Team Size Recommendation
# ---------------------------------------------------------------------------

def recommend_team(total_days: int, num_modules: int) -> Dict[str, Any]:
    """Recommend a team composition based on project size."""
    if total_days <= 30:
        return {
            'size': 'Small Team',
            'developers': 1,
            'designers': 1,
            'qa': 0,
            'devops': 0,
            'pm': 0,
            'total': 2,
            'description': 'Solo developer + designer for a small project.',
        }
    elif total_days <= 90:
        return {
            'size': 'Medium Team',
            'developers': 2,
            'designers': 1,
            'qa': 1,
            'devops': 0,
            'pm': 1,
            'total': 5,
            'description': 'Small team suited for a mid-size project.',
        }
    elif total_days <= 180:
        return {
            'size': 'Standard Team',
            'developers': 3,
            'designers': 2,
            'qa': 2,
            'devops': 1,
            'pm': 1,
            'total': 9,
            'description': 'Balanced team for a medium-to-large project.',
        }
    else:
        return {
            'size': 'Large Team',
            'developers': 5,
            'designers': 2,
            'qa': 3,
            'devops': 2,
            'pm': 2,
            'total': 14,
            'description': 'Full team required for a large-scale project.',
        }


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def estimate_project(
    text: str,
    hourly_rate: float = 500.0,
    start_date_str: str = None,
) -> Dict[str, Any]:
    """
    Full pipeline: SRS text → keywords → modules → timeline → cost.
    """
    # Parse start date
    if start_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            start_date = date.today()
    else:
        start_date = date.today()

    # Step 1: Extract keywords
    keyword_data = extract_keywords(text)

    # Step 2: Extract modules
    modules = extract_modules(text)

    # Step 3: Totals
    total_days = max(sum(m['days'] for m in modules), 1)
    hours_per_day = 8
    total_hours = total_days * hours_per_day

    # Step 4: Apply global complexity multiplier from keywords
    global_mult = keyword_data['global_multiplier']
    total_hours_adj = math.ceil(total_hours * global_mult)

    # Step 5: Cost breakdown
    labor_cost = total_hours_adj * hourly_rate
    infrastructure_cost = max(5000.0, total_days * 150)  # scale with project size
    contingency = round(labor_cost * 0.10)               # 10% contingency
    total_cost = labor_cost + infrastructure_cost + contingency

    # Step 6: Build timelines
    phase_timeline, module_timeline = build_gantt_timeline(modules, total_days, start_date)

    # Step 7: Team recommendation
    team = recommend_team(total_days, len(modules))

    return {
        # Keywords
        'keywords': keyword_data,

        # Modules
        'modules': [
            {
                'name': m['name'],
                'complexity': m['complexity'],
                'days': m['days'],
                'multiplier': m['multiplier'],
            }
            for m in modules
        ],

        # Timeline
        'phase_timeline': phase_timeline,
        'module_timeline': module_timeline,
        'start_date': start_date.isoformat(),
        'end_date': (start_date + timedelta(days=total_days - 1)).isoformat(),

        # Effort
        'total_days': total_days,
        'total_hours': total_hours_adj,
        'num_modules': len(modules),

        # Cost
        'labor_cost': round(labor_cost),
        'infrastructure_cost': round(infrastructure_cost),
        'contingency': contingency,
        'total_cost': round(total_cost),
        'hourly_rate': hourly_rate,
        'currency': 'INR',

        # Team
        'team': team,
    }
