"""
SmartPulse AI - Custom MCP Server (CSV Ingestor)

Purpose:
    This module implements a custom Model Context Protocol (MCP) server using the FastMCP framework.
    It exposes tools that allow AI agents to ingest and parse local CSV sales files securely.

Role in Agent System:
    The Data Monitor Agent acts as an MCP client. It starts this server as a subprocess 
    and communicates with it over stdio to fetch and parse the weekly sales CSV data.

Design Decisions:
    - FastMCP Framework: Utilized for its high-level, decorator-based declaration of tools.
    - JSON-RPC over stdio: The standard transport mechanism for local MCP servers.
    - Output Safeguards: Any debugging print statements are strictly directed to `sys.stderr` 
      because writing to `sys.stdout` would corrupt the JSON-RPC stream and disconnect the client.
    - Data Validation: Standardizes column naming and enforces float conversion for financial fields
      to ensure the anomaly detector receives clean inputs.

Agent Communication Pattern:
    1. Data Monitor Agent starts `csv_ingestor.py` as a subprocess.
    2. Data Monitor Agent sends a JSON-RPC request to call `read_sales_csv` tool.
    3. Custom MCP Server reads the file, parses it into JSON, and returns the response.
    4. Data Monitor Agent closes the connection and processes the parsed data.
"""

import os
import sys
import json
import logging
import pandas as pd
from fastmcp import FastMCP

# Configure logging to write to sys.stderr so it doesn't corrupt stdout JSON-RPC stream
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("CSV_Ingestor_MCP")

# Initialize FastMCP Server
mcp = FastMCP("CSV Ingestor Server")

@mcp.tool()
def read_sales_csv(file_path: str) -> str:
    """
    Reads and parses a weekly sales CSV file from disk.
    
    Args:
        file_path (str): The absolute path to the CSV file to ingest.
        
    Returns:
        str: A JSON string containing the list of parsed sales rows, 
             or an error dictionary if the read fails.
    """
    logger.info(f"Invoking read_sales_csv tool with path: {file_path}")
    
    # Check if the file exists
    if not os.path.exists(file_path):
        error_msg = f"Error: CSV file not found at {file_path}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
        
    try:
        # Read the CSV file using pandas
        # Expected columns: Date, Region, Revenue, Expenses, Profit
        df = pd.read_csv(file_path)
        logger.info(f"Successfully read CSV. Row count: {len(df)}")
        
        # Verify required columns exist
        required_cols = {"Date", "Region", "Revenue", "Expenses", "Profit"}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            error_msg = f"Error: Missing required columns in CSV: {list(missing_cols)}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})
            
        # Clean and format the data
        df["Date"] = df["Date"].astype(str).str.strip()
        df["Region"] = df["Region"].astype(str).str.strip()
        df["Revenue"] = pd.to_numeric(df["Revenue"]).astype(float)
        df["Expenses"] = pd.to_numeric(df["Expenses"]).astype(float)
        df["Profit"] = pd.to_numeric(df["Profit"]).astype(float)
        
        # Convert to dictionary records
        records = df.to_dict(orient="records")
        return json.dumps({"status": "success", "data": records})
        
    except Exception as e:
        error_msg = f"Error occurred while parsing CSV: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})

if __name__ == "__main__":
    # Start the MCP server using stdio transport
    logger.info("Starting CSV Ingestor MCP Server...")
    mcp.run()
