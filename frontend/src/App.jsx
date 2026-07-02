import React, { useState, useEffect } from 'react';
import Dashboard from './components/Dashboard';
import { Activity, ShieldAlert, Cpu } from 'lucide-react';

export default function App() {
  const [dashboardData, setDashboardData] = useState({
    raw_data: [],
    anomalies: [],
    insight_report: '',
    latest_alert: null
  });
  const [alerts, setAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch initial dashboard metrics and alert history on mount
  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // 1. Fetch dashboard metrics (which triggers initial run if cache is empty)
      const dashRes = await fetch('http://127.0.0.1:8000/api/dashboard');
      if (!dashRes.ok) {
        throw new Error('Failed to load dashboard data from backend.');
      }
      const dashData = await dashRes.json();
      setDashboardData(dashData);

      // 2. Fetch email alert logs
      const alertsRes = await fetch('http://127.0.0.1:8000/api/alerts');
      if (alertsRes.ok) {
        const alertsData = await alertsRes.json();
        setAlerts(alertsData);
      }
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // Callback triggered when the agent pipeline completes an upload run.
  // Always refetches the full dashboard from the backend to get the updated
  // raw_data for chart rendering — the stream result payload only contains
  // anomalies and the report, not the full records.
  const handleUploadSuccess = async (newData) => {
    try {
      const dashRes = await fetch('http://127.0.0.1:8000/api/dashboard');
      if (dashRes.ok) {
        const freshDash = await dashRes.json();
        setDashboardData(freshDash);
      } else {
        // Fallback: merge what we have from the stream result
        setDashboardData((prev) => ({ ...prev, ...newData }));
      }
    } catch {
      // Fallback if fetch fails
      setDashboardData((prev) => ({ ...prev, ...newData }));
    }
    
    // Refresh alert history to show the newly drafted email
    fetchAlerts();
  };

  const fetchAlerts = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/alerts');
      if (res.ok) {
        const data = await res.json();
        setAlerts(data);
      }
    } catch (e) {
      console.error('Failed to refresh alert logs:', e);
    }
  };

  return (
    <div className="min-h-screen text-slate-100 flex flex-col justify-between">
      
      {/* Premium Navbar Banner */}
      <header className="border-b border-white/5 bg-slate-950/20 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-gradient-to-tr from-indigo-600 to-purple-600 rounded-xl shadow-lg shadow-indigo-500/20 text-white animate-pulse">
              <Cpu size={18} />
            </div>
            <div>
              <h1 className="text-md font-bold text-white tracking-wide m-0">SMARTPULSE AI</h1>
              <p className="text-[10px] text-gray-400 font-semibold tracking-wider uppercase">SME Real-Time Intelligence</p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs font-semibold text-gray-400">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <Activity size={12} className="animate-pulse" />
              Connected
            </span>
          </div>
        </div>
      </header>

      {/* Main Dashboard Section */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-32 space-y-4">
            <div className="w-12 h-12 rounded-full border-4 border-indigo-500/20 border-t-indigo-500 animate-spin" />
            <div className="text-center">
              <p className="text-sm font-semibold text-white">Waking up SmartPulse AI agents...</p>
              <p className="text-xs text-gray-500 mt-1">First load fits Isolation Forest and loads sample analytics</p>
            </div>
          </div>
        ) : error ? (
          <div className="glass-panel p-8 rounded-2xl border-rose-500/20 max-w-lg mx-auto text-center mt-12">
            <ShieldAlert className="text-rose-500 mx-auto mb-4" size={40} />
            <h3 className="text-lg font-bold text-white mb-2">Backend Connection Lost</h3>
            <p className="text-sm text-gray-400 mb-6">{error}</p>
            <button 
              onClick={fetchInitialData}
              className="px-4 py-2 bg-indigo-600 text-white text-xs font-bold rounded-xl hover:bg-indigo-500 transition-all cursor-pointer"
            >
              Retry Connection
            </button>
          </div>
        ) : (
          <Dashboard 
            rawData={dashboardData.raw_data || dashboardData.raw_data_fallback || []}
            anomalies={dashboardData.anomalies || []}
            insightReport={dashboardData.insight_report || ''}
            alerts={alerts}
            onUploadSuccess={handleUploadSuccess}
          />
        )}
      </main>

      {/* Footer Banner */}
      <footer className="border-t border-white/5 bg-slate-950/10 py-6 text-center text-[10px] text-gray-500">
        <div className="max-w-7xl mx-auto px-4">
          <p>© {new Date().getFullYear()} SmartPulse AI. All rights reserved. Orchestrated via Google ADK multi-agent framework.</p>
        </div>
      </footer>

    </div>
  );
}
