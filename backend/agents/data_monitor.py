"""
SmartPulse AI - Data Monitor Agent

Purpose:
    This agent ingests weekly sales CSV data, processes it via a custom MCP server,
    and runs Isolation Forest anomaly detection to identify significant financial deviations.

Role in Agent System:
    Subclasses Google ADK's `BaseAgent`. It is the first specialist worker triggered 
    by the Orchestrator. It passes the raw CSV path to the MCP server and returns 
    a structured list of anomalies.

Design Decisions:
    - MCP Client Transport: Uses the `mcp` python library to establish an async stdio 
      connection (`stdio_client`) to the `csv_ingestor.py` server process.
    - Fallback Mechanism: If the subprocess execution fails due to environment-specific 
      pathing issues, the agent falls back to parsing the CSV directly using pandas.
      This ensures production-grade reliability.
    - Anomaly Extraction: Feeds the parsed CSV records into `SMEAnomalyDetector` and 
      stores the output list in the shared session state.

Agent Communication Pattern:
    1. Orchestrator calls DataMonitorAgent.run_async() with `csv_path` in session state.
    2. DataMonitorAgent queries the `csv_ingestor` MCP server.
    3. DataMonitorAgent runs the ML model and writes the `anomalies` list and 
       `raw_data` list into `context.session.state`.
    4. DataMonitorAgent yields completion status.
"""

import os
import sys
import json
import asyncio
import pandas as pd
from typing import AsyncGenerator
from google.adk.agents import BaseAgent

# Import our ML detector
from backend.ml.anomaly_detector import SMEAnomalyDetector

class DataMonitorAgent(BaseAgent):
    """
    Data Monitor Agent: Ingests CSV files using the custom MCP Server and detects anomalies.
    """
    
    def __init__(self, name: str = "DataMonitorAgent", **kwargs):
        # Initialize Google ADK BaseAgent
        super().__init__(name=name, **kwargs)
        self._detector = SMEAnomalyDetector()

    async def _run_async_impl(self, context) -> AsyncGenerator[str, None]:
        """
        Executes the agent logic.
        Reads 'csv_path' from context.session.state, runs the ingestion and ML detection,
        and saves findings to context.session.state.
        """
        yield "Data Monitor Agent: Initializing data ingestion..."
        
        # 1. Retrieve the CSV file path from the shared session state
        session_state = context.session.state
        csv_path = session_state.get("csv_path")
        
        if not csv_path:
            yield "Error: No 'csv_path' found in session state."
            return

        if not os.path.exists(csv_path):
            yield f"Error: CSV file not found at '{csv_path}'."
            return
            
        yield f"Data Monitor Agent: Connecting to Custom CSV Ingestor MCP Server to parse '{os.path.basename(csv_path)}'..."
        
        records = None
        mcp_error = None
        
        # 2. Try to communicate with MCP Server via stdio client
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            
            # Set up the parameters to start our custom MCP server as a subprocess
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp_server", "csv_ingestor.py"))],
                env=os.environ.copy()
            )
            
            # Start the stdio subprocess connection
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    # Perform MCP protocol handshake
                    await session.initialize()
                    
                    yield "Data Monitor Agent: Ingesting CSV via MCP read_sales_csv tool..."
                    
                    # Invoke the tool on the server
                    tool_result = await session.call_tool(
                        "read_sales_csv", 
                        arguments={"file_path": os.path.abspath(csv_path)}
                    )
                    
                    # Parse the stringified JSON returned by FastMCP
                    content_text = tool_result[0].text if hasattr(tool_result, "__getitem__") else tool_result.content[0].text
                    parsed_response = json.loads(content_text)
                    
                    if "error" in parsed_response:
                        mcp_error = parsed_response["error"]
                        yield f"Data Monitor Agent: MCP tool reported an error: {mcp_error}. Trying fallback parser..."
                    else:
                        records = parsed_response.get("data")
                        yield "Data Monitor Agent: CSV successfully ingested via custom MCP server."
                        
        except Exception as e:
            mcp_error = str(e)
            yield f"Data Monitor Agent: MCP connection failed ({str(e)}). Initiating local fallback parser..."

        # 3. Fallback parser if MCP server fails (e.g. library path issues, windows sub-processes)
        if records is None:
            try:
                # Read using local pandas directly
                df_fallback = pd.read_csv(csv_path)
                records = df_fallback.to_dict(orient="records")
                yield "Data Monitor Agent: CSV successfully parsed using local fallback parser."
            except Exception as fe:
                yield f"Error: Fallback parser also failed: {str(fe)}"
                return

        # Save raw data to session state for the frontend to render the charts
        session_state["raw_data"] = records

        # Convert records back to DataFrame for the Anomaly Detector
        df = pd.DataFrame(records)
        
        yield "Data Monitor Agent: Running Isolation Forest and statistical checks to locate anomalies..."
        
        # 4. Run anomaly detection
        try:
            anomalies = self._detector.detect_anomalies(df)
            
            # Save detected anomalies to session state
            session_state["anomalies"] = anomalies
            
            anomaly_count = len(anomalies)
            yield f"Data Monitor Agent: ML detection complete. Found {anomaly_count} anomalies."
            
        except Exception as de:
            yield f"Error: Anomaly detector failed: {str(de)}"
            return
        
        yield "Data Monitor Agent: Task complete. Data and anomalies written to session state."
