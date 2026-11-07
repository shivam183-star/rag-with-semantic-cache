import React from 'react';
import { Database, Activity, Sliders, Shield, RotateCcw } from 'lucide-react';

export default function Header({
  health,
  threshold,
  onResetChat,
  isMetricsOpen,
  setIsMetricsOpen,
}) {
  return (
    <header className="h-14 border-b border-slate-800 bg-slate-900/90 px-4 flex items-center justify-between select-none">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-slate-800 border border-slate-700 rounded flex items-center justify-center text-slate-200">
            <Shield className="w-4 h-4 text-slate-300" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm tracking-tight text-slate-100">Constitution AI</span>
              <span className="text-[10px] font-mono uppercase bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded border border-slate-700/60">
                Semantic Cache
              </span>
            </div>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-2 pl-4 border-l border-slate-800 text-xs text-slate-400">
          <span className="inline-flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${health ? 'bg-emerald-500' : 'bg-rose-500'}`} />
            {health ? 'API Ready' : 'Connecting...'}
          </span>
          <span className="text-slate-600">&middot;</span>
          <span className="font-mono text-slate-300 flex items-center gap-1">
            <Database className="w-3 h-3 text-slate-500" />
            {health?.docs_chunks ?? 0} Chunks
          </span>
          <span className="text-slate-600">&middot;</span>
          <span className="font-mono text-slate-300">
            {health?.cache_entries ?? 0} Cached Entries
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="hidden sm:flex items-center gap-1.5 bg-slate-950 border border-slate-800 px-2.5 py-1 rounded text-xs font-mono text-slate-300">
          <span className="text-slate-500">Threshold:</span>
          <span className="text-emerald-400 font-semibold">{threshold.toFixed(2)}</span>
        </div>

        <button
          onClick={onResetChat}
          title="Reset conversation"
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-transparent hover:border-slate-700 rounded transition"
        >
          <RotateCcw className="w-4 h-4" />
        </button>

        <button
          onClick={() => setIsMetricsOpen(!isMetricsOpen)}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border transition ${
            isMetricsOpen
              ? 'bg-slate-800 text-white border-slate-600'
              : 'bg-slate-900 text-slate-300 border-slate-700 hover:bg-slate-800 hover:text-white'
          }`}
        >
          <Activity className="w-3.5 h-3.5 text-emerald-400" />
          <span>Telemetry & Controls</span>
        </button>
      </div>
    </header>
  );
}
