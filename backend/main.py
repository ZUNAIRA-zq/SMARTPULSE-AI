"""
SmartPulse AI - FastAPI Web Entry Point

Purpose:
    This file acts as the FastAPI application server, exposing REST API endpoints to the
    React frontend. It provides file upload capability, triggers the multi-agent orchestrator,
    and returns analytical data for the dashboard.

Role in Agent System:
    It acts as the external gatekeeper. When a business owner uploads a sales CSV:
    1. It saves the CSV file.
    2. It instantiates the Orchestrator.
    3. It streams the step-by-step progress events back to the client using a StreamingResponse.
    4. It caches execution outcomes (raw sales records, anomalies, insights) to `backend/db/dashboard_cache.json` 
       so the dashboard can load them instantaneously on subsequent queries.

Design Decisions:
    - Streaming Response: Uses line-delimited JSON streams for `POST /api/upload` so the 
      frontend dashboard can show real-time agent execution status rather than a blank loader.
    - Initial Cache Ingestion: On startup, if no cache exists, the server automatically 
      runs the pipeline on `data/sample_sales.csv` so the UI is immediately populated with 
      our 4 embedded anomalies.
    - CORS Middleware: Enabled to permit cross-origin requests from the React dev server.

Agent Communication Pattern:
    1. UI sends sales CSV to `/api/upload`.
    2. FastAPI receives file, starts Orchestrator.run_workflow(file_path).
    3. Orchestrator yields status updates from Data Monitor, Insight Generator, and Alert agents.
    4. FastAPI relays these status events in real-time to the UI.
    5. On completion, FastAPI saves the results to local JSON cache and closes stream.
"""

import os
import json
import logging
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

# Import Orchestrator
from backend.agents.orchestrator import Orchestrator

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("SmartPulse_Backend")

app = FastAPI(title="SmartPulse AI Backend", version="1.0.0")

# Enable CORS for frontend integration
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_DIR = os.path.join(BASE_DIR, "db")
CACHE_FILE = os.path.join(DB_DIR, "dashboard_cache.json")
ALERTS_FILE = os.path.join(DB_DIR, "alerts.json")

# Ensure necessary directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)

# Shared in-memory lock to prevent concurrent pipeline runs
pipeline_lock = asyncio.Lock()

def load_cached_data() -> dict:
    """
    Helper to load cached pipeline results.
    """
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read cache file: {e}")
    return {}

def save_to_cache(data: dict):
    """
    Helper to save pipeline results to local JSON cache.
    """
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write cache file: {e}")

async def run_initial_pipeline():
    """
    Runs the pipeline on sample_sales.csv if no cache exists, 
    populating the dashboard on first startup.
    """
    if not os.path.exists(CACHE_FILE):
        logger.info("No dashboard cache found. Running initial pipeline on sample_sales.csv...")
        sample_path = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "sample_sales.csv"))
        if os.path.exists(sample_path):
            orchestrator = Orchestrator()
            raw_data = []
            anomalies = []
            insight_report = ""
            latest_alert = None
            
            # Read raw CSV to save in cache for graphing
            import pandas as pd
            try:
                df = pd.read_csv(sample_path)
                raw_data = df.to_dict(orient="records")
            except Exception as e:
                logger.error(f"Failed to parse initial raw data: {e}")

            # Run workflow generator and consume it
            async for event_str in orchestrator.run_workflow(sample_path):
                try:
                    event = json.loads(event_str)
                    if event.get("type") == "result":
                        res_data = event.get("data", {})
                        anomalies = res_data.get("anomalies", [])
                        insight_report = res_data.get("insight_report", "")
                        latest_alert = res_data.get("latest_alert", None)
                except Exception as e:
                    logger.error(f"Error parsing startup stream event: {e}")

            # Cache the initialized data
            save_to_cache({
                "raw_data": raw_data,
                "anomalies": anomalies,
                "insight_report": insight_report,
                "latest_alert": latest_alert
            })
            logger.info("Initial startup pipeline complete and cached.")
        else:
            logger.warning(f"Initial sample_sales.csv not found at: {sample_path}")

@app.on_event("startup")
async def startup_event():
    """
    Startup handler. Initializes cache.
    """
    await run_initial_pipeline()

@app.get("/api/dashboard")
async def get_dashboard_data():
    """
    Returns the latest business intelligence dashboard metrics.
    """
    cache = load_cached_data()
    if not cache:
        # Fallback if startup task hadn't completed
        return {
            "raw_data": [],
            "anomalies": [],
            "insight_report": "No reports generated yet. Please upload a CSV.",
            "latest_alert": None
        }
    return cache

@app.get("/api/alerts")
async def get_alerts_log():
    """
    Returns the complete list of alert emails drafted and sent.
    """
    if os.path.exists(ALERTS_FILE):
        try:
            with open(ALERTS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read alerts log: {str(e)}")
    return []

@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    """
    Endpoint to upload a CSV file and run the multi-agent analysis.
    Streams execution logs back to the UI in real-time.
    """
    # Enforce CSV files only
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a CSV.")
        
    if pipeline_lock.locked():
        raise HTTPException(status_code=429, detail="An analysis pipeline is already running. Please wait.")

    # Save uploaded file
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        logger.info(f"Saved uploaded sales CSV to: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    # Define streaming generator to pipe to StreamingResponse
    async def pipeline_streamer():
        async with pipeline_lock:
            orchestrator = Orchestrator()
            raw_data_records = []
            anomalies = []
            insight_report = ""
            latest_alert = None
            
            # Read raw CSV records to store in cache for graphing
            import pandas as pd
            try:
                df = pd.read_csv(file_path)
                raw_data_records = df.to_dict(orient="records")
            except Exception as e:
                logger.error(f"Error reading uploaded raw CSV: {e}")

            # Run orchestrator workflow
            async for event_str in orchestrator.run_workflow(file_path):
                # Yield log events to frontend
                yield event_str + "\n"
                
                # Check for final result to cache
                try:
                    event = json.loads(event_str)
                    if event.get("type") == "result":
                        res_data = event.get("data", {})
                        anomalies = res_data.get("anomalies", [])
                        insight_report = res_data.get("insight_report", "")
                        latest_alert = res_data.get("latest_alert", None)
                except Exception as e:
                    logger.error(f"Error reading result event: {e}")
            
            # Update cache if analysis succeeded
            if raw_data_records:
                save_to_cache({
                    "raw_data": raw_data_records,
                    "anomalies": anomalies,
                    "insight_report": insight_report,
                    "latest_alert": latest_alert
                })
                logger.info("Pipeline run complete and cached.")

    return StreamingResponse(pipeline_streamer(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    # Start the server locally
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
