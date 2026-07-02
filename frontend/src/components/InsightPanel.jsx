import React from 'react';
import { FileText, Download, ShieldCheck } from 'lucide-react';

export default function InsightPanel({ insightReport = '' }) {
  
  // Custom lightweight Markdown-to-HTML parser to avoid package dependency conflicts
  const renderMarkdown = (text) => {
    if (!text) {
      return (
        <p className="text-sm text-gray-500 italic">
          No audit reports available yet. Upload a sales CSV to trigger analysis.
        </p>
      );
    }

    const lines = text.split('\n');
    let inList = false;
    const elements = [];

    lines.forEach((line, index) => {
      const trimmed = line.trim();

      // Horizontal Rules
      if (trimmed === '---') {
        if (inList) {
          elements.push(<ul key={`ul-${index}`} className="list-disc pl-6 mb-4 space-y-1.5 text-gray-300 text-sm"></ul>);
          inList = false;
        }
        elements.push(<hr key={index} className="my-6 border-white/10" />);
        return;
      }

      // Headers (H1, H2, H3)
      if (trimmed.startsWith('# ')) {
        const title = trimmed.replace('# ', '');
        elements.push(
          <h1 key={index} className="text-xl md:text-2xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400 mt-6 mb-4">
            {parseBoldText(title)}
          </h1>
        );
        return;
      }
      if (trimmed.startsWith('## ')) {
        const title = trimmed.replace('## ', '');
        // Extract anomaly type from heading (e.g. "Anomaly 1: REVENUE_DROP in West (2026-03-09)")
        const typeMatch = title.match(/\b(REVENUE_DROP|ZERO_SALES|REVENUE_SPIKE|EXPENSE_SPIKE)\b/);
        const anomalyType = typeMatch ? typeMatch[1] : null;
        const typeColors = {
          REVENUE_DROP:  'bg-rose-500/20 text-rose-300 border-rose-500/30',
          ZERO_SALES:    'bg-red-600/20 text-red-300 border-red-600/30',
          REVENUE_SPIKE: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
          EXPENSE_SPIKE: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
        };
        const badgeClass = anomalyType ? (typeColors[anomalyType] || '') : '';
        elements.push(
          <h2 key={index} className="text-md md:text-lg font-bold text-white mt-5 mb-3 border-l-2 border-indigo-500 pl-3 flex flex-wrap items-center gap-2">
            <span>{parseBoldText(title)}</span>
            {anomalyType && (
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${badgeClass} shrink-0`}>
                {anomalyType.replace(/_/g, ' ')}
              </span>
            )}
          </h2>
        );
        return;
      }
      if (trimmed.startsWith('### ')) {
        const title = trimmed.replace('### ', '');
        elements.push(
          <h3 key={index} className="text-sm md:text-md font-semibold text-indigo-300 mt-4 mb-2">
            {parseBoldText(title)}
          </h3>
        );
        return;
      }

      // Bullet List Items
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        const itemText = trimmed.substring(2);
        if (!inList) {
          inList = true;
        }
        elements.push(
          <li key={index} className="ml-5 list-disc text-sm text-gray-300 mb-1.5 leading-relaxed">
            {parseBoldText(itemText)}
          </li>
        );
        return;
      }

      // End list if a non-bullet line is found
      if (inList && trimmed !== '') {
        inList = false;
      }

      // Paragraphs
      if (trimmed !== '') {
        elements.push(
          <p key={index} className="text-sm text-gray-300 leading-relaxed mb-4">
            {parseBoldText(trimmed)}
          </p>
        );
      }
    });

    return elements;
  };

  // Helper to parse **bold** text inline
  const parseBoldText = (text) => {
    const parts = text.split(/\*\*(.*?)\*\*/g);
    return parts.map((part, i) => {
      // Every odd element was surrounded by **
      if (i % 2 === 1) {
        return <strong key={i} className="text-white font-semibold">{part}</strong>;
      }
      // Check for italic *italic*
      const italicParts = part.split(/\*(.*?)\*/g);
      if (italicParts.length > 1) {
        return italicParts.map((ip, j) => {
          if (j % 2 === 1) {
            return <em key={j} className="text-gray-200 italic">{ip}</em>;
          }
          return ip;
        });
      }
      return part;
    });
  };

  // Export report utility
  const downloadReport = () => {
    const element = document.createElement("a");
    const file = new Blob([insightReport], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = "SmartPulse_AI_Insight_Report.md";
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="glass-panel p-6 rounded-2xl border border-white/8 shadow-xl flex flex-col h-full">
      <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-4">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <FileText className="text-indigo-400" />
            AI Root Cause Insights
          </h3>
          <p className="text-xs text-gray-400">Plain-English anomalies audit and hypotheses</p>
        </div>
        
        {insightReport && (
          <button 
            onClick={downloadReport}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white/5 text-gray-300 border border-white/10 hover:bg-white/10 hover:text-white transition-all cursor-pointer"
          >
            <Download size={14} />
            Export Markdown
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto max-h-[500px] pr-2 space-y-1">
        {renderMarkdown(insightReport)}
      </div>

      <div className="mt-4 pt-3 border-t border-white/5 flex items-center gap-2 text-[10px] text-emerald-400 font-semibold uppercase tracking-wider">
        <ShieldCheck size={14} />
        Secure: Financial numbers were masked before AI ingestion
      </div>
    </div>
  );
}
