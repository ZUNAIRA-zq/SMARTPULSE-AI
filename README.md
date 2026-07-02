# SmartPulse AI

### **Real-Time Business Intelligence Agent for SMEs**

SmartPulse AI is a secure, real-time business intelligence agent designed specifically for Small and Medium Enterprises (SMEs). It automates the process of sales data auditing, anomaly detection, root cause analysis, and executive alerting.

---

## 📖 Problem Statement
Small business owners frequently face unexpected shifts in sales and operational expenses (e.g. sudden drop in web transactions, operational cost spikes, or supply chain bottlenecks). However, they rarely have the time or budget to employ dedicated data scientists to monitor their records daily. Valuable insights are lost in static spreadsheets, leading to delayed decisions and revenue loss.

## 💡 Solution Overview
SmartPulse AI solves this by introducing an autonomous team of specialized AI agents:
1. A business owner uploads their weekly sales CSV.
2. **Data Monitor Agent** connects to a custom CSV Ingestor Model Context Protocol (MCP) server, pulls the records, and runs a machine learning Isolation Forest model to detect anomalies.
3. **Insight Generator Agent** takes the detected anomalies, masks sensitive financial data to ensure complete privacy, calls the **Google Gemini API** to analyze likely operational root causes, and returns a plain-English report.
4. **Alert Agent** drafts a professional alert email digest and logs it to a local database, which is rendered live in the dashboard.
5. The **React Dashboard** displays the interactive visual trend chart, AI findings, and alert digests, providing an automated and explainable auditing flow.

---

## 🏗 System Architecture & Agent Communication

```
                         [ SME Sales CSV Upload ]
                                    │
                                    ▼
                           ┌─────────────────┐
                           │   FastAPI API   │
                           └────────┬────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │   Orchestrator Agent    │◀──────────────┐
                       └────────────┬────────────┘               │
                                    │                            │
                    ┌───────────────┼───────────────┐            │
                    ▼               ▼               ▼            │ Status
              ┌───────────┐   ┌───────────┐   ┌───────────┐      │ Stream
              │   Data    │   │  Insight  │   │   Alert   │      │
              │  Monitor  │   │ Generator │   │   Agent   │      │
              │   Agent   │   │   Agent   │   │           │      │
              └─────┬─────┘   └─────┬─────┘   └─────┬─────┘      │
                    │               │               │            │
                    ▼               ▼               ▼            │
                ┌───────┐      ┌─────────┐     ┌─────────┐       │
                │  CSV  │      │ Gemini  │     │  Mock   │       │
                │Ingest │      │ API (via│     │  Mode   │       │
                │  MCP  │      │ Masker) │     │alerts.  │       │
                │Server │      │         │     │  json   │       │
                └───────┘      └─────────┘     └─────────┘       │
                    │               │               │            │
                    └───────────────┴───────────────┴────────────┘
                                    │
                                    ▼
                           [ React Dashboard ]
                  (Trend Analytics · AI Findings · Alert Digests
                          · Live Agent Console)
```

### Agent Communication Protocol:
- **`Orchestrator`**: The parent controller. Instantiates the workspace session and sequentially triggers the worker agents. It yields progress status lines back to the FastAPI stream and holds the shared state object (`context.session.state`).
- **`Data Monitor Agent`**: Initiates a JSON-RPC transport client session to query the `csv_ingestor` MCP server. It runs the Isolation Forest model on the returned records and writes `raw_data` and `anomalies` lists into the shared state.
- **`Insight Generator Agent`**: Retrieves anomalies, passes them through a local data-masking utility (replacing exact figures with baseline ratios and pseudonymizing regions), sends a root-cause analysis prompt to the **Google Gemini API** (`gemini-2.5-flash`), unmasks the response text, and writes the plain-English report back to the shared state. If the API is unavailable (e.g. rate limits, missing key), the agent transparently falls back to a rule-based local analyzer so the pipeline never breaks.
- **`Alert Agent`**: Extracts the generated report, drafts a professional email digest, and logs it to a shared JSON cache (`backend/db/alerts.json`), which is rendered live in the dashboard's Alert Logs tab.

---

## 🛠 Tech Stack
- **Backend Core**: Python, FastAPI, Uvicorn, python-dotenv
- **Frontend Core**: React, Vite, Tailwind CSS, Recharts, Lucide React
- **Machine Learning**: Scikit-Learn (Isolation Forest), Pandas, NumPy
- **Orchestration**: Google Agent Development Kit (`google-adk`)
- **Language Models**: Google Gemini API (`gemini-2.5-flash`) via the official `google-genai` SDK
- **Protocol layer**: Custom Model Context Protocol (MCP) server via `FastMCP`

---

## ⚙ Setup & Installation

### Prerequisites
- Python 3.10+ installed
- Node.js 18+ and `npm` installed

### 1. Backend Setup
1. Open your terminal and navigate to the project directory.
2. Install the Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create your `.env` file by copying the example template:
   ```bash
   copy .env.example .env
   ```
4. Open `.env` and fill in your details:
   - Configure `GEMINI_API_KEY` (get one free at [aistudio.google.com](https://aistudio.google.com)) to enable Gemini-powered root-cause analysis.
   - No email credentials are required. Alerts run permanently in **Mock Mode**, writing complete email digests to `backend/db/alerts.json`, which are rendered directly in the dashboard's Alert Logs tab. This is an intentional design choice that avoids exposing personal credentials in a public repository while still fully demonstrating the alerting workflow.

### 2. Frontend Setup
1. Navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```

---

## 🚀 Running Locally

To run the application locally, you will start the Backend FastAPI server and the Frontend Vite server in two separate terminals.

### Start Backend:
From the project root:
```bash
uvicorn backend.main:app --port 8000 --reload
```
*The API will be available at `http://127.0.0.1:8000`. On startup, it will run an initial analysis on the default mock sales dataset and cache the results.*

### Start Frontend:
From the `frontend` directory:
```bash
npm run dev
```
*Open your browser and navigate to `http://localhost:5173` (or the port shown in your terminal) to see the dashboard.*

---
<img width="1920" height="916" alt="image" src="https://github.com/user-attachments/assets/4dda6790-5584-4f17-a6ef-ef2c3d2ad3df" />

## 📊 Sample Demo Walkthrough

1. **Dashboard Home**: On first boot, the dashboard automatically loads analysis metrics for `data/sample_sales.csv`.
2. **KPIs**: You will see total revenue, operating profit, flagged anomalies, and logged alerts at a glance.
3. **Analytics**: Inspect the chart under the *Trend Analytics* tab. You can filter the chart by region (North, South, East, West, Central).
   - Note the visual spikes and dips marking detected anomalies!
4. **Inspect Insights**: Click the *AI Audit Findings* tab to read the unmasked, plain-English root cause analysis generated by Gemini, including:
   - West region's revenue drop (week of March 9)
   - South region's zero sales outage (week of April 6)
   - North region's revenue spike (week of May 18)
   - Central region's expense surge (week of June 1)
5. **View Alert Digests**: Click *Alert Logs* to view the professional email digests drafted by the Alert Agent, expandable to see the full body.
6. **Upload Custom Sales**: Drag a new weekly sales CSV into the upload section. The dashboard will automatically transition to the *Agent Console* tab, showing a live hacker-style console with real-time output streamed from the Orchestrator and each worker agent as they communicate.
## 📄 CSV Data Format
SmartPulse AI expects a weekly sales CSV with the following columns:

- **`Date`** *(string)* — Week start date, ISO format (`YYYY-MM-DD`). Example: `2026-03-09`
- **`Region`** *(string)* — Sales region or branch name. Example: `North`
- **`Revenue`** *(number)* — Total revenue for that region/week, in your local currency. Example: `30048.78`
- **`Expenses`** *(number)* — Total operating expenses for that region/week. Example: `17317.45`
- **`Profit`** *(number)* — Net profit for that region/week (Revenue − Expenses). Example: `12731.33`

**Notes:**
- ⚠️ **All five columns are required.** The Isolation Forest model uses `Revenue`, `Expenses`, and `Profit` together to detect anomalies - missing any of them will cause the Data Monitor Agent to fail and skip insight generation.
- `Date` values should be consistent (weekly cadence) and sortable chronologically.
- `Region` can be any label of your choosing  the system doesn't require specific region names, it just needs consistent grouping to compute baselines per region.
- More historical weeks (ideally 3+ months) give the anomaly detector a stronger sense of "normal" baseline behavior, improving detection accuracy.
- A ready-to-use sample file with realistic embedded anomalies is included at `data/sample_sales.csv`.

---

## 🔒 Security & Design Notes
- No API keys, passwords, or secrets are ever hardcoded — all credentials load exclusively from environment variables via `python-dotenv`.
- `.env` is excluded from version control via `.gitignore`; `.env.example` documents required variables with placeholder values only.
- Financial figures are pseudonymized (region names masked, absolute values converted to relative baseline percentages) before ever being sent to an external LLM API, then unmasked only after the response is received.
- The Insight Generator Agent includes a graceful local fallback analyzer, ensuring the system remains fully functional and demonstrable even if the Gemini API is rate-limited or temporarily unavailable."# SMARTPULSE-AI" 
"# SMARTPULSE-AI"                                                       git init             
"# SMARTPULSE-AI" 
