# SQL Performance Analyzer
### Database Performance Monitoring & Query Optimization Platform

[![CI Pipeline](https://github.com/abdulroufe28/sql-performance-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/abdulroufe28/sql-performance-analyzer/actions/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.162.0-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.14-3776AB.svg?logo=python)](https://python.org)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1.svg?logo=mysql)](https://mysql.com)
[![Tests](https://img.shields.io/badge/tests-33%20passed-success.svg)](https://docs.pytest.org)

**SQL Performance Analyzer** is a production-oriented database performance monitoring platform designed to analyze SQL execution plans, pinpoint query bottlenecks, benchmark query rewrites side-by-side, and provide evidence-based optimization recommendations.

---

## 🚀 Core Features

- **🛡️ Multi-Layer SQL Safety Engine**:
  - Whitelist-only parser restricting operations to read-only `SELECT` queries.
  - Rejects dangerous SQL patterns (`DROP`, `DELETE`, `UPDATE`, `ALTER`, `TRUNCATE`, comments injection, multi-statement chaining).
  - Controlled analysis database environment operated via restricted MySQL read-only credentials (`SELECT, SHOW VIEW`).

- **⚡ Automated Execution Measurement & Profiling**:
  - Measures execution latency (`execution_time_ms`) via high-precision monotonic timers (`time.perf_counter`).
  - Measures true row count vs rows examined without fabricating performance metrics.

- **🔍 Dual MySQL EXPLAIN Parsing**:
  - Leverages MySQL 8 `EXPLAIN` and `EXPLAIN FORMAT=JSON` to extract structured execution blocks.
  - Automatically identifies:
    - **Full Table Scans (`type: ALL`)** on unindexed tables.
    - **In-memory/Disk Filesorts (`Using filesort`)** in `ORDER BY` operations.
    - **Internal Temporary Tables (`Using temporary`)** in complex aggregations.
    - **Wildcard Column Over-fetching (`SELECT *`)**.
    - **Optimizer Misses** where suitable indexes exist but were skipped.

- **💡 Evidence-Based Recommendation Engine**:
  - Generates specific, context-aware indexing and projection recommendations directly mapped to table predicates and join conditions.
  - Computes an overall query health rating (`OPTIMIZED`, `NEEDS_OPTIMIZATION`, `CRITICAL_BOTTLENECK`).

- **⚖️ Side-by-Side Query Comparison (A/B Benchmarking)**:
  - Benchmark two query variations side-by-side with true database measurements.
  - Real-time comparison metrics: latency difference, speedup percentage, reduction in rows examined, and automated optimization verdicts.
  - Configurable free-tier usage quota enforcement (10 comparisons limit for free accounts).

- **📊 Developer Dashboard & History**:
  - Real-time performance KPI cards (total queries, average latency, full table scan rates, quota tracker).
  - Visual trend charts using Chart.js.
  - Paginated user history with strict multi-tenant data isolation.

- **🔐 Enterprise Authentication & Role-Based Authorization**:
  - Argon2 password hashing via `pwdlib`.
  - Stateless JWT token authentication with expiration handling.
  - Role-based access control (`USER` vs `ADMIN`).
  - Admin dashboard displaying platform-wide analytics, user metrics, and live database health monitoring.

---

## 🏛️ System Architecture

```text
                        +----------------------------+
                        |      Web UI / Client       |
                        +--------------+-------------+
                                       |
                                       v  HTTP (JWT Bearer)
                        +----------------------------+
                        |       FastAPI Router       |
                        +--------------+-------------+
                                       |
                   +-------------------+-------------------+
                   |                                       |
                   v                                       v
      +-------------------------+             +-------------------------+
      |  SQL Safety & Validator |             |  JWT Auth & Permissions |
      +------------+------------+             +-------------------------+
                   |
                   v
      +-------------------------+
      | Query Execution Service |
      +------------+------------+
                   |
       +-----------+-----------+
       |                       |
       v                       v
+---------------+       +---------------+
|  Application  |       |   Controlled  |
|   Database    |       |    Analysis   |
| (App, Users,  |       |    Database   |
|   History)    |       |  (Read-Only)  |
+---------------+       +---------------+
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, PyMySQL |
| **Security** | Argon2 password hashing (`pwdlib`), PyJWT, HTTPBearer |
| **Databases** | MySQL 8.0 (Dual DB Architecture: Application DB + Restricted Analysis DB) |
| **Frontend** | HTML5, Modern Responsive CSS, JavaScript (Vanilla ES6+), Chart.js |
| **Testing** | pytest, FastAPI TestClient, HTTPX |
| **CI/CD** | GitHub Actions Automated Test Pipeline with MySQL Service Container |

---

## 🔌 API Reference Summary

### Authentication
- `POST /api/v1/auth/register` — Create account with email, password, and full name.
- `POST /api/v1/auth/login` — Authenticate and receive a JWT access token.
- `GET /api/v1/auth/me` — Retrieve the currently authenticated user profile.

### Query Analysis & Performance
- `POST /api/v1/queries/analyze` — Safely execute a SELECT query, profile latency, extract EXPLAIN plans, and generate recommendations.
- `GET /api/v1/queries/history` — Retrieve paginated query analysis history for the current user.
- `POST /api/v1/queries/compare` — Compare two queries side-by-side with resource diffing and quota tracking.
- `GET /api/v1/queries/comparisons` — Retrieve saved comparison reports for the current user.

### Dashboard & Analytics
- `GET /api/v1/dashboard/metrics` — Aggregate metrics: total analyses, avg latency, scan counts, quota status, and slowest queries.
- `GET /api/v1/admin/dashboard` — Platform user stats, system latency, and live database health status (Requires `ADMIN` role).
- `GET /api/v1/health` — Public API health check endpoint.

---

## 🧪 Automated Testing

The application includes 33 comprehensive unit and integration tests covering SQL safety, execution profiling, EXPLAIN analysis, query comparison, quota limits, dashboard metrics, and admin role isolation.

Run tests using pytest:

```bash
pytest
```

---

## 💻 Local Setup & Development

### 1. Prerequisites
- Python 3.12 or newer
- MySQL Server 8.0+
- Git

### 2. Clone Repository
```bash
git clone https://github.com/abdulroufe28/sql-performance-analyzer.git
cd sql-performance-analyzer
```

### 3. Setup Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure Environment
Copy `.env.example` to `.env` and fill in your local MySQL credentials and JWT secret:
```bash
cp .env.example .env
```

### 5. Seed Analysis Database & Run Migrations
```bash
mysql -u root -p < backend/scripts/seed_analysis_db.sql
alembic upgrade head
```

### 6. Start Development Server
```bash
uvicorn backend.app.main:app --reload --port 8000
```
Visit `http://localhost:8000` to access the interactive web interface, or `http://localhost:8000/docs` for the interactive Swagger OpenAPI docs.

---

## 👤 Author

**Abdul Roufe**  
B.Tech Computer Science Engineering  
Christ College of Engineering and Technology  
GitHub: [@abdulroufe28](https://github.com/abdulroufe28)
