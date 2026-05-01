"use client";

import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Activity, 
  Database, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  ExternalLink,
  Lock,
  RefreshCcw
} from 'lucide-react';

export default function DASCDashboard() {
  const [stats, setStats] = useState({ total: 0, commits: 0, rejections: 0, escalations: 0 });
  const [history, setHistory] = useState([]);
  const [integrity, setIntegrity] = useState({ status: 'checking', valid: true });

  // Mock data for initial render since the backend isn't running
  useEffect(() => {
    setStats({ total: 124, commits: 98, rejections: 18, escalations: 8 });
    setHistory([
      { intent_id: 'INT-99A', actor_agent: 'finance_agent', status: 'COMMIT', timestamp: '2026-05-01 12:00:01', record_hash: 'af82...12' },
      { intent_id: 'INT-99B', actor_agent: 'ops_agent', status: 'REJECT', timestamp: '2026-05-01 12:05:32', record_hash: '92b1...fc' },
      { intent_id: 'INT-99C', actor_agent: 'admin_agent', status: 'ESCALATE', timestamp: '2026-05-01 12:10:15', record_hash: '110d...ee' },
    ]);
    setIntegrity({ status: 'intact', valid: true });
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-slate-200 font-sans selection:bg-indigo-500/30">
      {/* Header */}
      <header className="border-b border-slate-800/60 bg-[#0a0a0c]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <ShieldCheck className="text-white w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white">DASC <span className="text-indigo-400 font-medium">Control Plane</span></h1>
              <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-bold">Deterministic Safety Boundary</p>
            </div>
          </div>
          
          <div className="flex items-center gap-6">
            <div className={`flex items-center gap-2 px-4 py-1.5 rounded-full border ${integrity.valid ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-rose-500/10 border-rose-500/20 text-rose-400'} text-xs font-semibold`}>
              <Lock className="w-3 h-3" />
              Chain Integrity: {integrity.status.toUpperCase()}
            </div>
            <button className="text-slate-400 hover:text-white transition-colors">
              <RefreshCcw className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-10">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
          {[
            { label: 'Total Intents', value: stats.total, icon: Activity, color: 'indigo' },
            { label: 'Commits', value: stats.commits, icon: CheckCircle2, color: 'emerald' },
            { label: 'Rejections', value: stats.rejections, icon: XCircle, color: 'rose' },
            { label: 'Escalations', value: stats.escalations, icon: AlertTriangle, color: 'amber' },
          ].map((stat, i) => (
            <div key={i} className="bg-[#111114] border border-slate-800/60 rounded-2xl p-6 hover:border-slate-700 transition-colors">
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm font-medium text-slate-400">{stat.label}</p>
                <stat.icon className={`w-5 h-5 text-${stat.color}-400`} />
              </div>
              <p className="text-3xl font-bold text-white">{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Main Content Split */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
          {/* Ledger Table */}
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Database className="w-5 h-5 text-indigo-400" />
                Bitemporal Ledger
              </h2>
              <button className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1">
                View Full Audit <ExternalLink className="w-3 h-3" />
              </button>
            </div>

            <div className="bg-[#111114] border border-slate-800/60 rounded-2xl overflow-hidden">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800/60 bg-slate-900/40">
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Intent ID</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Actor</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Timestamp</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Hash</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40">
                  {history.map((row, i) => (
                    <tr key={i} className="hover:bg-slate-800/20 transition-colors group cursor-pointer">
                      <td className="px-6 py-4">
                        <span className="font-mono text-indigo-400 text-sm font-medium">{row.intent_id}</span>
                      </td>
                      <td className="px-6 py-4 text-slate-300 text-sm">{row.actor_agent}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-md text-[10px] font-bold tracking-wide uppercase ${
                          row.status === 'COMMIT' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                          row.status === 'REJECT' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                          'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        }`}>
                          {row.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-500 text-xs">{row.timestamp}</td>
                      <td className="px-6 py-4 text-right">
                        <span className="font-mono text-slate-600 text-[10px] group-hover:text-slate-400">{row.record_hash}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Sidebar / Active Escalations */}
          <div className="space-y-6">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              Pending Escalations
            </h2>
            
            <div className="space-y-4">
              {[1, 2].map((_, i) => (
                <div key={i} className="bg-[#111114] border border-amber-500/20 rounded-2xl p-6 space-y-4 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-2 bg-amber-500/10 rounded-bl-xl text-amber-400">
                    <AlertTriangle className="w-4 h-4" />
                  </div>
                  
                  <div>
                    <p className="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-1">Tier 4 Violation</p>
                    <h3 className="text-sm font-bold text-white">Shutdown Cluster 01</h3>
                  </div>
                  
                  <div className="text-xs text-slate-400 bg-slate-900/50 p-3 rounded-lg font-mono">
                    intent_id: "ESCL-44X"<br/>
                    agent: "auto_scaler"<br/>
                    reason: "MANDATORY_HUMAN_APPROVAL"
                  </div>

                  <div className="flex gap-2 pt-2">
                    <button className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold py-2.5 rounded-xl transition-all active:scale-95 shadow-lg shadow-emerald-500/20">
                      Approve
                    </button>
                    <button className="flex-1 bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold py-2.5 rounded-xl transition-all active:scale-95 shadow-lg shadow-rose-500/20">
                      Deny
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Quick Action */}
            <div className="bg-gradient-to-br from-indigo-600 to-indigo-800 rounded-2xl p-6 shadow-2xl shadow-indigo-500/20">
              <h3 className="text-white font-bold mb-2">Need Help?</h3>
              <p className="text-indigo-100 text-xs mb-4 leading-relaxed">Access the research paper and technical documentation to understand the safety kernel's decision logic.</p>
              <button className="w-full bg-white/10 hover:bg-white/20 text-white text-xs font-bold py-2.5 rounded-xl transition-colors">
                Open Documentation
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
