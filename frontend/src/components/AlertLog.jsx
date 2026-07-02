/**
 * SmartPulse AI - Alert Log Component
 * 
 * Purpose:
 *     Renders the timeline audit log of email alerts drafted by the Alert Agent.
 * 
 * Role in Agent System:
 *     Provides visual confirmation of the final phase of the multi-agent orchestration.
 *     Since the Alert Agent runs permanently in Mock Mode, this log is the primary interface
 *     through which owners inspect drafted notifications without requiring real-world SMTP configurations.
 * 
 * Design Decisions:
 *     - Mock-First Timeline: Clearly presents alerts as "Mock Sent" using a blue badge
 *       to differentiate from active SMTP systems, showing all transaction logs and email templates.
 *     - Interactive Drilldown: Allows expanding/collapsing individual email bodies so business owners
 *       can review the detailed plain-English insights within the drafted email.
 *     - Responsive Glassmorphism: Built using translucent backdrops (glass-panel) and Tailwind CSS 
 *       utility classes for a premium dark mode layout.
 */
import React, { useState } from 'react';
import { Mail, ChevronDown, ChevronUp, Clock, User, AlertTriangle, CheckCircle, Info } from 'lucide-react';

export default function AlertLog({ alerts = [] }) {
  const [expandedIndex, setExpandedIndex] = useState(null);

  const toggleExpand = (index) => {
    if (expandedIndex === index) {
      setExpandedIndex(null);
    } else {
      setExpandedIndex(index);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'Delivered (Gmail/SMTP)':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle size={10} />
            Delivered
          </span>
        );
      case 'Logged (Mock Mode)':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20">
            <Info size={10} />
            Mock Sent
          </span>
        );
      case 'Delivery Failed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertTriangle size={10} />
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            {status}
          </span>
        );
    }
  };

  const formatTimestamp = (isoString) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleString(undefined, { 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="glass-panel p-6 rounded-2xl border border-white/8 shadow-xl flex flex-col h-full">
      <div className="border-b border-white/5 pb-4 mb-4">
        <h3 className="text-lg font-bold text-white flex items-center gap-2">
          <Mail className="text-indigo-400" />
          Alert Transmission Log (Mock Mode)
        </h3>
        <p className="text-xs text-gray-400">Audit trail of drafted executive email digests stored in backend/db/alerts.json</p>
      </div>

      <div className="flex-1 overflow-y-auto max-h-[500px] pr-2 space-y-4">
        {alerts.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-500 py-12">
            <p className="text-sm italic">No alerts recorded in the database. Run analysis to create an alert.</p>
          </div>
        ) : (
          <div className="relative pl-4 border-l border-indigo-900/60 ml-2 space-y-6">
            {alerts.map((alert, idx) => {
              const isExpanded = expandedIndex === idx;
              return (
                <div key={idx} className="relative">
                  {/* Timeline dot */}
                  <div className="absolute -left-[21px] top-1.5 w-3 h-3 rounded-full bg-indigo-500 border-2 border-slate-900" />
                  
                  <div className="glass-panel p-4 rounded-xl border border-white/5 hover:border-white/10 transition-all">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 mb-2">
                      <div className="flex items-center gap-1.5 text-xs text-indigo-300">
                        <Clock size={12} />
                        <span>{formatTimestamp(alert.timestamp)}</span>
                      </div>
                      <div>{getStatusBadge(alert.status)}</div>
                    </div>

                    <h4 className="text-sm font-bold text-white mb-1.5">{alert.subject}</h4>
                    
                    <div className="flex items-center gap-2 text-xs text-gray-400 mb-3">
                      <User size={12} className="text-gray-500" />
                      <span>To: {alert.recipient}</span>
                    </div>

                    <button
                      onClick={() => toggleExpand(idx)}
                      className="flex items-center gap-1 text-[11px] font-semibold text-indigo-400 hover:text-indigo-300 transition-all cursor-pointer"
                    >
                      {isExpanded ? (
                        <>
                          <ChevronUp size={14} />
                          Collapse Email Digest
                        </>
                      ) : (
                        <>
                          <ChevronDown size={14} />
                          Expand Email Digest
                        </>
                      )}
                    </button>

                    {isExpanded && (
                      <div className="mt-4 p-4 rounded-lg bg-black/40 border border-white/5 text-xs text-gray-300 font-mono whitespace-pre-wrap leading-relaxed max-h-[300px] overflow-y-auto">
                        {alert.body}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
