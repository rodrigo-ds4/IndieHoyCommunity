Got it. I'll provide the complete, updated content for you to **replace** in your `README.md` file. It includes the architecture diagram, schemas, and all other sections, fully in English.

---

# IndieHOY Discount System 🎫

A simple and reliable system for requesting show discounts – deterministic, fast, and ready for production.

---

## Objective

A complete solution that allows users to request discounts for shows through:

-   A modern landing page with real-time show search
-   Email pre-validation to ensure only eligible users can request discounts
-   A human supervision dashboard for reviewing, editing, and approving requests
-   Ultra-fast, deterministic processing (less than 1 second per request)

**Current Status:** Fully functional and production-ready

---

## System Overview

### User Flow

1.  **Show Search:**
    Users search for a show in real time and select from available options.

2.  **Email Validation:**
    The system validates the user's email, subscription status, and payment status before allowing a request.

3.  **Request Processing:**
    If valid, the request is processed using deterministic business rules and added to a human supervision queue.

4.  **Human Supervision:**
    Administrators review, approve, reject, or edit requests and emails via a dedicated dashboard.

---

## System Architecture

```mermaid
graph TD
    A[User: Landing Page] --> B[Show Search<br/>GET /shows/search]
    B --> C[Show List (Real Time)]
    C --> D[User Selects Show]
    D --> E[Email Validation<br/>POST /users/validate-email]
    E --> F{Email Valid?}
    F -->|No| G[Error: Not Registered]
    F -->|Warning| H[Warning: Payment/Subscription]
    F -->|Yes| I[Request Discount<br/>POST /discounts/request]
    I --> J[PreFilter: User Validation]
    J --> K[Fuzzy Matching: Show]
    K --> L[Template Email: DB Data]
    L --> M[Supervision Queue: Human Review]
    M --> N[Dashboard: /supervision]
    N --> O{Human Decision}
    O -->|Approve| P[Email Sent: Discount Code]
    O -->|Reject| Q[Rejection Email: Reason]
    O -->|Edit| R[Custom Email: Supervisor]
    R --> S[Final Email Sent]
```

---

## Database Schemas

### USERS

| Field                | Type     | Description                 |
| -------------------- | -------- | --------------------------- |
| id                   | INT (PK) | Primary key                 |
| name                 | STRING   | Full name                   |
| email                | STRING   | Email address (unique)      |
| phone                | STRING   | Phone number                |
| subscription_active  | BOOLEAN  | Active subscription status  |
| monthly_fee_current  | BOOLEAN  | Payment status (up to date) |
| created_at           | DATETIME | Record creation             |

### SHOWS

| Field         | Type     | Description                 |
| ------------- | -------- | --------------------------- |
| id            | INT (PK) | Primary key                 |
| code          | STRING   | Internal show code (unique) |
| title         | STRING   | Show title                  |
| artist        | STRING   | Artist/performer name       |
| venue         | STRING   | Venue location              |
| show_date     | DATETIME | Show date and time          |
| max_discounts | INT      | Maximum discounts available |
| other_data    | JSON     | Additional flexible data    |
| active        | BOOLEAN  | Show active status          |

### DISCOUNT_REQUESTS

| Field          | Type     | Description                         |
| -------------- | -------- | ----------------------------------- |
| id             | INT (PK) | Primary key                         |
| user_id        | INT (FK) | Reference to users.id               |
| show_id        | INT (FK) | Reference to shows.id               |
| approved       | BOOLEAN  | System decision (True/False/None)   |
| human_approved | BOOLEAN  | Human supervisor approval           |
| other_data     | JSON     | Flexible data (reason, email, etc)  |
| request_date   | DATETIME | When request was made               |

### SUPERVISION_QUEUE

| Field            | Type     | Description                         |
| ---------------- | -------- | ----------------------------------- |
| id               | INT (PK) | Primary key                         |
| request_id       | STRING   | Unique request identifier           |
| user_email       | STRING   | User email                          |
| user_name        | STRING   | User name                           |
| show_description | STRING   | Show description                    |
| decision_type    | STRING   | approved/rejected/clarification     |
| decision_source  | STRING   | prefilter/template                  |
| email_subject    | STRING   | Email subject                       |
| email_content    | TEXT     | Email content                       |
| status           | STRING   | pending/approved/sent               |
| created_at       | DATETIME | Record creation                     |

---

## API Endpoints

-   `GET /api/v1/shows/search?q={query}` – Real-time show search
-   `POST /api/v1/users/validate-email` – Email pre-validation
-   `POST /api/v1/discounts/request` – Submit a discount request
-   `GET /api/v1/supervision/queue?status={status}` – List requests by status
-   `POST /api/v1/supervision/queue/{id}/action` – Approve/Reject
-   `POST /api/v1/supervision/queue/{id}/send` – Mark as sent
-   `GET /health` – System health check
-   `GET /docs` – API documentation

---

## Tech Stack

-   **Backend:** Python 3.11, FastAPI, SQLAlchemy, SQLite/PostgreSQL, Pydantic, FuzzyWuzzy
-   **Frontend:** HTML5, JavaScript ES6, Tailwind CSS, Fetch API
-   **DevOps:** Docker, Git, GitHub

---

## Setup

```bash
git clone <repo-url>
cd backend
docker build -t charro-backend .
docker run -d -p 8000:8000 --name charro-backend charro-backend
```

-   Landing Page: http://localhost:8000/request
-   Admin Dashboard: http://localhost:8000/supervision
-   API Docs: http://localhost:8000/docs
-   Health Check: http://localhost:8000/health

---

## Roadmap

-   **Phase 1 (Current):** Deterministic, rule-based discount system with human supervision and modern frontend.
-   **Phase 2 (Planned):** Integration of a community chatbot as a microservice for conversational discount requests.
