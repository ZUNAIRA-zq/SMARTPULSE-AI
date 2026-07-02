"""
SmartPulse AI - ML Anomaly Detector

Purpose:
    This module uses Machine Learning (scikit-learn's Isolation Forest) combined with 
    statistical heuristics to detect revenue and expense anomalies in weekly sales data.

Role in Agent System:
    The Data Monitor Agent utilizes this module after ingesting the CSV sales data. 
    The detector returns a structured list of anomalies which are then passed to the 
    Orchestrator, and subsequently to the Insight Generator.

Design Decisions:
    - Per-Region Isolation Forest: Because different regions have vastly different baseline sales 
      (e.g., North averages $30k while Central averages $18k), running a single global model 
      would flag Central as a permanent anomaly due to its smaller scale. Running a separate 
      model for each region prevents this scale-bias.
    - Hybrid Statistical Filtering: Isolation Forest flags the most outlying 8-10% of points 
      regardless of whether they represent minor natural variance or serious business threats. 
      To ensure the AI is only triggered for significant business events, we filter the 
      Isolation Forest predictions using Z-score thresholds against a shifted rolling baseline.
    - Shifted Rolling Baseline: Rolling mean/std are computed with `.shift(1)` so each point
      is evaluated against the PRIOR weeks only. This prevents a spike from inflating its own
      baseline, which would suppress its Z-score and cause missed detections.
    - Categorization Heuristic: Automatically determines if an anomaly is a "REVENUE_DROP", 
      "ZERO_SALES", "REVENUE_SPIKE", or "EXPENSE_SPIKE" by comparing metrics against rolling averages.

Agent Communication Pattern:
    1. Data Monitor Agent ingests pandas DataFrame.
    2. Data Monitor Agent calls SMEAnomalyDetector.detect_anomalies(df).
    3. The detector returns a list of dictionaries detailing the anomaly type, severity, and values.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any
from sklearn.ensemble import IsolationForest

class SMEAnomalyDetector:
    """
    Detects business intelligence anomalies (revenue drops, spikes, expense surges) 
    using scikit-learn's Isolation Forest and shifted rolling z-scores.
    """

    def __init__(self, contamination: float = 0.1, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state

    def detect_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Processes sales data and returns a list of verified anomalies.
        
        Args:
            df: Pandas DataFrame containing columns ['Date', 'Region', 'Revenue', 'Expenses', 'Profit']
            
        Returns:
            List of dictionaries representing detected anomaly events.
        """
        # Ensure correct data types
        df = df.copy()
        df["Revenue"] = pd.to_numeric(df["Revenue"])
        df["Expenses"] = pd.to_numeric(df["Expenses"])
        df["Profit"] = pd.to_numeric(df["Profit"])
        df["Date"] = df["Date"].astype(str)

        detected_anomalies = []

        # Process each region independently to avoid scale bias
        regions = df["Region"].unique()
        for region in regions:
            region_df = df[df["Region"] == region].sort_values("Date").reset_index(drop=True)
            
            if len(region_df) < 6:
                # Need sufficient data points to fit model and compute rolling averages
                continue
                
            # Prepare feature matrix for Isolation Forest (Revenue and Expenses)
            X = region_df[["Revenue", "Expenses"]].values
            
            # Fit Isolation Forest
            model = IsolationForest(
                contamination=self.contamination, 
                random_state=self.random_state,
                n_estimators=100
            )
            model.fit(X)
            
            # Predict: -1 represents anomalies, 1 represents inliers
            predictions = model.predict(X)
            
            # Get raw anomaly scores (lower = more anomalous)
            anomaly_scores = model.decision_function(X)
            
            # Compute SHIFTED rolling statistics (window=6 weeks, shifted by 1).
            # The .shift(1) is critical: it ensures each row's baseline mean/std is computed
            # from PRIOR weeks only, preventing a spike from diluting its own Z-score.
            rolling_rev = region_df["Revenue"].rolling(window=6, min_periods=3)
            rolling_exp = region_df["Expenses"].rolling(window=6, min_periods=3)

            rolling_rev_mean = rolling_rev.mean().shift(1)
            rolling_rev_std  = rolling_rev.std().shift(1)
            rolling_exp_mean = rolling_exp.mean().shift(1)
            rolling_exp_std  = rolling_exp.std().shift(1)

            # Global fallback stats (used for first few rows without enough prior history)
            global_rev_mean = region_df["Revenue"].mean()
            global_rev_std  = region_df["Revenue"].std() or 1.0
            global_exp_mean = region_df["Expenses"].mean()
            global_exp_std  = region_df["Expenses"].std() or 1.0
            
            # Loop through records and check those flagged by Isolation Forest
            for i, row in region_df.iterrows():
                if predictions[i] == -1:
                    # Verify using rolling statistical Z-scores
                    rev_val = row["Revenue"]
                    exp_val = row["Expenses"]
                    
                    # Use shifted rolling baseline; fall back to global stats if NaN (first rows)
                    mean_rev = rolling_rev_mean[i] if not pd.isna(rolling_rev_mean[i]) else global_rev_mean
                    std_rev  = rolling_rev_std[i]  if not pd.isna(rolling_rev_std[i])  else global_rev_std
                    mean_exp = rolling_exp_mean[i] if not pd.isna(rolling_exp_mean[i]) else global_exp_mean
                    std_exp  = rolling_exp_std[i]  if not pd.isna(rolling_exp_std[i])  else global_exp_std

                    # Protect against zero std
                    std_rev = std_rev if std_rev > 0 else 1.0
                    std_exp = std_exp if std_exp > 0 else 1.0
                    
                    z_rev = (rev_val - mean_rev) / std_rev
                    z_exp = (exp_val - mean_exp) / std_exp
                    
                    # Determine if it's a significant anomaly
                    is_anomaly = False
                    anomaly_type = "UNKNOWN"
                    severity = abs(anomaly_scores[i])
                    
                    # 1. Zero sales check (always flag — no revenue is always critical)
                    if rev_val == 0:
                        is_anomaly = True
                        anomaly_type = "ZERO_SALES"
                        
                    # 2. Revenue Drop (> 1.8 std deviations below prior mean, or > 50% drop)
                    elif z_rev < -1.8 or rev_val < (mean_rev * 0.5):
                        is_anomaly = True
                        anomaly_type = "REVENUE_DROP"
                        
                    # 3. Revenue Spike (> 1.8 std deviations above prior mean)
                    elif z_rev > 1.8:
                        is_anomaly = True
                        anomaly_type = "REVENUE_SPIKE"
                        
                    # 4. Expense Surge (> 1.8 std deviations above prior mean)
                    elif z_exp > 1.8:
                        is_anomaly = True
                        anomaly_type = "EXPENSE_SPIKE"
                        
                    if is_anomaly:
                        detected_anomalies.append({
                            "Date": row["Date"],
                            "Region": row["Region"],
                            "Revenue": float(rev_val),
                            "Expenses": float(exp_val),
                            "Profit": float(row["Profit"]),
                            "AnomalyType": anomaly_type,
                            "SeverityScore": round(float(severity), 4),
                            "ZScoreRevenue": round(float(z_rev), 2),
                            "ZScoreExpenses": round(float(z_exp), 2)
                        })
                        
        # Sort anomalies by date so they form a chronological log
        detected_anomalies = sorted(detected_anomalies, key=lambda x: x["Date"])
        return detected_anomalies

