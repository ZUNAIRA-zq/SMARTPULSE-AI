/**
 * SmartPulse AI - Dashboard Component
 * 
 * Purpose:
 *     Serves as the main control center for SmartPulse AI, displaying KPI cards,
 *     anomaly trends, AI audit findings, and mock alert logs.
 * 
 * Role in Agent System:
 *     Interacts with the FastAPI server to trigger the multi-agent pipeline and
 *     stream progress logs from the Orchestrator, Data Monitor, Insight Generator, 
 *     and Alert Agent in real-time.
 * 
 * Design Decisions:
 *     - Real-Time Agent Console: A built-in terminal-like console displays streaming logs 
 *       directly from individual agents as they run, enabling deep explainability.
 *     - Premium Dashboard Aesthetics: Utilizes custom glassmorphism panels, 
 *       a high-contrast dark palette, dynamic Lucide React icons, and smooth layout transitions.
 *     - Stream Management: Uses a chunk decoder to parse line-delimited event streams 
 *       sent by FastAPI during execution, dynamically updating the active console log.
 */
import React, { useState, useRef, useMemo, useEffect } from 'react';
import { Upload, AlertTriangle, Send, Terminal, Loader2, Sparkles, TrendingUp, DollarSign, CheckCircle2, X } from 'lucide-react';
import AnomalyChart from './AnomalyChart';
import InsightPanel from './InsightPanel';
import AlertLog from './AlertLog';

export default function Dashboard({ 
  rawData = [], 
  anomalies = [], 
  insightReport = '', 
  alerts = [], 
  onUploadSuccess 
}) {
  const [activeTab, setActiveTab] = useState('chart');
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [agentLogs, setAgentLogs] = useState([]);
  const [pipelineSuccess, setPipelineSuccess] = useState(null); // { anomalyCount, alertStatus }
  const fileInputRef = useRef(null);
  const consoleEndRef = useRef(null); // Anchor to auto-scroll console to bottom

  // Auto-scroll the agent console whenever new logs arrive
  useEffect(() => {
    consoleEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [agentLogs]);

  // Compute KPI values
  const totalRevenue = useMemo(() => {
    return rawData.reduce((sum, item) => sum + item.Revenue, 0);
  }, [rawData]);

  const totalProfit = useMemo(() => {
    return rawData.reduce((sum, item) => sum + item.Profit, 0);
  }, [rawData]);

  // Handle file drop events
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      uploadFile(e.target.files[0]);
    }
  };

  const triggerFileSelect = () => {
    fileInputRef.current.click();
  };

  // Perform upload and read streaming response
  const uploadFile = async (file) => {
    if (!file.name.endsWith('.csv')) {
      alert('Please upload a valid CSV file.');
      return;
    }

    setIsUploading(true);
    setAgentLogs([]);
    setActiveTab('console'); // Shift tab to the Agent console to show real-time progress
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed. Server returned an error.');
      }

      // Read the streaming text event-stream line-by-line
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Retain the last unfinished line in the buffer
        buffer = lines.pop();

        for (const line of lines) {
          if (line.trim()) {
            try {
              const event = jsonParseSafe(line);
              if (event) {
                if (event.type === 'log') {
                  setAgentLogs((prev) => [
                    ...prev, 
                    {
                      agent: event.agent,
                      message: event.message,
                      timestamp: new Date().toLocaleTimeString()
                    }
                  ]);
                } else if (event.type === 'result') {
                  // Pipeline completed successfully! Refresh data in App
                  onUploadSuccess(event.data);
                  // Show success banner
                  setPipelineSuccess({
                    anomalyCount: event.data?.anomalies?.length ?? 0,
                    alertStatus: event.data?.latest_alert?.status ?? 'Logged'
                  });
                  // Push a final indicator log
                  setAgentLogs((prev) => [
                    ...prev,
                    {
                      agent: 'orchestrator',
                      message: `✔ Pipeline Complete — ${event.data?.anomalies?.length ?? 0} anomalies detected. Switch tabs to view results.`,
                      timestamp: new Date().toLocaleTimeString()
                    }
                  ]);
                  // Stay on console so user can read full log
                }
              }
            } catch (e) {
              console.error('Error parsing streaming line:', line, e);
            }
          }
        }
      }
    } catch (err) {
      console.error(err);
      setAgentLogs((prev) => [
        ...prev,
        {
          agent: 'orchestrator',
          message: `❌ Pipeline Failure: ${err.message}`,
          timestamp: new Date().toLocaleTimeString()
        }
      ]);
    } finally {
      setIsUploading(false);
    }
  };

  const jsonParseSafe = (str) => {
    try {
      return JSON.parse(str);
    } catch {
      return null;
    }
  };

  // Render agent console log lines
  const getAgentColor = (agent) => {
    switch (agent) {
      case 'orchestrator': return 'text-purple-400';
      case 'data_monitor': return 'text-sky-400';
      case 'insight_generator': return 'text-indigo-400';
      case 'alert_agent': return 'text-amber-400';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="space-y-6">

      {/* Success Banner */}
      {pipelineSuccess && (
        <div className="flex items-center justify-between gap-4 px-5 py-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-sm animate-pulse-glow">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="text-emerald-400 shrink-0" size={18} />
            <div>
              <p className="font-bold text-emerald-300">Pipeline Complete!</p>
              <p className="text-xs text-emerald-400/80">
                {pipelineSuccess.anomalyCount} anomalies detected &mdash; alert status: <span className="font-semibold">{pipelineSuccess.alertStatus}</span>. Switch tabs to review findings.
              </p>
            </div>
          </div>
          <button
            onClick={() => setPipelineSuccess(null)}
            className="text-emerald-400/60 hover:text-emerald-300 transition-colors cursor-pointer shrink-0"
            aria-label="Dismiss success banner"
          >
            <X size={16} />
          </button>
        </div>
      )}

      
      {/* 1. Header Row */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-extrabold text-white tracking-tight flex items-center gap-2">
            SmartPulse AI
            <span className="text-xs px-2 py-0.5 rounded-md bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">SME BI Agent</span>
          </h2>
          <p className="text-sm text-gray-400">Automated sales anomaly detection, root-cause investigation, and email digests.</p>
        </div>

        {/* 2. Upload Box */}
        <div 
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={triggerFileSelect}
          className={`flex items-center gap-3 px-6 py-3 rounded-xl border border-dashed transition-all cursor-pointer ${
            dragActive 
              ? 'border-indigo-400 bg-indigo-500/10' 
              : 'border-white/10 bg-slate-900/40 hover:bg-slate-900/60 hover:border-indigo-500/30'
          }`}
        >
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileChange} 
            className="hidden" 
            accept=".csv"
          />
          {isUploading ? (
            <Loader2 className="animate-spin text-indigo-400 shrink-0" size={20} />
          ) : (
            <Upload className="text-indigo-400 shrink-0" size={20} />
          )}
          <div className="text-left">
            <p className="text-xs font-bold text-white">
              {isUploading ? 'Running Agent Team...' : 'Upload sales CSV'}
            </p>
            <p className="text-[10px] text-gray-400">Drag sales CSV or click to browse</p>
          </div>
        </div>
      </div>

      {/* 3. KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Total Revenue */}
        <div className="glass-panel glass-panel-hover p-5 rounded-2xl border border-white/5 flex items-center gap-4">
          <div className="p-3.5 rounded-xl bg-indigo-600/10 border border-indigo-500/20 text-indigo-400">
            <DollarSign size={22} />
          </div>
          <div>
            <span className="text-xs text-gray-400 font-semibold block">Total Revenue</span>
            <span className="text-xl font-extrabold text-white">${totalRevenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
          </div>
        </div>

        {/* Total Profit */}
        <div className="glass-panel glass-panel-hover p-5 rounded-2xl border border-white/5 flex items-center gap-4">
          <div className="p-3.5 rounded-xl bg-emerald-600/10 border border-emerald-500/20 text-emerald-400">
            <TrendingUp size={22} />
          </div>
          <div>
            <span className="text-xs text-gray-400 font-semibold block">Operating Profit</span>
            <span className={`text-xl font-extrabold ${totalProfit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              ${totalProfit.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </span>
          </div>
        </div>

        {/* Active Anomalies */}
        <div className="glass-panel glass-panel-hover p-5 rounded-2xl border border-white/5 flex items-center gap-4">
          <div className="p-3.5 rounded-xl bg-rose-600/10 border border-rose-500/20 text-rose-400">
            <AlertTriangle size={22} />
          </div>
          <div>
            <span className="text-xs text-gray-400 font-semibold block">Flagged Anomalies</span>
            <span className="text-xl font-extrabold text-white">{anomalies.length}</span>
          </div>
        </div>

        {/* Alert Status */}
        <div className="glass-panel glass-panel-hover p-5 rounded-2xl border border-white/5 flex items-center gap-4">
          <div className="p-3.5 rounded-xl bg-amber-600/10 border border-amber-500/20 text-amber-400">
            <Send size={22} />
          </div>
          <div>
            <span className="text-xs text-gray-400 font-semibold block">Logged Alerts (Mock)</span>
            <span className="text-xl font-extrabold text-white">{alerts.length}</span>
          </div>
        </div>

      </div>

      {/* 4. Tab Navigation */}
      <div className="flex border-b border-white/10 gap-6">
        <button
          onClick={() => setActiveTab('chart')}
          className={`pb-3.5 text-xs font-bold uppercase tracking-wider border-b-2 transition-all cursor-pointer ${
            activeTab === 'chart' 
              ? 'border-indigo-500 text-white' 
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          Trend Analytics
        </button>
        <button
          onClick={() => setActiveTab('insights')}
          className={`pb-3.5 text-xs font-bold uppercase tracking-wider border-b-2 transition-all cursor-pointer ${
            activeTab === 'insights' 
              ? 'border-indigo-500 text-white' 
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          AI Audit Findings
        </button>
        <button
          onClick={() => setActiveTab('alerts')}
          className={`pb-3.5 text-xs font-bold uppercase tracking-wider border-b-2 transition-all cursor-pointer ${
            activeTab === 'alerts' 
              ? 'border-indigo-500 text-white' 
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          Alert logs
        </button>
        <button
          onClick={() => setActiveTab('console')}
          className={`pb-3.5 text-xs font-bold uppercase tracking-wider border-b-2 transition-all flex items-center gap-1.5 cursor-pointer ${
            activeTab === 'console' 
              ? 'border-indigo-500 text-white' 
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          <Terminal size={14} />
          Agent Console
        </button>
      </div>

      {/* 5. Main Content Panel */}
      <div className="grid grid-cols-1 gap-6">
        
        {activeTab === 'chart' && (
          <AnomalyChart rawData={rawData} anomalies={anomalies} />
        )}

        {activeTab === 'insights' && (
          <InsightPanel insightReport={insightReport} />
        )}

        {activeTab === 'alerts' && (
          <AlertLog alerts={alerts} />
        )}

        {activeTab === 'console' && (
          <div className="glass-panel p-6 rounded-2xl border border-white/8 shadow-xl">
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-white/5">
              <h3 className="text-sm font-bold text-white flex items-center gap-1.5 font-mono">
                <Terminal size={14} className="text-indigo-400" />
                Multi-Agent Team execution monitor
              </h3>
              {isUploading && (
                <span className="flex items-center gap-1 text-xs text-indigo-400 font-semibold animate-pulse">
                  <Sparkles size={12} className="animate-spin" />
                  Agents Thinking...
                </span>
              )}
            </div>
            
            {/* Terminal console */}
            <div className="bg-black/80 rounded-xl p-5 border border-indigo-500/10 font-mono text-xs leading-relaxed h-[350px] overflow-y-auto space-y-2.5">
              {agentLogs.length === 0 ? (
                <div className="text-gray-600 italic">Console idle. Upload a CSV to view active agent communication.</div>
              ) : (
                agentLogs.map((log, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <span className="text-gray-500 shrink-0 select-none">[{log.timestamp}]</span>
                    <span className={`font-semibold shrink-0 select-none w-28 ${getAgentColor(log.agent)}`}>
                      @{log.agent.toUpperCase()}:
                    </span>
                    <span className="text-gray-300 break-all">{log.message}</span>
                  </div>
                ))
              )}
              {/* Invisible anchor — scrollIntoView keeps console pinned to bottom */}
              <div ref={consoleEndRef} />
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
