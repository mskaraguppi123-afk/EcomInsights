# EcomInsights — Project Report & Comprehensive Viva Defense Guide

**Project Title:** EcomInsights: Intelligent E-Commerce Price Tracking & Trend Forecasting Engine  
**Architecture:** React (Vite) + FastAPI (Python 3.13) + SQLAlchemy (SQLite/PostgreSQL) + Explainable Time-Series ML  
**Academic Target:** College Major Project / Capstone Project Viva Defense  

---

## 1. Executive Project Summary

### 1.1 Problem Statement
Modern e-commerce platforms utilize dynamic pricing algorithms, flash sales, and algorithmic price fluctuations. Consumers frequently struggle to determine whether a "discounted" price is genuinely a bargain or an artificial inflation followed by a mark-down. 

### 1.2 Proposed Solution
**EcomInsights** is an end-to-end full-stack web application and analytical pipeline designed to:
1. Ingest multi-timestamp price observations for products across distinct categories.
2. Persist historical price trajectories with strict relational integrity.
3. Compute explainable time-series forecasts using an ensemble of Exponential Moving Average (EMA) and Ordinary Least Squares (OLS) Linear Regression.
4. Render real-time interactive price trajectory visualisations and actionable buying recommendations (`BUY_NOW`, `WAIT`, `NEUTRAL`).
5. Provide a zero-dependency sandbox testing suite for examiners to simulate price variations and observe real-time algorithmic reactions.

---

## 2. System Architecture & Component Interaction

```text
┌────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER                            │
│                                                                        │
│   React 18 + Vite (Tailwind / Custom Modern UI)                       │
│   • Product Catalog & Category Filters                                │
│   • Native Pure-SVG Historical & Forecast Price Trajectory Chart       │
│   • Dynamic Recommendation Card with AI Explanations                  │
│   • Live "Record Test Price" Observation Form                         │
└─────────────────────────────────▲──────────────────────────────────────┘
                                  │ JSON via HTTP / REST
                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION LAYER                             │
│                                                                        │
│   FastAPI (Asynchronous Python REST API)                               │
│   • CORS Middleware enabled for local development                      │
│   • Pydantic V2 Schemas for request/response validation                │
│   • Modular Router: Products, Insights, Observations, Seeding          │
│   • Embedded SSR Dashboard fallback (app/web.py)                       │
└───────────────────▲───────────────────────────────▲────────────────────┘
                    │                               │
                    ▼                               ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│            DATA PERSISTENCE          │  │       ANALYTICS & ML         │
│                                      │  │                              │
│  SQLAlchemy 2.0 ORM                  │  │  ecominsights_ml Package     │
│  • Dialect: SQLite (dev) / PG (prod) │  │  • Exponential Moving Avg    │
│  • Product Table (1-to-many)         │  │  • OLS Linear Regression     │
│  • PriceObservation Table            │  │  • Range Spread Ratio        │
│  • Decimal / Numeric Precision       │  │  • Decision Recommendation   │
└──────────────────────────────────────┘  └──────────────────────────────┘
```

---

## 3. Database Schema & Relational Design

The database employs a clean 3NF (Third Normal Form) relational design with two core entities:

### 3.1 Entity Details

#### Entity 1: `products`
| Column | Type | Constraints / Attributes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | Primary Key, Autoincrement | Unique product identifier |
| `sku` | `VARCHAR(64)` | Unique, Indexed, Not Null | Stock Keeping Unit / Barcode |
| `title` | `VARCHAR(255)` | Not Null | Product display title |
| `category` | `VARCHAR(64)` | Indexed, Not Null | Product taxonomy (e.g. Electronics) |
| `currency` | `VARCHAR(3)` | Default `'INR'`, Not Null | ISO-4217 Currency Code |
| `created_at` | `DATETIME` | Default `utcnow()` | Timestamp of record creation |
| `updated_at` | `DATETIME` | Default `utcnow()` | Timestamp of last modification |

#### Entity 2: `price_observations`
| Column | Type | Constraints / Attributes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | Primary Key, Autoincrement | Unique observation identifier |
| `product_id` | `INTEGER` | Foreign Key (`products.id`), Indexed | Relational parent link |
| `recorded_at` | `DATETIME` | Indexed, Not Null | Timestamp of recorded price |
| `price` | `NUMERIC(10, 2)` | Not Null | Recorded price in currency units |
| `source` | `VARCHAR(32)` | Default `'manual'` | Data provenance indicator |
| `scraped_at` | `DATETIME` | Nullable | Optional external crawl timestamp |

### 3.2 Relational Integrity & Decimal Precision
* **Foreign Key Relationship:** `price_observations.product_id` enforces referential integrity. Deleting a product automatically cascades or restricts dependent prices.
* **Financial Data Types:** Currency is stored as `NUMERIC(10, 2)` (SQLAlchemy `Numeric` mapped to Python `Decimal`), completely eliminating binary floating-point representation anomalies (e.g., `0.1 + 0.2 = 0.30000000000000004`).

---

## 4. Machine Learning & Forecasting Methodology

Rather than deploying an opaque, unexplainable deep neural network on sparse time-series points, EcomInsights deploys an **explainable hybrid ensemble model**.

### 4.1 Step 1: Exponential Moving Average (EMA)
Weights recent price observations higher than older observations to capture immediate volatility:

$$\alpha = 0.5$$

$$S_1 = Y_1$$

$$S_t = \alpha \cdot Y_t + (1 - \alpha) \cdot S_{t-1} \quad \text{for } t \ge 2$$

Where $Y_t$ represents the price at sequence step $t$, and $S_t$ is the smoothed estimate.

### 4.2 Step 2: Ordinary Least Squares (OLS) Linear Trend Regression
Captures the overarching macroscopic price momentum and slope over normalized time steps $x \in \{0, 1, \dots, n-1\}$:

$$\bar{x} = \frac{1}{n}\sum_{i=0}^{n-1} x_i, \quad \bar{y} = \frac{1}{n}\sum_{i=0}^{n-1} y_i$$

$$\text{Slope } m = \frac{\sum_{i=0}^{n-1} (x_i - \bar{x})(y_i - \bar{y})}{\sum_{i=0}^{n-1} (x_i - \bar{x})^2}$$

$$\text{Intercept } c = \bar{y} - m \cdot \bar{x}$$

$$\text{Projected Next Price } P_{\text{OLS}} = m \cdot n + c$$

### 4.3 Step 3: Ensemble Forecasting Synthesis
The projected next price $\hat{P}_{\text{next}}$ balances responsive momentum with structural trend:

$$\hat{P}_{\text{next}} = 0.60 \cdot S_n + 0.40 \cdot P_{\text{OLS}}$$

### 4.4 Step 4: Range-Spread Decision Tree (Buying Recommendation)
To determine whether a user should buy now or wait, the model evaluates both price momentum and relative price position:

1. **Relative Spread Ratio ($R$):**
   $$R = \frac{P_{\text{current}} - P_{\min}}{P_{\max} - P_{\min}}$$
   - If $R \le 0.25$: The product is in its bottom 25th percentile (near all-time low).
   - If $R \ge 0.75$: The product is near its peak historical price.

2. **Decision Matrix:**
   - **`BUY_NOW`**: Triggered if $P_{\text{current}} \le 1.05 \cdot P_{\min}$ OR ($R < 0.35$ and projected delta $\Delta P \ge 0$).
   - **`WAIT`**: Triggered if $P_{\text{current}} \ge 0.95 \cdot P_{\max}$ OR ($R > 0.65$ and downward trend $m < 0$).
   - **`NEUTRAL`**: Triggered when the current price hovers near historical median with low volatility.

---

## 5. Justification: Synthetic Data vs. Web Scraping

Examiners frequently ask: *"Why does your project use synthetic CSV data instead of scraping Amazon or Flipkart live?"*

### Clear Academic Justification:
1. **Legal & Terms of Service (ToS) Compliance:** 
   Commercial e-commerce platforms explicitly prohibit automated scraping in their `robots.txt` and Terms of Service (e.g. Amazon Conditions of Use §13). Building academic prototypes dependent on scraping violates ethical scraping guidelines.
2. **Technical Anti-Bot Defenses:**
   Major sites employ Cloudflare, Akamai Bot Manager, CAPTCHA challenges, and dynamic DOM obfuscation. These cause unpredictable runtime failures during viva demonstrations.
3. **Reproducibility & Scientific Rigor:**
   Using controlled benchmark datasets (`sample_prices.csv`) ensures deterministic evaluation, reliable unit testing, and instant demonstration capability without internet reliance.
4. **Production Extensibility:**
   The backend routes are designed with standard REST contracts (`POST /api/v1/products/{id}/observations`). In enterprise deployment, the ingestion endpoint connects to official affiliate APIs (Amazon Product Advertising API, Flipkart Affiliate API) with zero modifications to the database or ML layers.
5. **Hybrid Live Pricing Engine (SerpApi Google Shopping):**
   When `SERPAPI_API_KEY` is configured in `.env`, the system automatically queries live Google Shopping to fetch real-time market prices across active Indian retailers (Amazon, Flipkart, Reliance Digital, Croma). If offline or if quota expires, it gracefully falls back to local adapter simulation without crashing the application.


---

## 6. Top 15 Viva Questions & Model Answers

### Q1: Why did you choose FastAPI over Flask or Django?
> **Answer:** "FastAPI offers high performance comparable to Node.js and Go because it is built on Starlette and Pydantic with native ASGI async/await support. Unlike Flask, FastAPI provides automatic request validation and auto-generated interactive OpenAPI/Swagger documentation (`/docs`). Django is monolithic and carries heavy overhead that is unnecessary for a focused RESTful microservice."

### Q2: How does the application handle SQLite versus PostgreSQL?
> **Answer:** "We decoupled the database configuration in `app/core/config.py` and `app/db/session.py`. The system reads `DATABASE_URL` from `.env`. If PostgreSQL is configured, it connects to PostgreSQL; if not, it automatically falls back to an embedded SQLite database (`sqlite:///./ecominsights.db`) with `check_same_thread=False`. This enables zero-dependency offline demonstration while remaining enterprise-ready for PostgreSQL."

### Q3: Why is financial data stored as Decimal/Numeric instead of Float?
> **Answer:** "Binary floating-point arithmetic (IEEE 754) cannot accurately represent base-10 fractions like `0.1` or `0.2`, which can accumulate rounding errors in financial transactions. SQLAlchemy `Numeric(10, 2)` maps directly to Python's `decimal.Decimal`, ensuring exact 2-decimal-place precision without precision loss."

### Q4: Explain your ML model. Why not use LSTM or Recurrent Neural Networks?
> **Answer:** "Deep learning architectures like LSTM or Transformer networks require tens of thousands of continuous data points to avoid severe overfitting. In real-world retail tracking, individual products often have sparse historical checkpoints (e.g. 5 to 50 observations). An ensemble of Exponential Moving Average (EMA, $\alpha=0.5$) and Ordinary Least Squares (OLS) Linear Regression is mathematically sound, avoids overfitting, executes in sub-millisecond time, and provides transparent, human-explainable reasoning to the user."

### Q5: What happens if a product only has 1 price record?
> **Answer:** "Our ML pipeline incorporates fallback boundary handling: if $n < 2$, the pipeline returns a `NEUTRAL` recommendation with a baseline confidence of 0.50, identifying the current price as the single known baseline. Once at least 2 checkpoints exist, linear regression and EMA activate dynamically."

### Q6: What is CORS and why is it configured in the backend?
> **Answer:** "Cross-Origin Resource Sharing (CORS) is a browser security mechanism that blocks web pages from making AJAX/Fetch requests to a different domain, port, or protocol. Because our React frontend runs on `http://localhost:5173` and the FastAPI backend runs on `http://127.0.0.1:8000`, we configured FastAPI's `CORSMiddleware` with `allow_origins=["*"]` to authorize frontend API calls."

### Q7: How does your price chart work without third-party charting packages?
> **Answer:** "To keep the frontend bundle lightweight and eliminate heavy external dependencies (such as Chart.js or D3), we implemented a pure SVG (Scalable Vector Graphics) component in `App.jsx`. It maps historical timestamps and prices to mathematical 2D coordinate spaces using SVG `<path>` for the trendline and historical `<circle>` markers, plus a dashed forecast vector projecting to the predicted price."

### Q8: What is Pydantic and what role does it play in this project?
> **Answer:** "Pydantic is a data validation and parsing library powered by Python type hints. In `app/schemas/product.py`, Pydantic models define the exact schemas for incoming observation payloads (`PriceObservationCreate`) and outgoing responses (`ProductDetail`, `PriceInsight`). It automatically validates data types, serializes database models to JSON, and rejects invalid inputs with HTTP 422 Unprocessable Entity."

### Q9: What is the time and space complexity of the analytical pipeline?
> **Answer:** "The time complexity is $O(n)$ where $n$ is the number of price observations for a given product, because calculating the mean, OLS slope, and EMA requires a single linear pass over the price array. Space complexity is $O(n)$ to store intermediate arrays in memory. Since product observation history is typically under 1,000 checkpoints, execution latency is under 2 milliseconds."

### Q10: What is the difference between Checking & Comparing a price versus Recording a price observation?
> **Answer:** "Checking & Comparing (`GET /api/v1/products/{id}/compare?price=...`) is a safe deal simulator that compares any candidate price against historical low, average, and high values to provide an instant verdict (e.g., 'Steal Deal', 'Above Average') and buying advice *without mutating the database or corrupting the historical timeline*. In contrast, Recording an observation (`POST /api/v1/products/{id}/observations`) is an explicit write operation that permanently appends a new checkpoint to the database only when deliberately saved by the user."

### Q11: How do you prevent SQL Injection in this project?
> **Answer:** "All database interactions are handled through SQLAlchemy ORM and parameterized queries (`db.query(Product).filter(...)`). User inputs are never concatenated directly into raw SQL strings, neutralizing SQL injection vectors."

### Q12: How are unit tests implemented in the codebase?
> **Answer:** "We use `pytest` with FastAPI's `TestClient` (based on HTTPX) in `backend/tests/test_api.py`. The suite validates 9 distinct endpoints and operations: health check status, product listing, single product retrieval, price insight calculations, 404 error handling for non-existent IDs, database seeding, real-time deal comparison without data mutation, database reset, and permanent checkpoint ingestion."


### Q13: What is the role of Virtual Environments (`.venv`)?
> **Answer:** "A virtual environment isolates project-specific dependencies and library versions from the global Python installation. This prevents dependency conflicts and ensures consistent execution across different host machines."

### Q14: How does the recommendation logic determine confidence score?
> **Answer:** "The confidence score is computed dynamically based on sample size and trend consistency. It starts at a base level of $0.60$ and scales with $\min(0.95, 0.60 + 0.05 \cdot n)$, adjusting for standard deviation stability. A higher number of recorded observations increases confidence in the trendline."

### Q15: How did you implement real-time price comparison across multiple e-commerce websites?
> **Answer:** "We implemented the Software Engineering **Adapter Pattern** via an abstract `BaseStoreAdapter` interface. Concrete adapters (`AmazonAdapter`, `FlipkartAdapter`, `CromaAdapter`, and `RelianceDigitalAdapter`) normalize store quotes with prices, stock status, delivery times, and ratings. The `CrossStoreArbitrageEngine` evaluates all registered retailer adapters concurrently, identifies the cheapest store, computes potential savings, and recommends the best retailer to purchase from. This modular architecture allows scaling to 20+ retailers without modifying core business or database logic."

### Q16: How does the Link-Based Search feature work?
> **Answer:** "The Link-Based Search engine (`app/services/link_search.py`) parses URLs from major Indian e-commerce platforms (Amazon India, Flipkart, Croma, Reliance Digital) using URL slug and canonical path regex parsing to extract the product title and merchant identity. It then performs real-time multi-retailer price queries using Google Shopping API via SerpApi, with automatic fallback to local multi-store adapter simulation if offline. Furthermore, successful searches **automatically persist into the database catalog** (`db_updated: true`), dynamically creating new product entities or appending new timestamped checkpoints if the product already exists."

---


## 7. Step-by-Step Viva Demonstration Script

Follow this exact sequence during your project demonstration:

### Step 1: Open Terminal 1 (Start Backend)
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```
*Show the examiner:*
- Open `http://127.0.0.1:8000/docs` to show the Swagger/OpenAPI interactive documentation.
- Highlight the automatic schemas and endpoints (`GET /api/v1/search/universal`, `POST /api/v1/products/quick-add`, `GET /api/v1/products`).

### Step 2: Open Terminal 2 (Start React Frontend)
```powershell
cd frontend
$env:PATH = "C:\Program Files\nodejs;" + $env:PATH
npm run dev
```
*Show the examiner:*
- Open `http://localhost:5173` (or the unified embedded dashboard at `http://127.0.0.1:8000/`).
- Point out the active products (Wireless Mouse, Steel Water Bottle, Sony Headphones).
- Click on **Sony Headphones** to display its ₹14,990 baseline, its historical trajectory, and its recommendation card.

### Step 3: Link-Based & Multi-Store Search Demo (The "Wow" Factor)
1. In the **🔗 Link-Based & Universal Search** card at the top of the dashboard:
   - Paste an Amazon India link, e.g.:
     `https://www.amazon.in/Sony-WH-1000XM4-Cancelling-Headphones-Bluetooth/dp/B0863TXGM3`
   - Or enter a product name: `iPhone 15`.
2. Click **🔍 Compare Across Stores**.
3. Point out to the examiner:
   - The engine automatically parsed the URL, extracted the exact product title, and detected the platform (`Amazon India Detected`).
   - It queries live Google Shopping / multi-store adapters and returns cards showing prices from Amazon, Flipkart, Croma, Reliance Digital, etc.
   - It highlights the **Lowest Price** badge and calculates exact savings compared to other stores.
   - Clicking **➕ Track in Catalog** immediately adds this searched product to your database catalog!

### Step 4: Interactive Price Checkpoint Simulation
1. Select any product from the catalogue.
2. In the **Record Price Observation** card, enter a test discount price: e.g. `12499.00`.
3. Click **Save Observation**.
4. Show that the backend recorded the data into SQLite and updated the recommendation and trajectory in real time.

---
*Document prepared for academic submission and examination defense.*

