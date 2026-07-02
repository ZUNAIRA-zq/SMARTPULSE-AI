import React, { useState, useMemo } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot } from 'recharts';
import { TrendingUp, AlertCircle, Calendar } from 'lucide-react';

export default function AnomalyChart({ rawData = [], anomalies = [] }) {
  const [selectedRegion, setSelectedRegion] = useState('All');

  // Available regions in the dataset
  const regions = useMemo(() => {
    const unique = new Set(rawData.map((item) => item.Region));
    return ['All', ...Array.from(unique)];
  }, [rawData]);

  // Filter raw data based on selected region
  const filteredData = useMemo(() => {
    if (!rawData || rawData.length === 0) return [];
    
    // Group by Date for 'All' region to show aggregate performance,
    // or filter by specific region
    if (selectedRegion === 'All') {
      const dateMap = {};
      rawData.forEach((item) => {
        const date = item.Date;
        if (!dateMap[date]) {
          dateMap[date] = { Date: date, Revenue: 0, Expenses: 0, Profit: 0 };
        }
        dateMap[date].Revenue += item.Revenue;
        dateMap[date].Expenses += item.Expenses;
        dateMap[date].Profit += item.Profit;
      });
      return Object.values(dateMap).sort((a, b) => new Date(a.Date) - new Date(b.Date));
    }
    
    return rawData
      .filter((item) => item.Region === selectedRegion)
      .sort((a, b) => new Date(a.Date) - new Date(b.Date));
  }, [rawData, selectedRegion]);

  // Filter anomalies for the selected region
  const regionAnomalies = useMemo(() => {
    if (selectedRegion === 'All') return anomalies;
    return anomalies.filter((a) => a.Region === selectedRegion);
  }, [anomalies, selectedRegion]);

  // Find corresponding data points for ReferenceDots in Recharts
  const anomalyDots = useMemo(() => {
    const dots = [];
    regionAnomalies.forEach((anomaly) => {
      const match = filteredData.find((d) => d.Date === anomaly.Date);
      if (match) {
        dots.push({
          x: anomaly.Date,
          y: match.Revenue,
          type: anomaly.AnomalyType,
          region: anomaly.Region,
          description: `${anomaly.AnomalyType}: $${anomaly.Revenue.toLocaleString()}`
        });
      }
    });
    return dots;
  }, [regionAnomalies, filteredData]);

  // Custom tooltips for premium feel
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const dateAnomalies = anomalies.filter((a) => a.Date === label && (selectedRegion === 'All' || a.Region === selectedRegion));
      
      return (
        <div className="glass-panel p-4 rounded-xl border border-indigo-500/20 text-sm shadow-2xl">
          <p className="text-gray-400 font-semibold mb-2 flex items-center gap-1.5">
            <Calendar size={14} className="text-indigo-400" />
            {label}
          </p>
          <div className="space-y-1.5">
            <p className="text-indigo-300 font-medium">
              Revenue: <span className="text-white">${payload[0].value.toLocaleString()}</span>
            </p>
            <p className="text-amber-400 font-medium">
              Expenses: <span className="text-white">${payload[1].value.toLocaleString()}</span>
            </p>
            <p className={`font-semibold ${data.Revenue - data.Expenses >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              Profit: ${(data.Revenue - data.Expenses).toLocaleString()}
            </p>
          </div>

          {dateAnomalies.length > 0 && (
            <div className="mt-3 pt-2.5 border-t border-white/10 space-y-1.5">
              {dateAnomalies.map((a, idx) => (
                <div key={idx} className="flex items-start gap-1.5 text-rose-400 text-xs">
                  <AlertCircle size={14} className="shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold">[{a.Region}] {a.AnomalyType}</span>
                    <p className="text-gray-400">Score: {a.SeverityScore}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="glass-panel p-6 rounded-2xl border border-white/8 shadow-xl">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <TrendingUp className="text-indigo-400" />
            Financial Performance & Anomalies
          </h3>
          <p className="text-xs text-gray-400">Weekly revenue, operating expenses, and profit trends</p>
        </div>

        {/* Region Selector Tab List */}
        <div className="flex flex-wrap gap-1.5 bg-slate-900/60 p-1 rounded-xl border border-white/5">
          {regions.map((region) => (
            <button
              key={region}
              onClick={() => setSelectedRegion(region)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                selectedRegion === region
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
            >
              {region}
            </button>
          ))}
        </div>
      </div>

      {/* Recharts Performance Visualizer */}
      <div className="h-[300px] w-full mt-4">
        {filteredData.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-500">
            No sales data available. Ingest a sales CSV.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={filteredData} margin={{ top: 15, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0}/>
                </linearGradient>
                <linearGradient id="colorExp" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.15}/>
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0}/>
                </linearGradient>
                <linearGradient id="colorProfit" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.18}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis 
                dataKey="Date" 
                stroke="#6b7280" 
                fontSize={10}
                tickLine={false}
              />
              <YAxis 
                stroke="#6b7280" 
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `$${(val / 1000)}k`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area 
                type="monotone" 
                dataKey="Revenue" 
                stroke="#6366f1" 
                strokeWidth={2}
                fillOpacity={1} 
                fill="url(#colorRev)" 
              />
              <Area 
                type="monotone" 
                dataKey="Expenses" 
                stroke="#f59e0b" 
                strokeWidth={1.5}
                fillOpacity={1} 
                fill="url(#colorExp)" 
              />
              <Area
                type="monotone"
                dataKey="Profit"
                stroke="#10b981"
                strokeWidth={1.5}
                strokeDasharray="4 3"
                fillOpacity={1}
                fill="url(#colorProfit)"
              />
              
              {/* Plot glowing red dots for anomaly positions */}
              {anomalyDots.map((dot, index) => (
                <ReferenceDot
                  key={index}
                  x={dot.x}
                  y={dot.y}
                  r={6}
                  fill="#ef4444"
                  stroke="#ffffff"
                  strokeWidth={2}
                  className="cursor-pointer animate-pulse-glow"
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Chart Legend */}
      <div className="flex flex-wrap items-center gap-4 mt-2 text-[11px] text-gray-400 font-medium">
        <span className="flex items-center gap-1.5"><span className="inline-block w-3 h-0.5 bg-indigo-500 rounded"></span>Revenue</span>
        <span className="flex items-center gap-1.5"><span className="inline-block w-3 h-0.5 bg-amber-400 rounded"></span>Expenses</span>
        <span className="flex items-center gap-1.5"><span className="inline-block w-3 h-0.5 bg-emerald-400 rounded" style={{borderTop:'1px dashed #10b981', background:'none'}}></span>Profit</span>
        <span className="flex items-center gap-1.5"><span className="inline-block w-2.5 h-2.5 rounded-full bg-red-500 border border-white shadow-sm shadow-red-500/60"></span>Anomaly</span>
      </div>

      {/* Micro-Panel showing Anomaly Bullets */}
      {regionAnomalies.length > 0 && (
        <div className="mt-4 pt-4 border-t border-white/5">
          <h4 className="text-xs font-semibold text-rose-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <AlertCircle size={14} />
            Detected Anomalies ({regionAnomalies.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {regionAnomalies.map((a, idx) => {
              const typeColors = {
                REVENUE_DROP:  'bg-rose-500/20 text-rose-300 border-rose-500/30',
                ZERO_SALES:    'bg-red-600/20 text-red-300 border-red-600/30',
                REVENUE_SPIKE: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
                EXPENSE_SPIKE: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
              };
              const badgeClass = typeColors[a.AnomalyType] || 'bg-gray-500/20 text-gray-300 border-gray-500/30';
              return (
                <div 
                  key={idx} 
                  className="flex items-center justify-between p-3 rounded-xl bg-rose-500/5 border border-rose-500/10 hover:border-rose-500/20 transition-all"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-white">{a.Region}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold border ${badgeClass}`}>
                        {a.AnomalyType.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="text-[10px] text-gray-500 mt-0.5">Week of {a.Date}</p>
                    <p className="text-[10px] text-gray-600 mt-0.5">Z&#x2080; Rev: {a.ZScoreRevenue > 0 ? '+' : ''}{a.ZScoreRevenue} &bull; Severity: {a.SeverityScore}</p>
                  </div>
                  <div className="text-right text-xs">
                    <span className="block font-semibold text-white">${a.Revenue.toLocaleString()}</span>
                    <span className="text-[10px] text-gray-400">Exp: ${a.Expenses.toLocaleString()}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
