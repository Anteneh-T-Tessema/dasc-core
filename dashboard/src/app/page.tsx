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
  RefreshCcw,
  User,
  Clock,
  ChevronRight,
  FileJson,
  Check,
  X,
  History,
  Info,
  Layers,
  CheckSquare
} from 'lucide-react';

const API_BASE = typeof window !== 'undefined' 
  ? (window.location.port === '3000' ? 'http://localhost:8000' : '') 
  : 'http://localhost:8000';

export default function DASCDashboard() {
  const [stats, setStats] = useState({ total: 0, commits: 0, rejections: 0, escalations: 0 });
  const [history, setHistory] = useState<any[]>([]);
  const [integrity, setIntegrity] = useState({ status: 'connecting', valid: true });
  const [asOf, setAsOf] = useState('');
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [selectedRecord, setSelectedRecord] = useState<any>(null);
  const [isVerifyingIntegrity, setIsVerifyingIntegrity] = useState(false);
  const [integrityAlert, setIntegrityAlert] = useState<string | null>(null);

  const fetchData = async (targetAsOf = asOf) => {
    try {
      const ledgerUrl = targetAsOf ? `${API_BASE}/ledger?as_of=${encodeURIComponent(targetAsOf)}` : `${API_BASE}/ledger`;
      const headers = { 'X-API-KEY': 'dasc-dev-key-123' };
      const [statsRes, historyRes] = await Promise.all([
        fetch(`${API_BASE}/stats`, { headers }),
        fetch(ledgerUrl, { headers })
      ]);
      const statsData = await statsRes.json();
      const historyData = await historyRes.json();
      
      setStats(statsData);
      setHistory(historyData);
    } catch (err) {
      console.error("Failed to fetch DASC data:", err);
    }
  };

  const verifyIntegrity = async () => {
    setIsVerifyingIntegrity(true);
    setIntegrityAlert(null);
    try {
      const headers = { 'X-API-KEY': 'dasc-dev-key-123' };
      const res = await fetch(`${API_BASE}/integrity`, { headers });
      const data = await res.json();
      setIntegrity(prev => ({ ...prev, valid: data.valid }));
      if (data.valid) {
        setIntegrityAlert("INTEGRITY_OK: All cryptographic hashes match. Ledger chain is untampered.");
      } else {
        setIntegrityAlert("WARNING: Cryptographic mismatch detected in ledger. Chain integrity has been compromised!");
      }
    } catch (err) {
      console.error("Integrity check failed:", err);
      setIntegrityAlert("ERROR: Failed to connect to safety kernel for integrity verification.");
    } finally {
      setIsVerifyingIntegrity(false);
      setTimeout(() => setIntegrityAlert(null), 5000);
    }
  };

  const handleApproval = async (intent_id: string, approved: boolean) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: approved ? "APPROVE" : "DENY",
        intent_id,
        approver: "DASC_ADMIN_WS"
      }));
    } else {
      try {
        await fetch(`${API_BASE}/approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-API-KEY': 'dasc-dev-key-123' },
          body: JSON.stringify({
            intent_id,
            approved,
            approver_id: "DASC_ADMIN_CONSOLE"
          })
        });
        fetchData(); // Refresh
      } catch (err) {
        console.error("Approval failed:", err);
      }
    }
  };

  useEffect(() => {
    fetchData();

    // Establish WebSocket connection
    const wsUrl = API_BASE 
      ? API_BASE.replace(/^http/, 'ws') + '/ws'
      : (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/ws';
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log("Connected to DASC WebSocket");
      setIntegrity(prev => ({ ...prev, status: 'connected' }));
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("DASC Real-Time Update:", data);
        fetchData();
      } catch (err) {
        console.error("Error parsing socket message:", err);
      }
    };

    socket.onclose = () => {
      console.log("Disconnected from DASC WebSocket");
      setIntegrity(prev => ({ ...prev, status: 'disconnected' }));
    };

    setWs(socket);

    // Fallback polling in case of websocket failure
    const interval = setInterval(() => {
      fetchData();
    }, 5000);

    return () => {
      socket.close();
      clearInterval(interval);
    };
  }, [asOf]);

  // Find the latest status for each intent_id to avoid showing resolved escalations
  const latestStatuses: { [key: string]: string } = {};
  history.forEach((h: any) => {
    if (!latestStatuses[h.intent_id]) {
      latestStatuses[h.intent_id] = h.status;
    }
  });

  const pendingEscalations = history.filter((h: any) => {
    return h.status === 'ESCALATE' && latestStatuses[h.intent_id] === 'ESCALATE';
  });

  // Helper to safely parse JSON content for display
  const parseJsonField = (jsonStr: string) => {
    try {
      return JSON.parse(jsonStr);
    } catch {
      return {};
    }
  };

  return (
    <div className="min-h-screen bg-[#060608] text-slate-200 font-sans selection:bg-indigo-500/30 pb-20">
      {/* Header */}
      <header className="border-b border-slate-800/80 bg-[#060608]/80 backdrop-blur-xl sticky top-0 z-40 transition-all duration-300">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 bg-gradient-to-tr from-indigo-600 to-indigo-500 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/25 relative overflow-hidden group">
              <ShieldCheck className="text-white w-6 h-6 z-10 transition-transform group-hover:scale-110" />
              <div className="absolute inset-0 bg-gradient-to-tr from-violet-600 to-indigo-600 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                DASC <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-violet-400 font-semibold">Control Plane</span>
              </h1>
              <p className="text-[10px] uppercase tracking-[0.25em] text-slate-500 font-extrabold">Deterministic Safety Boundary</p>
            </div>
          </div>
          
          <div className="flex items-center gap-5">
            {/* Time Travel */}
            <div className="flex items-center gap-2.5 bg-[#0f0f13] border border-slate-800/80 rounded-xl px-3.5 py-1.5 text-xs focus-within:border-indigo-500/50 transition-all duration-200">
              <History className="w-4 h-4 text-indigo-400" />
              <span className="text-slate-400 font-semibold text-[10px] uppercase tracking-wider hidden md:inline">Time Travel:</span>
              <input 
                type="datetime-local" 
                className="bg-transparent border-0 text-slate-300 outline-none cursor-pointer focus:ring-0 text-xs [color-scheme:dark] w-40" 
                onChange={(e) => {
                  if (e.target.value) {
                    const iso = new Date(e.target.value).toISOString();
                    setAsOf(iso);
                  } else {
                    setAsOf('');
                  }
                }}
              />
            </div>
            
            {/* Connection Status & Integrity Trigger */}
            <button 
              onClick={verifyIntegrity}
              disabled={isVerifyingIntegrity}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl border transition-all active:scale-98 ${
                integrity.valid 
                  ? 'bg-emerald-500/5 hover:bg-emerald-500/10 border-emerald-500/20 text-emerald-400' 
                  : 'bg-rose-500/5 hover:bg-rose-500/10 border-rose-500/20 text-rose-400'
              } text-xs font-semibold`}
            >
              <Lock className={`w-3.5 h-3.5 ${isVerifyingIntegrity ? 'animate-spin' : ''}`} />
              <span className="relative flex h-2 w-2 mr-1">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${integrity.status === 'connected' ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                <span className={`relative inline-flex rounded-full h-2 w-2 ${integrity.status === 'connected' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              </span>
              Audit Integrity
            </button>

            <button onClick={() => fetchData()} className="text-slate-400 hover:text-white hover:bg-slate-800/40 p-2 rounded-xl border border-transparent hover:border-slate-800/80 transition-all duration-200">
              <RefreshCcw className="w-4.5 h-4.5" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Integrity Validation Overlay Notification */}
        {integrityAlert && (
          <div className={`border rounded-2xl p-4.5 mb-6 flex items-start gap-3.5 animate-in fade-in slide-in-from-top-4 duration-300 ${
            integrityAlert.includes('OK') 
              ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-300' 
              : 'bg-rose-950/20 border-rose-500/30 text-rose-300'
          }`}>
            <ShieldCheck className="w-5.5 h-5.5 mt-0.5 shrink-0" />
            <div>
              <p className="font-bold text-sm">Ledger Verification Status</p>
              <p className="text-xs opacity-90 mt-0.5">{integrityAlert}</p>
            </div>
          </div>
        )}

        {/* Time Travel Banner */}
        {asOf && (
          <div className="bg-amber-500/10 border border-amber-500/25 rounded-2xl p-4.5 mb-8 flex items-center justify-between text-amber-400 text-sm animate-pulse">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0" />
              <span><strong>Bitemporal Time Travel Active:</strong> Querying ledger state records history slice as of <strong className="text-white underline">{new Date(asOf).toLocaleString()}</strong></span>
            </div>
            <button 
              onClick={() => {
                setAsOf('');
                const inputEl = document.querySelector('input[type="datetime-local"]') as HTMLInputElement;
                if (inputEl) inputEl.value = '';
              }}
              className="bg-amber-500/20 hover:bg-amber-500/30 text-white font-bold px-3 py-1.5 rounded-lg text-xs transition-all duration-200 border border-amber-500/30"
            >
              Reset to Live
            </button>
          </div>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
          {[
            { label: 'Total Intents', value: stats.total, icon: Activity, colorClass: 'text-indigo-400', bgClass: 'bg-indigo-500/10' },
            { label: 'Commits', value: stats.commits, icon: CheckCircle2, colorClass: 'text-emerald-400', bgClass: 'bg-emerald-500/10' },
            { label: 'Rejections', value: stats.rejections, icon: XCircle, colorClass: 'text-rose-400', bgClass: 'bg-rose-500/10' },
            { label: 'Escalations', value: stats.escalations, icon: AlertTriangle, colorClass: 'text-amber-400', bgClass: 'bg-amber-500/10' },
          ].map((stat, i) => (
            <div key={i} className="bg-[#0f0f13]/60 backdrop-blur-md border border-slate-800/80 rounded-2xl p-6 hover:border-indigo-500/50 hover:shadow-[0_0_20px_rgba(99,102,241,0.08)] transition-all duration-300">
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm font-semibold text-slate-400 tracking-tight">{stat.label}</p>
                <div className={`p-2 rounded-xl ${stat.bgClass}`}>
                  <stat.icon className={`w-5 h-5 ${stat.colorClass}`} />
                </div>
              </div>
              <p className="text-3.5xl font-extrabold text-white tracking-tight">{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Main Content Split */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10 items-start">
          {/* Ledger Table */}
          <div className="lg:col-span-2 space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
                <Database className="w-5 h-5 text-indigo-400" />
                Ledger Operations
              </h2>
              <div className="text-xs text-slate-500 flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5" />
                Click row to inspect cryptographic envelope
              </div>
            </div>

            <div className="bg-[#0f0f13]/80 backdrop-blur-md border border-slate-800/80 rounded-2xl overflow-hidden shadow-xl shadow-black/10">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800/80 bg-slate-900/40">
                      <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Intent ID</th>
                      <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Actor Agent</th>
                      <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Status</th>
                      <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Timestamp</th>
                      <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest text-right">Inspect</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-850">
                    {history.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-6 py-12 text-center text-slate-500 italic">
                          No ledger records found.
                        </td>
                      </tr>
                    ) : (
                      history.map((row: any, i) => (
                        <tr 
                          key={i} 
                          onClick={() => setSelectedRecord(row)}
                          className={`hover:bg-slate-800/35 transition-all duration-200 cursor-pointer group ${
                            selectedRecord?.intent_id === row.intent_id ? 'bg-[#151522]/60 border-l-2 border-indigo-500' : ''
                          }`}
                        >
                          <td className="px-6 py-4">
                            <span className="font-mono text-indigo-400 text-sm font-medium">{row.intent_id}</span>
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-2">
                              <div className="w-5.5 h-5.5 bg-slate-800/60 rounded-md flex items-center justify-center text-[10px] text-slate-400 font-bold uppercase border border-slate-700/40">
                                {row.actor_agent.slice(0, 2)}
                              </div>
                              <span className="text-slate-200 text-sm font-medium">{row.actor_agent}</span>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <span className={`px-2.5 py-1 rounded-lg text-[10px] font-extrabold tracking-wider uppercase border ${
                              row.status === 'COMMIT' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                              row.status === 'REJECT' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                              'bg-amber-500/10 text-amber-400 border-amber-500/20'
                            }`}>
                              {row.status}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-slate-400 text-xs">
                            {new Date(row.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                          </td>
                          <td className="px-6 py-4 text-right">
                            <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-indigo-400 group-hover:translate-x-0.5 transition-all inline-block" />
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Sidebar / Active Escalations & Info */}
          <div className="space-y-6">
            <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
              <AlertTriangle className="w-5 h-5 text-amber-400 animate-pulse" />
              Pending Escalations
            </h2>
            
            <div className="space-y-4">
              {pendingEscalations.length === 0 && (
                <div className="text-sm text-slate-500 italic p-8 border border-dashed border-slate-800 rounded-2xl text-center bg-[#0a0a0d]/40">
                  No pending escalations requiring human oversight
                </div>
              )}
              {pendingEscalations.map((item: any, i) => {
                const intentPayload = parseJsonField(item.intent_json);
                return (
                  <div key={i} className="bg-[#0f0f13]/85 backdrop-blur-md border border-amber-500/25 rounded-2xl p-5.5 space-y-4 relative overflow-hidden group shadow-lg shadow-amber-500/3">
                    <div className="absolute top-0 right-0 p-2.5 bg-amber-500/15 rounded-bl-2xl text-amber-400 border-l border-b border-amber-500/20">
                      <AlertTriangle className="w-4 h-4" />
                    </div>
                    
                    <div>
                      <p className="text-[9px] uppercase tracking-[0.2em] text-amber-400 font-extrabold mb-1">Human Oversight Needed</p>
                      <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                        <Layers className="w-4 h-4 text-slate-400" />
                        {intentPayload.action_type || 'ADMIN_ACTION'}
                      </h3>
                    </div>
                    
                    <div className="text-xs space-y-1.5 text-slate-400 bg-slate-950/60 p-3.5 rounded-xl font-mono border border-slate-850">
                      <div><span className="text-indigo-400">intent_id:</span> "{item.intent_id}"</div>
                      <div><span className="text-indigo-400">agent:</span> "{item.actor_agent}"</div>
                      <div><span className="text-indigo-400">target:</span> "{intentPayload.target_artifact}"</div>
                      {intentPayload.risk_tier && <div><span className="text-indigo-400">risk_tier:</span> {intentPayload.risk_tier}</div>}
                    </div>

                    <div className="flex gap-2.5 pt-1">
                      <button 
                        onClick={() => handleApproval(item.intent_id, true)}
                        className="flex-1 bg-emerald-600 hover:bg-emerald-500 active:scale-97 text-white text-xs font-bold py-2.5 rounded-xl transition-all shadow-lg shadow-emerald-500/10 flex items-center justify-center gap-1.5 cursor-pointer"
                      >
                        <Check className="w-4 h-4" /> Approve
                      </button>
                      <button 
                        onClick={() => handleApproval(item.intent_id, false)}
                        className="flex-1 bg-rose-600 hover:bg-rose-500 active:scale-97 text-white text-xs font-bold py-2.5 rounded-xl transition-all shadow-lg shadow-rose-500/10 flex items-center justify-center gap-1.5 cursor-pointer"
                      >
                        <X className="w-4 h-4" /> Deny
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Quick Action Info Panel */}
            <div className="bg-gradient-to-br from-indigo-950/30 to-indigo-900/15 border border-indigo-500/20 rounded-2xl p-5.5 relative overflow-hidden">
              <div className="absolute -right-10 -bottom-10 w-28 h-28 bg-indigo-500/10 rounded-full blur-2xl" />
              <h3 className="text-white text-sm font-bold mb-2 flex items-center gap-1.5">
                <ShieldCheck className="w-4.5 h-4.5 text-indigo-400" />
                Centralized Safety Boundary
              </h3>
              <p className="text-slate-400 text-xs mb-4.5 leading-relaxed">
                DASC operates a centralized validation boundary verifying agent intents using information flow control, optimistic concurrency version check verification, and custom policy rulesets.
              </p>
              <a 
                href="https://github.com/Anteneh-T-Tessema/dasc-core" 
                target="_blank" 
                rel="noreferrer" 
                className="w-full bg-[#0d0d12]/80 hover:bg-[#0d0d12]/100 text-slate-200 text-xs font-bold py-2.5 rounded-xl transition-colors border border-slate-800/80 inline-flex items-center justify-center gap-1.5"
              >
                Inspect Source Repository <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>
        </div>

        {/* Selected Record Inspection Modal/Overlay Panel */}
        {selectedRecord && (
          <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div 
              className="w-full max-w-xl h-full bg-[#0a0a0d] border-l border-slate-800/80 shadow-2xl p-6.5 overflow-y-auto flex flex-col animate-in slide-in-from-right duration-300"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-4.5 mb-5 shrink-0">
                <div className="flex items-center gap-2">
                  <FileJson className="w-5 h-5 text-indigo-400" />
                  <h3 className="text-base font-bold text-white">Cryptographic Safety Envelope</h3>
                </div>
                <button 
                  onClick={() => setSelectedRecord(null)}
                  className="text-slate-400 hover:text-white bg-slate-800/40 p-1.5 rounded-lg border border-slate-700/20 transition-all cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="flex-1 space-y-5.5">
                {/* Meta details */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[#0f0f13] border border-slate-800/60 p-3.5 rounded-xl">
                    <p className="text-[10px] uppercase text-slate-500 font-bold tracking-wider mb-1">Intent ID</p>
                    <p className="text-sm font-mono text-white font-semibold">{selectedRecord.intent_id}</p>
                  </div>
                  <div className="bg-[#0f0f13] border border-slate-800/60 p-3.5 rounded-xl">
                    <p className="text-[10px] uppercase text-slate-500 font-bold tracking-wider mb-1">Evaluation Status</p>
                    <span className={`inline-block px-2.5 py-0.5 rounded-md text-[10px] font-extrabold tracking-wider uppercase border mt-1 ${
                      selectedRecord.status === 'COMMIT' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                      selectedRecord.status === 'REJECT' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                      'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}>
                      {selectedRecord.status}
                    </span>
                  </div>
                </div>

                <div className="space-y-2">
                  <p className="text-xs font-bold text-slate-400 flex items-center gap-1.5">
                    <User className="w-4 h-4 text-indigo-400" /> Intent Submitter
                  </p>
                  <div className="bg-[#0f0f13] border border-slate-800/60 p-3.5 rounded-xl text-sm font-medium text-slate-200">
                    Agent ID: <span className="text-white font-mono">{selectedRecord.actor_agent}</span>
                  </div>
                </div>

                {/* Intent JSON parsed */}
                <div className="space-y-2">
                  <p className="text-xs font-bold text-slate-400 flex items-center gap-1.5">
                    <Clock className="w-4 h-4 text-indigo-400" /> Bitemporal Timestamp
                  </p>
                  <div className="bg-[#0f0f13] border border-slate-800/60 p-3.5 rounded-xl text-sm text-slate-300">
                    {new Date(selectedRecord.timestamp).toLocaleString()}
                  </div>
                </div>

                {/* Reason Codes */}
                <div className="space-y-2">
                  <p className="text-xs font-bold text-slate-400 flex items-center gap-1.5">
                    <AlertTriangle className="w-4 h-4 text-indigo-400" /> Evaluation Violations & Reason Codes
                  </p>
                  <div className="bg-[#0f0f13] border border-slate-800/60 p-4 rounded-xl space-y-2">
                    {parseJsonField(selectedRecord.reason_codes).length === 0 ? (
                      <p className="text-xs text-emerald-400 font-semibold flex items-center gap-1">
                        <CheckSquare className="w-4 h-4" /> Passed all safety policy checks. No violations.
                      </p>
                    ) : (
                      parseJsonField(selectedRecord.reason_codes).map((code: string, idx: number) => (
                        <div key={idx} className="text-xs text-rose-400 font-mono bg-rose-500/5 p-2 rounded-lg border border-rose-500/10 flex items-start gap-2">
                          <span className="font-bold text-rose-500 mt-0.5">•</span>
                          <span>{code}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Cryptographic Ledger Hashes */}
                <div className="space-y-2">
                  <p className="text-xs font-bold text-slate-400 flex items-center gap-1.5">
                    <Lock className="w-4 h-4 text-indigo-400" /> Cryptographic Signatures
                  </p>
                  <div className="bg-[#0f0f13] border border-slate-800/60 p-4 rounded-xl space-y-3 font-mono text-xs text-slate-400">
                    <div>
                      <span className="text-slate-500 block text-[9px] uppercase font-bold tracking-wider mb-0.5">Previous Signature Hash</span>
                      <span className="text-slate-300 break-all select-all bg-slate-900/50 p-2 rounded-lg border border-slate-850 block mt-1">{selectedRecord.previous_hash}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[9px] uppercase font-bold tracking-wider mb-0.5">Record Signature Hash</span>
                      <span className="text-slate-300 break-all select-all bg-slate-900/50 p-2 rounded-lg border border-slate-850 block mt-1">{selectedRecord.record_hash}</span>
                    </div>
                  </div>
                </div>

                {/* Raw JSON Details */}
                <div className="space-y-2">
                  <p className="text-xs font-bold text-slate-400 flex items-center gap-1.5">
                    <FileJson className="w-4 h-4 text-indigo-400" /> Raw Intent payload
                  </p>
                  <div className="bg-[#0f0f13] border border-slate-800/60 rounded-xl overflow-hidden">
                    <pre className="text-xs text-slate-300 p-4 font-mono overflow-x-auto max-h-60 bg-slate-950/60 select-text">
                      {JSON.stringify(parseJsonField(selectedRecord.intent_json), null, 2)}
                    </pre>
                  </div>
                </div>
              </div>

              <div className="border-t border-slate-800/80 pt-4.5 mt-6 shrink-0">
                <button 
                  onClick={() => setSelectedRecord(null)}
                  className="w-full bg-slate-800 hover:bg-slate-700 text-white font-bold py-3 rounded-xl transition-colors cursor-pointer text-xs"
                >
                  Close Inspection
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
