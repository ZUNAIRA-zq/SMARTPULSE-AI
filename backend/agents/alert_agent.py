"""
SmartPulse AI - Alert Agent

Purpose:
    This agent takes the plain-English insight report, drafts a professional alert email 
    to the business owner, and records it in a local database (backend/db/alerts.json) 
    for visualization on the dashboard.

Role in Agent System:
    Subclasses Google ADK's `BaseAgent`. It is the third and final specialist worker 
    triggered by the Orchestrator. It depends on the report output from the Insight Generator.

Design Decisions:
    - Permanent Mock Mode Design:
      The Alert Agent runs permanently in Mock Mode to safely draft and log alert digests 
      without requiring active SMTP credentials, preventing runtime configuration errors 
      and unauthorized network requests. The FastAPI server exposes the resulting logs 
      to populate the React frontend's AlertLog component.
    - Path Isolation: Automatically creates the database directory `backend/db` if it does 
      not exist.
    - Structured Logging: Tracks and records email status (Logged (Mock Mode)) and timestamps.

Agent Communication Pattern:
    1. Orchestrator calls AlertAgent.run_async() with `insight_report` and `anomalies` list 
       in session state.
    2. AlertAgent reads configuration from environment.
    3. AlertAgent drafts the email alert.
    4. AlertAgent writes transaction details to `backend/db/alerts.json` and updates 
       `context.session.state` with alert transmission logs.
    5. AlertAgent yields completion status.
"""

import os
import json
from datetime import datetime
from typing import AsyncGenerator
from google.adk.agents import BaseAgent
from dotenv import load_dotenv

load_dotenv()

class AlertAgent(BaseAgent):
    """
    Alert Agent: Drafts mock email alerts to the business owner and logs them.
    """

    def __init__(self, name: str = "AlertAgent", **kwargs):
        super().__init__(name=name, **kwargs)
        self._db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "db"))
        self._db_path = os.path.join(self._db_dir, "alerts.json")

    async def _run_async_impl(self, context) -> AsyncGenerator[str, None]:
        """
        Executes the agent logic.
        Drafts the email, and saves a delivery log in Mock Mode.
        """
        yield "Alert Agent: Retrieving report and anomalies from state..."
        
        session_state = context.session.state
        insight_report = session_state.get("insight_report")
        anomalies = session_state.get("anomalies", [])
        
        if not insight_report:
            yield "Error: No 'insight_report' found in session state. Cannot send alert."
            return
            
        # 1. Gather configuration from environment variables
        recipient = os.getenv("ALERT_RECIPIENT_EMAIL", "owner@smartpulse.ai")
        
        yield f"Alert Agent: Drafting professional email to {recipient}..."
        
        # 2. Draft the email content
        subject = f"[SmartPulse AI Alert] {len(anomalies)} Weekly Sales Anomalies Detected"
        
        # Build anomaly bullet summary
        bullets = []
        for a in anomalies:
            bullets.append(f"- **{a['Region']}** ({a['Date']}): {a['AnomalyType']} (Revenue: ${a['Revenue']:.2f}, Expenses: ${a['Expenses']:.2f})")
        bullet_text = "\n".join(bullets)
        
        email_body = f"""Hello Team,

SmartPulse AI has completed its weekly audit on your sales data. Our machine learning pipelines detected {len(anomalies)} anomalies requiring executive attention.

### Summary of Anomalies:
{bullet_text}

---

{insight_report}

---
Best regards,
SmartPulse AI Agent
"""

        # 3. Handle email delivery in Mock Mode (Permanently enabled)
        # Mock mode is the intended, final behavior to save cost and avoid dependency on live SMTP servers.
        # No actual SMTP/Gmail sending is attempted, and credential checks are removed.
        status = "Logged (Mock Mode)"
        error_log = None
        yield "Alert Agent: Running permanently in Mock Mode. Storing draft in database log."
            
        # 4. Save the alert log to the local JSON database file
        alert_record = {
            "timestamp": datetime.now().isoformat(),
            "recipient": recipient,
            "subject": subject,
            "body": email_body,
            "status": status,
            "error": error_log
        }
        
        try:
            os.makedirs(self._db_dir, exist_ok=True)
            
            # Load existing alerts
            alerts_list = []
            if os.path.exists(self._db_path):
                try:
                    with open(self._db_path, "r") as f:
                        alerts_list = json.load(f)
                except Exception:
                    alerts_list = []
                    
            # Prepend new alert (newest first)
            alerts_list.insert(0, alert_record)
            
            # Write back
            with open(self._db_path, "w") as f:
                json.dump(alerts_list, f, indent=2)
                
            yield "Alert Agent: Alert log written to backend/db/alerts.json."
            
            # Store in session state as well
            session_state["latest_alert"] = alert_record
            session_state["alerts_log"] = alerts_list
            
        except Exception as file_err:
            yield f"Error: Failed to write alert log: {str(file_err)}"
            
        yield "Alert Agent: Task complete."
