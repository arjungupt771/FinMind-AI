# FinMind AI

**FinMind AI** is an AI-powered personal finance assistant that combines deterministic financial analytics with Gemini-powered financial guidance.

It provides transaction tracking, financial health analysis, anomaly detection, recurring expense intelligence, forecasting, goal planning, AI financial advice, RAG-based financial memory, scenario planning, and cross-domain financial intelligence through a React/Vite frontend and FastAPI backend.

> **Project scope:** FinMind AI is designed as a local/portfolio project. It is intended to run locally and does not require deployment infrastructure.

---

## ✨ Features

### 💳 Transaction Intelligence
- Create, update, delete, and analyze financial transactions
- User-scoped transaction data
- Spending and income categorization
- Financial summaries and trends
- Deterministic financial calculations

### ❤️ Financial Health
- Financial health score
- Spending behavior analysis
- Savings analysis
- Income/expense trends
- Financial health insights

### 🚨 Anomaly & Fraud Intelligence
- Spending spike detection
- Category outlier detection
- Robust statistical anomaly detection
- Isolation Forest-based anomaly detection
- Fraud-pattern rules
- Combined anomaly scoring
- Ranked and deduplicated transaction-level anomalies

### 🔄 Recurring Expense Intelligence
- Recurring transaction detection
- Subscription identification
- Recurring expense analysis
- Subscription-related financial insights

### 📈 Forecasting
- Expense forecasting
- Savings forecasting
- Multiple forecasting approaches:
  - Prophet
  - XGBoost
  - Exponential Smoothing
- Naive and seasonal-naive baselines
- Moving-average baseline
- Walk-forward backtesting
- Forecast model comparison
- Forecast evaluation reports

### 🎯 Goal Intelligence
- Create and track financial goals
- Goal progress analysis
- Goal-aware financial insights
- Goal context integrated into the AI advisor
- Persistent goal-related memory

### 🤖 AI Financial Advisor
- Gemini-powered financial guidance
- Spending analysis
- Savings recommendations
- Budget insights
- Investment-related analysis
- Goal planning
- Financial reviews
- Health-aware recommendations
- Conversation memory
- Context-aware follow-up questions
- Source citations

### 🧠 RAG & Financial Memory
- Persistent financial memory
- ChromaDB-backed retrieval
- Semantic memory retrieval
- User-scoped RAG queries
- Financial context retrieval
- Memory prioritization
- Memory lifecycle handling
- Conflict resolution
- Retrieval citations
- Transaction-level source references

### 🔮 Scenario & What-If Planning
- Financial scenario analysis
- What-if planning
- Goal and spending scenario evaluation
- Cross-domain financial impact analysis

### 🧩 Cross-Domain Financial Intelligence
FinMind connects different areas of a user's financial data to produce broader insights across:

- Transactions
- Financial health
- Goals
- Recurring expenses
- Forecasts
- Anomalies
- Financial memory

---

# 🏗️ Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                        React / Vite UI                       │
│                                                              │
│ Dashboard • Transactions • Goals • Forecasts • Advisor      │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                         FastAPI API                          │
│                                                              │
│ Auth • Transactions • Analytics • Goals • Advisor • RAG      │
│ Forecasting • Memory • Scenario Planning                    │
└──────────────────────────────┬───────────────────────────────┘
                               │
             ┌─────────────────┼──────────────────┐
             ▼                 ▼                  ▼
      ┌─────────────┐   ┌──────────────┐   ┌──────────────┐
      │ Deterministic│   │ AI Advisor   │   │ RAG / Memory │
      │ Intelligence │   │   Gemini      │   │ ChromaDB     │
      └─────────────┘   └──────────────┘   └──────────────┘
             │                 │                  │
             ▼                 ▼                  ▼
      Analytics / Health   Narration &       Semantic
      Forecasting /       Recommendations   Retrieval
      Anomalies / Goals
             │
             └─────────────────┬────────────────┘
                               ▼
                         SQLAlchemy DB
```

---

## 🧠 Deterministic Analytics vs. the LLM

A core design principle of FinMind AI is that **the LLM does not perform the financial calculations**.

Financial values such as:

- Spending totals
- Income
- Savings rate
- Financial health score
- Anomaly scores
- Forecast values
- Goal progress
- Recurring expense information

are calculated first by deterministic application code.

Gemini receives this already-computed financial context and is responsible primarily for:

- Explaining the results
- Connecting financial signals
- Generating recommendations
- Answering user questions
- Providing conversational guidance

This separation reduces the risk of the LLM inventing financial numbers or performing inconsistent calculations.

Both `/chat` and `/advisor/chat` build their financial context through the shared `build_financial_context()` pipeline.

---

# 📁 Project Structure

```text
FinMind AI/
│
├── src/
│   ├── components/
│   ├── pages/
│   ├── services/
│   ├── store/
│   └── ...
│
├── backend/
│   ├── analytics/
│   │   ├── health/
│   │   ├── anomaly/
│   │   └── ...
│   │
│   ├── database/
│   │   ├── models.py
│   │   ├── repositories.py
│   │   ├── config.py
│   │   └── migrations/
│   │
│   ├── forecasting/
│   │   ├── forecasting.py
│   │   ├── evaluation.py
│   │   └── report.py
│   │
│   ├── rag/
│   │   └── rag_service.py
│   │
│   ├── routers/
│   │   ├── advisor.py
│   │   ├── analytics.py
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── forecasting.py
│   │   ├── goals.py
│   │   ├── memory.py
│   │   ├── scenario.py
│   │   ├── subscriptions.py
│   │   └── transactions.py
│   │
│   ├── services/
│   │   ├── financial_advisor.py
│   │   ├── financial_memory.py
│   │   ├── goal_intelligence.py
│   │   ├── advisor_intelligence.py
│   │   ├── decision_intelligence.py
│   │   ├── recurring_expense_intelligence.py
│   │   ├── gemini_service.py
│   │   └── ...
│   │
│   ├── tests/
│   ├── auth.py
│   ├── dependencies.py
│   └── main.py
│
├── alembic.ini
├── .env.example
├── package.json
└── README.md
```

---

# 🛠️ Tech Stack

## Frontend

- React
- Vite
- JavaScript
- Zustand
- Modern CSS/UI components
- Data visualization

## Backend

- Python
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- SQLite
- PostgreSQL support

## AI / ML

- Google Gemini
- ChromaDB
- Sentence Transformers
- PyTorch
- scikit-learn
- Prophet
- XGBoost
- Statistical forecasting methods

## Testing

- pytest
- In-memory SQLite test database
- Mocked Gemini calls

---

# ⚙️ Prerequisites

- **Node.js 18+**
- **Python 3.10+**

---

# 🚀 Local Setup

## 1. Clone the repository

```bash
git clone <your-repository-url>
cd FinMind-AI
```

---

## 2. Frontend

```bash
npm install
npm run dev
```

The Vite development server will start the frontend locally.

---

## 3. Backend

Create and activate a virtual environment:

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Create the environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Add your Gemini API key:

```env
GEMINI_API_KEY=your_api_key_here
```

Start the backend:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

---

# 🗄️ Database

FinMind AI uses SQLAlchemy for database access.

By default, the application can use a local SQLite database:

```env
DATABASE_URL=sqlite:///./finmind.db
```

This allows the project to run locally without requiring an external database service.

PostgreSQL can also be configured through `DATABASE_URL` if desired.

---

# 🔄 Database Migrations

For a fresh database:

```bash
alembic upgrade head
```

After modifying SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe schema change"
```

Review the generated migration before applying it:

```bash
alembic upgrade head
```

---

# 🧪 Running Tests

Run the complete test suite:

```bash
pytest
```

The test suite uses an in-memory SQLite database through dependency overrides.

Gemini calls are mocked during testing, so the tests do not require:

- A real Gemini API key
- Your local `finmind.db`
- A live Gemini API
- A live ChromaDB installation

---

# 🔐 Authentication

FinMind AI supports JWT-based authentication.

### Register

```text
POST /auth/register
```

### Login

```text
POST /auth/login
```

Authenticated requests use:

```text
Authorization: Bearer <token>
```

For development and testing, the application also supports the configured demo user fallback.

Passwords must meet the application's configured minimum requirements, and JWT secrets should be provided through environment variables.

> Never commit real API keys, JWT secrets, database credentials, or other secrets to the repository.

---

# 🔌 API Overview

## Health

```text
GET /health
```

Returns service/configuration status.

---

## Transactions

```text
GET    /transactions
POST   /transactions
PUT    /transactions/{id}
DELETE /transactions/{id}
```

Transaction CRUD is scoped to the authenticated user.

---

## AI Chat

```text
POST /chat
```

Provides Gemini-powered financial analysis for areas such as:

- Spending
- Savings
- Investment
- Goals
- Budget
- Financial review
- Financial health

Structured Gemini responses are used where supported, with a fallback path for SDK/model combinations that do not support structured response schemas.

---

## AI Advisor

```text
POST /advisor/chat
```

Provides context-aware financial advice using:

- Transactions
- Financial health
- Forecasts
- Anomalies
- Goals
- Recurring expenses
- RAG memory
- Conversation history

The endpoint supports conversation continuation through `conversation_id`.

Responses can include:

- Financial summary
- Insights
- Recommendations
- RAG sources
- Conversation ID

---

## Anomaly Detection

```text
GET /analytics/anomalies
```

Returns ranked and deduplicated transaction-level anomaly information using multiple detection approaches.

---

## Forecast Evaluation

```text
GET /analytics/forecast-evaluation?metric_type=expense&horizon=7
```

Runs walk-forward forecast evaluation against multiple models and baseline approaches.

---

## Financial Report

```text
GET /analytics/report
```

Returns combined forecasting and anomaly analysis for the user's financial data.

---

# 🧠 RAG & Memory Design

FinMind's memory system uses ChromaDB and semantic retrieval to provide relevant historical financial context.

Memory retrieval is always scoped by `user_id`.

The advisor can retrieve relevant historical information such as:

- Previous financial goals
- Important financial decisions
- Relevant spending patterns
- Historical advisor context
- Persistent user-specific financial information

Retrieved information is accompanied by source information so that advisor responses can be traced back to underlying financial data.

The memory system also handles:

- Duplicate memories
- Memory importance
- Retrieval ranking
- Conflicting memories
- Superseded information
- Memory lifecycle

---

# 📊 Forecasting & Evaluation

FinMind does not rely on a single forecasting model.

Forecasting can evaluate multiple approaches, including:

- Prophet
- XGBoost
- Exponential Smoothing
- Naive baseline
- Seasonal-naive baseline
- Moving-average baseline

The evaluation pipeline uses walk-forward validation rather than evaluating only on the training data.

Monthly granularity is used as the recommended headline evaluation metric for personal-finance forecasting, while daily granularity remains available for more detailed diagnostics.

---

# 🚨 Anomaly Detection

FinMind combines several signals rather than relying on one anomaly detector.

These include:

- Percentile-based detection
- Robust statistical scoring
- Absolute deviation
- Isolation Forest
- Spending-pattern rules

The system combines these signals into a transaction-level anomaly score.

For high-severity anomalies, the system considers both statistical extremeness and meaningful absolute deviation.

When a user's spending is highly uniform, the system can surface a `dataset_variability` indicator to communicate that percentile-based anomaly detection may have limited usefulness for that dataset.

---

# 🎯 Goal Intelligence

Goals are not treated as isolated CRUD records.

FinMind analyzes goals alongside transaction history to understand:

- Current progress
- Spending behavior
- Savings capacity
- Forecasted financial trends
- Potential goal risks
- Relevant financial actions

Goal context can also be persisted into financial memory and used by the AI advisor in later conversations.

---

# 🔮 Scenario Planning

The scenario engine allows financial decisions to be evaluated through what-if analysis.

Examples include:

```text
What happens if monthly spending increases?

What happens if I increase my monthly savings?

How does a change in spending affect a financial goal?

How could a recurring expense affect future savings?
```

Scenario analysis connects multiple financial domains rather than treating each metric independently.

---

# 🛡️ Financial Data Safety

FinMind follows a deterministic-first architecture for financial calculations.

The application separates:

```text
Financial Data
      ↓
Deterministic Analytics
      ↓
Financial Context
      ↓
Gemini
      ↓
Explanation / Recommendations
```

The LLM is therefore not responsible for calculating the underlying financial metrics.

---

# ⚠️ Limitations

FinMind AI is a **personal finance portfolio project** and should not be treated as professional financial advice.

AI-generated recommendations can be incomplete or incorrect and should be independently evaluated before making real financial decisions.

Forecasting results depend heavily on the amount and quality of historical transaction data.

Anomaly detection also becomes less meaningful when a dataset contains very little variation or very few transactions.

The project is primarily designed for local experimentation, learning, and portfolio demonstration.

---

# 📦 Dependencies

The RAG subsystem uses Sentence Transformers for embeddings.

This dependency pulls in PyTorch and is one of the larger dependencies in the project, so the initial backend installation may take several minutes and require several hundred MB of disk space.

---

# 🧪 Testing Philosophy

The project emphasizes testing the financial intelligence independently from external AI services.

Tests cover areas including:

- Authentication
- Transactions
- Financial analytics
- Financial health
- Anomaly detection
- Recurring expenses
- Forecasting
- Forecast evaluation
- Goals
- Goal intelligence
- AI advisor behavior
- Conversation memory
- Financial memory
- RAG retrieval
- Scenario planning
- Database migrations

Gemini-dependent functionality is mocked during tests where appropriate.

---

# 🗺️ Project Development

FinMind AI was developed progressively around several major layers:

```text
Foundation
    ↓
Transaction Intelligence
    ↓
Financial Health
    ↓
Anomaly Intelligence
    ↓
Recurring Expense Intelligence
    ↓
Forecasting
    ↓
Goal Intelligence
    ↓
AI Financial Advisor
    ↓
RAG & Persistent Memory
    ↓
Cross-Domain Intelligence
    ↓
Scenario Planning
    ↓
Advanced Forecasting
    ↓
Dashboard & Advisor Refinement
    ↓
Final Codebase Polish
```

The project has now reached a feature-complete portfolio stage, with the focus shifting from adding major architectural components toward refinement, usability, and maintainability.

---


# 👨‍💻 Project

**FinMind AI** is a personal finance intelligence project built to explore the combination of:

- Full-stack development
- Financial analytics
- Machine learning
- Forecasting
- RAG
- Persistent memory
- LLM-powered reasoning
- Conversational AI
- Scenario analysis
- Data-driven decision support

The project focuses on making financial data **understandable, explainable, and actionable** while keeping the underlying financial calculations deterministic.

---#   F i n M i n d - A I  
 