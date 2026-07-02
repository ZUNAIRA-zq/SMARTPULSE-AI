"""
SmartPulse AI - Orchestrator Agent

Purpose:
    This module implements the Orchestrator Agent which coordinates the entire 
    business intelligence workflow: Ingesting Data -> Running ML -> Generating Insights -> Alerting.

Role in Agent System:
    Coordinates and drives the three specialist agents (Data Monitor, Insight Generator, Alert Agent).
    It manages the shared session state and exposes a streaming event generator so the 
    FastAPI backend can push real-time log updates to the React frontend.

Design Decisions:
    - Shared Session Context: Implements a session context class compatible with Google ADK's 
      design where agents communicate by reading and writing to `context.session.state`.
    - Event Streaming: Drives the execution of each sub-agent sequentially, yielding 
      their progressive status logs. This provides visual explanation of the agent's thought 
      processes in the dashboard.
    - Error Propagation: Checks the state after each step. If a major failure occurs 
      (e.g., input CSV missing or unreadable), it halts downstream agents.

Agent Communication Pattern:
    1. FastAPI controller calls Orchestrator.run_workflow(csv_path).
    2. Orchestrator initializes shared state and Context.
    3. Orchestrator executes DataMonitorAgent -> updates state.
    4. Orchestrator executes InsightGeneratorAgent -> updates state.
    5. Orchestrator executes AlertAgent -> updates state.
    6. Orchestrator yields final status and saves execution summary.
"""

import os
import json
import logging
from typing import AsyncGenerator, Dict, Any

# Import Google ADK agents
from google.adk.agents import BaseAgent

# Import our specialized agents
from backend.agents.data_monitor import DataMonitorAgent
from backend.agents.insight_generator import InsightGeneratorAgent
from backend.agents.alert_agent import AlertAgent

logger = logging.getLogger("Orchestrator")

class AgentSession:
    """
    Session object holding the shared state across all agents, 
    mimicking the Google ADK Session model.
    """
    def __init__(self, initial_state: Dict[str, Any]):
        self.state = initial_state

class AgentContext:
    """
    Context object passed to each agent's run implementation, 
    complying with Google ADK's Context structure.
    """
    def __init__(self, session: AgentSession):
        self.session = session

class Orchestrator:
    """
    Master Orchestrator Agent coordinates the sequential execution of specialist agents.
    """
    def __init__(self):
        # Instantiate worker agents
        self.data_monitor = DataMonitorAgent()
        self.insight_generator = InsightGeneratorAgent()
        self.alert_agent = AlertAgent()

    async def run_workflow(self, csv_path: str) -> AsyncGenerator[str, None]:
        """
        Runs the complete business intelligence pipeline sequentially, yielding log events.
        
        Args:
            csv_path (str): Path to the weekly sales CSV file.
            
        Yields:
            str: JSON strings representing log events with type and content.
        """
        yield self._format_event("orchestrator", "Orchestrator: Initializing SmartPulse AI pipeline...")

        # 1. Initialize shared state
        shared_state = {
            "csv_path": csv_path,
            "raw_data": [],
            "anomalies": [],
            "insight_report": "",
            "latest_alert": None,
            "alerts_log": []
        }
        
        # Create session context
        session = AgentSession(shared_state)
        context = AgentContext(session)
        
        # --- Step 1: Data Monitor Agent ---
        yield self._format_event("orchestrator", "Orchestrator: Triggering Data Monitor Agent...")
        try:
            async for log in self.data_monitor._run_async_impl(context):
                yield self._format_event("data_monitor", log)
        except Exception as e:
            yield self._format_event("orchestrator", f"Critical Error in Data Monitor: {str(e)}")
            return

        # Check if we successfully read data
        if not session.state.get("raw_data"):
            yield self._format_event("orchestrator", "Orchestrator: No data ingested. Aborting workflow.")
            return

        # --- Step 2: Insight Generator Agent ---
        anomalies = session.state.get("anomalies", [])
        if len(anomalies) == 0:
            yield self._format_event("orchestrator", "Orchestrator: No anomalies detected. Insight generation skipped.")
            session.state["insight_report"] = "### Weekly Sales Audit\nNo revenue or expense anomalies detected. All parameters within nominal thresholds."
        else:
            yield self._format_event("orchestrator", f"Orchestrator: Found {len(anomalies)} anomalies. Triggering Insight Generator Agent...")
            try:
                async for log in self.insight_generator._run_async_impl(context):
                    yield self._format_event("insight_generator", log)
            except Exception as e:
                yield self._format_event("orchestrator", f"Critical Error in Insight Generator: {str(e)}")
                return

        # --- Step 3: Alert Agent ---
        yield self._format_event("orchestrator", "Orchestrator: Triggering Alert Agent...")
        try:
            async for log in self.alert_agent._run_async_impl(context):
                yield self._format_event("alert_agent", log)
        except Exception as e:
            yield self._format_event("orchestrator", f"Critical Error in Alert Agent: {str(e)}")
            return

        # --- Workflow Summary ---
        summary = {
            "status": "success",
            "anomalies_count": len(session.state.get("anomalies", [])),
            "alert_status": session.state.get("latest_alert", {}).get("status", "N/A"),
            "timestamp": session.state.get("latest_alert", {}).get("timestamp", "")
        }
        
        yield self._format_event("orchestrator", "Orchestrator: Pipeline complete. Returning results.")
        yield json.dumps({
            "type": "result",
            "content": "Pipeline execution complete.",
            "data": {
                "anomalies": session.state["anomalies"],
                "insight_report": session.state["insight_report"],
                "latest_alert": session.state["latest_alert"],
                "summary": summary
            }
        })

    def _format_event(self, agent_name: str, message: str) -> str:
        """
        Helper to format progress events into standard JSON strings.
        """
        return json.dumps({
            "type": "log",
            "agent": agent_name,
            "message": message
        })
