import React, { useEffect, useState } from 'react';
import { Activity, Radio, Cpu, ShieldCheck, AlertCircle } from 'lucide-react';
import { api } from '../../api/client';

export const Navbar: React.FC = () => {
  const [backendStatus, setBackendStatus] = useState<'online' | 'offline' | 'checking'>('checking');

  useEffect(() => {
    const check = async () => {
      try {
        const res = await api.checkHealth();
        setBackendStatus(res.status === 'ok' ? 'online' : 'offline');
      } catch {
        setBackendStatus('offline');
      }
    };
    check();
    const interval = setInterval(check, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 border-b border-white/10 bg-slate-900/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 ring-1 ring-white/20">
          <Radio className="w-5 h-5 text-white animate-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold text-white tracking-tight">LiDAR Performance Analysis Platform</h1>
            <span className="badge badge-cyan text-[10px]">SilvaLab / UF</span>
          </div>
          <p className="text-xs text-slate-400">Monte Carlo Simulation & Forest Inventory Assessment Engine</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-white/5 text-xs">
          <Cpu className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-slate-300 font-mono">Pydantic v2 Engine</span>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-white/5 text-xs">
          <Activity className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-slate-300">Backend API:</span>
          {backendStatus === 'online' ? (
            <span className="badge badge-emerald flex items-center gap-1 text-[11px]">
              <ShieldCheck className="w-3 h-3" /> Online
            </span>
          ) : backendStatus === 'offline' ? (
            <span className="badge badge-rose flex items-center gap-1 text-[11px]">
              <AlertCircle className="w-3 h-3" /> Offline
            </span>
          ) : (
            <span className="badge badge-amber text-[11px]">Checking...</span>
          )}
        </div>
      </div>
    </header>
  );
};
