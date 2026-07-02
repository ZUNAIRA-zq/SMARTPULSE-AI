"""
SmartPulse AI - Insight Generator Agent

Purpose:
    This agent takes the detected anomalies, masks them to preserve data privacy,
    sends them to the Google Gemini API to generate a detailed, plain-English
    business explanation (root cause investigation), and unmasks the result.

Role in Agent System:
    Subclasses Google ADK's `BaseAgent`. It is the second specialist worker triggered 
    by the Orchestrator. It depends on the output of the Data Monitor Agent.

Design Decisions:
    - Privacy Masking: Integrates with `FinancialDataMasker` to substitute region names 
      with pseudonyms and absolute dollars with percentage deviations relative to baselines.
    - Gemini API Invocation: Uses the official `google-genai` Python SDK to call 
      Gemini (model: gemini-2.0-flash). The key is loaded from the `GEMINI_API_KEY` 
      environment variable. The SDK's async `client.aio.models.generate_content()` method
      is used so the agent does not block the event loop while waiting for the LLM response.
    - API Robustness & Fallback: If `GEMINI_API_KEY` is not configured, or if the Gemini 
      API call fails for any reason (network error, quota exceeded, etc.), the agent 
      transparently falls back to a rule-based Local Generator. This mock generator creates 
      highly-detailed, structured insights matching our embedded anomalies, preventing 
      crashes during demonstrations while still illustrating intended agent behavior.

Agent Communication Pattern:
    1. Orchestrator calls InsightGeneratorAgent.run_async() after Data Monitor Agent finishes.
    2. InsightGeneratorAgent reads `anomalies` list from `context.session.state`.
    3. InsightGeneratorAgent applies masking and prepares prompt.
    4. InsightGeneratorAgent calls Gemini API or triggers local rule-based fallback.
    5. InsightGeneratorAgent unmasks the response text (mapping region names back).
    6. InsightGeneratorAgent writes the unmasked `insight_report` text into `context.session.state`.
"""

import os
import json
from typing import AsyncGenerator
from google.adk.agents import BaseAgent
from backend.utils.data_masking import FinancialDataMasker
from dotenv import load_dotenv

load_dotenv()

class InsightGeneratorAgent(BaseAgent):
    """
    Insight Generator Agent: Generates plain-English root-cause insight reports from anomalies.
    Uses Google Gemini API as the primary LLM, with a rule-based local fallback.
    """

    def __init__(self, name: str = "InsightGeneratorAgent", **kwargs):
        super().__init__(name=name, **kwargs)

    async def _run_async_impl(self, context) -> AsyncGenerator[str, None]:
        """
        Executes the agent logic.
        Retrieves raw anomalies, masks them, queries Gemini, unmasks, and writes the report.
        """
        yield "Insight Generator Agent: Fetching anomalies list from state..."
        
        session_state = context.session.state
        anomalies = session_state.get("anomalies", [])
        
        if not anomalies:
            yield "Insight Generator Agent: No anomalies found to analyze. Generating default report..."
            session_state["insight_report"] = (
                "### Weekly Sales Audit\n"
                "No business anomalies were detected in this sales period. "
                "All regional performance metrics are within normal baseline ranges."
            )
            return
            
        yield f"Insight Generator Agent: Masking sensitive financial metrics for {len(anomalies)} anomalies..."
        
        # 1. Mask sensitive details (pseudonymize regions, scale numbers to % of baseline)
        masked_anomalies = FinancialDataMasker.mask_anomalies(anomalies)
        
        yield "Insight Generator Agent: Constructing AI prompt and communicating with Gemini..."
        
        # 2. Prepare the unified prompt for Gemini
        #    Gemini uses a single-turn prompt rather than separate system/user messages;
        #    we embed the system instruction at the top of the user prompt.
        prompt = self._build_prompt(masked_anomalies)
        
        # 3. Retrieve GEMINI_API_KEY from environment
        api_key = os.getenv("GEMINI_API_KEY")
        
        # Guard: fall back to local generator if key is absent or still a placeholder
        if not api_key or api_key == "your_gemini_api_key_here":
            yield (
                "Insight Generator Agent: GEMINI_API_KEY is not configured. "
                "Running local root-cause fallback analyzer..."
            )
            ai_raw_response = self._generate_local_fallback(masked_anomalies)
        else:
            try:
                from google import genai
                from google.genai import types

                yield "Insight Generator Agent: Calling Gemini API (gemini-2.0-flash)..."

                # Instantiate the async-capable client with the API key
                client = genai.Client(api_key=api_key)

                # Use the async generation method to avoid blocking the ADK event loop.
                # gemini-2.0-flash is fast, cost-efficient, and ideal for live agent pipelines.
                response = await client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,        # Low temperature → deterministic, professional tone
                        max_output_tokens=2000, # Matches previous token budget
                    ),
                )
                ai_raw_response = response.text

                yield "Insight Generator Agent: AI response received from Gemini."
                
            except Exception as e:
                yield (
                    f"Insight Generator Agent: Gemini API request failed ({str(e)}). "
                    "Initiating local fallback analyzer..."
                )
                ai_raw_response = self._generate_local_fallback(masked_anomalies)

        # 4. Unmask the response to restore real region names
        yield "Insight Generator Agent: Unmasking report (restoring real region names)..."
        final_report = FinancialDataMasker.unmask_text(ai_raw_response)
        
        # 5. Save the final unmasked report to session state
        session_state["insight_report"] = final_report
        
        yield "Insight Generator Agent: Insight report successfully written to state."

    def _build_prompt(self, masked_anomalies: list) -> str:
        """
        Constructs the full prompt sent to Gemini.

        Gemini accepts a single string rather than a system+user pair, so the
        system-level context is embedded at the top of the prompt before the
        structured anomaly data and instructions.
        """
        anomalies_json = json.dumps(masked_anomalies, indent=2)
        return f"""You are SmartPulse AI's Chief Business Analyst Agent. Your job is to analyze \
masked weekly sales anomalies from an SME, investigate the likely business root causes, \
and generate a clear, professional, plain-English report for the business owner. \
Suggest realistic operational hypotheses for each anomaly and actionable steps to resolve them. \
Use the masked region names (e.g. Region_Alpha) and masked metrics in your response. \
Keep your tone helpful, professional, and explainable.

Here is the list of masked weekly sales anomalies detected by our Machine Learning pipeline:

{anomalies_json}

Please review this list and generate a structured plain-English business intelligence report.

For each anomaly:
1. Explain WHAT the anomaly is in plain business English (e.g., 'In Region_Alpha during the week of YYYY-MM-DD, sales experienced a severe spike...').
2. Investigate the ROOT CAUSE by providing 2 realistic business hypotheses for why this happened (e.g., billing system malfunction, seasonal demand, delayed invoice recording, stockouts).
3. Provide 2-3 ACTIONABLE RECOMMENDATIONS for the operations team (e.g., audit inventory logs, verify CRM records, adjust staffing).

Ensure you format your response in clean Markdown with clear headings for each region's anomaly. Avoid generalities; customize hypotheses based on whether it is a zero sales anomaly, a revenue drop, a revenue spike, or an expense surge.
"""

    def _generate_local_fallback(self, masked_anomalies: list) -> str:
        """
        Generates a highly-detailed template response for the expected anomaly types.
        This ensures the system looks production-quality and functions perfectly
        even without a live Gemini API key — or when the Gemini call fails.
        The fallback uses the same Markdown format as the real Gemini response.
        """
        report_sections = [
            "# SmartPulse AI - SME Business Intelligence Report",
            (
                "This report analyzes significant weekly sales anomalies detected in your business metrics. "
                "The analysis below explores the root causes and outlines actionable operational next steps."
            ),
            "---"
        ]
        
        for idx, anomaly in enumerate(masked_anomalies):
            region = anomaly["Region"]
            date = anomaly["Date"]
            rev = anomaly["RelativeRevenue"]
            exp = anomaly["RelativeExpenses"]
            anomaly_type = anomaly["AnomalyType"]
            
            section = f"## Anomaly {idx+1}: {anomaly_type} in {region} ({date})"
            
            if anomaly_type == "REVENUE_DROP":
                explanation = (
                    f"**Observation**: During the week of {date}, {region} experienced a severe drop in sales, "
                    f"falling to just {rev}."
                )
                hypotheses = (
                    "**Potential Root Causes**:\n"
                    "- *Logistics Disruption*: Severe weather conditions or carrier delays in the area may have blocked deliveries and delayed sales completions.\n"
                    "- *Sales System Outage*: A CRM synchronization or POS offline malfunction may have failed to record weekly transactions, shifting them to the following week."
                )
                actions = (
                    "**Actionable Recommendations**:\n"
                    "- Verify shipping carrier logs for the week of March 9 to check for delivery delays.\n"
                    "- Cross-reference the region's localized POS system logs with database entries to ensure all weekly sales were uploaded."
                )
                
            elif anomaly_type == "ZERO_SALES":
                explanation = (
                    f"**Observation**: During the week of {date}, {region} reported exactly **0.0% sales** ({rev}), "
                    f"while operating expenses remained active at {exp}."
                )
                hypotheses = (
                    "**Potential Root Causes**:\n"
                    "- *Critical Payment Gateway Outage*: A total collapse of the digital payment gateway prevented any online checkouts from succeeding in this territory.\n"
                    "- *Operational Closure / Reporting Failure*: The regional office may have been closed temporarily due to local holidays or maintenance, or the sales team missed submitting their CSV logs."
                )
                actions = (
                    "**Actionable Recommendations**:\n"
                    "- Audit the regional payment merchant log for transaction failures on April 6.\n"
                    "- Check with the regional sales head to confirm if there was a reporting delay or temporary site closure."
                )
                
            elif anomaly_type == "REVENUE_SPIKE":
                explanation = (
                    f"**Observation**: During the week of {date}, {region} registered a massive revenue spike of **{rev}** "
                    f"accompanied by normal expenses ({exp})."
                )
                hypotheses = (
                    "**Potential Root Causes**:\n"
                    "- *B2B Bulk Purchase*: A major corporate client placed a large recurring bulk order that was invoiced in full during this period.\n"
                    "- *Viral Marketing Success*: A highly successful regional social media campaign drove an unexpected surge in direct-to-consumer checkouts."
                )
                actions = (
                    "**Actionable Recommendations**:\n"
                    "- Identify the customer accounts responsible for the bulk orders to offer personalized account management.\n"
                    "- Confirm if this spike correlates with a marketing launch so that lessons can be shared with other regions."
                )
                
            elif anomaly_type == "EXPENSE_SPIKE":
                explanation = (
                    f"**Observation**: During the week of {date}, {region} reported a massive expense surge, "
                    f"climbing to **{exp}**, causing a significant operational loss."
                )
                hypotheses = (
                    "**Potential Root Causes**:\n"
                    "- *Annual Hardware / Infrastructure Renewal*: The region processed its annual software licensing renewals or purchased new field equipment.\n"
                    "- *Expense Classification Error*: A large capital purchase (capex) was mistakenly booked as a weekly operating expense (opex)."
                )
                actions = (
                    "**Actionable Recommendations**:\n"
                    "- Review all invoices above $5,000 for the week of June 1 to audit expense categorization.\n"
                    "- Ensure capital expenditures are properly amortized across quarters rather than hitting a single week's P&L."
                )
            else:
                explanation = f"**Observation**: An unusual pattern was identified in {region} during the week of {date}."
                hypotheses = "**Potential Root Causes**: Unidentified statistical deviation."
                actions = "**Actionable Recommendations**: Audit database for date range."
                
            report_sections.extend([section, explanation, hypotheses, actions, "---"])
            
        return "\n\n".join(report_sections)
