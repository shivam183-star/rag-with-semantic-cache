import React, { useState } from 'react';
import { X, RefreshCw, Trash2, Scissors, Gauge, Zap, Clock, Coins, Layers } from 'lucide-react';
import { clearCache, pruneCache } from '../api';

export default function MetricsDrawer({
  isOpen,
  onClose,
  stats,
  logs,
  onRefreshStats,
  threshold,
  setThreshold,
  dryRun,
  setDryRun,
  runTag,
  setRunTag,
}) {
  const [actionMsg, setActionMsg] = useState(null);
  const [isActing, setIsActing] = useState(false);

  if (!isOpen) return null;

  const handleClear = async () => {
    if (!window.confirm('Are you sure you want to completely clear the semantic cache?')) return;
    setIsActing(true);
    try {
      await clearCache();
      setActionMsg('Cache cleared successfully.');
      onRefreshStats();
    } catch (e) {
      setActionMsg(`Failed to clear: ${e.message}`);
    } finally {
      setIsActing(false);
      setTimeout(() => setActionMsg(null), 3000);
    }
  };

  const handlePrune = async () => {
    setIsActing(true);
    try {
      const res = await pruneCache();
      setActionMsg(`Pruned ${res.pruned_entries} expired entries.`);
      onRefreshStats();
    } catch (e) {
      setActionMsg(`Failed to prune: ${e.message}`);
    } finally {
      setIsActing(false);
      setTimeout(() => setActionMsg(null), 3000);
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-xl bg-slate-900 border-l border-slate-800 shadow-2xl z-50 flex flex-col font-sans">
      {/* Header */}
      <div className="h-14 border-b border-slate-800 px-5 flex items-center justify-between bg-slate-950">
        <div className="flex items-center gap-2">
          <Gauge className="w-4 h-4 text-emerald-400" />
          <h2 className="font-semibold text-sm text-slate-100 tracking-tight">Telemetry & Cache Controls</h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onRefreshStats}
            title="Refresh statistics"
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {actionMsg && (
        <div className="bg-slate-800 border-b border-slate-700 px-4 py-2 text-xs font-mono text-emerald-300">
          {actionMsg}
        </div>
      )}

      {/* Body scroll */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6 text-slate-300 text-xs">
        {/* KPI Cards */}
        <div>
          <span className="text-[11px] font-mono uppercase text-slate-400 font-semibold tracking-wider block mb-3">
            Real-Time Performance Metrics
          </span>
          <div className="grid grid-cols-2 gap-3">
            {/* Card 1: Hit Rate */}
            <div className="bg-slate-950 border border-slate-800 p-3 rounded-lg">
              <div className="flex items-center justify-between text-slate-400 mb-1">
                <span>Cache Hit Rate</span>
                <Zap className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <div className="text-xl font-mono font-bold text-white">
                {stats ? `${(stats.hit_rate * 100).toFixed(1)}%` : '--'}
              </div>
              <div className="text-[11px] text-slate-500 font-mono mt-1">
                {stats?.hits ?? 0} hits / {stats?.total_requests ?? 0} requests
              </div>
            </div>

            {/* Card 2: Latency Drop */}
            <div className="bg-slate-950 border border-slate-800 p-3 rounded-lg">
              <div className="flex items-center justify-between text-slate-400 mb-1">
                <span>Latency Reduction</span>
                <Clock className="w-3.5 h-3.5 text-blue-400" />
              </div>
              <div className="text-xl font-mono font-bold text-emerald-400">
                {stats?.latency_reduction_pct ? `-${stats.latency_reduction_pct}%` : '--'}
              </div>
              <div className="text-[11px] text-slate-500 font-mono mt-1">
                Avg: {stats?.avg_latency_ms_hit ? `${Math.round(stats.avg_latency_ms_hit)}ms` : '--'} vs{' '}
                {stats?.avg_latency_ms_miss ? `${Math.round(stats.avg_latency_ms_miss)}ms` : '--'}
              </div>
            </div>

            {/* Card 3: Tokens Saved */}
            <div className="bg-slate-950 border border-slate-800 p-3 rounded-lg">
              <div className="flex items-center justify-between text-slate-400 mb-1">
                <span>Tokens Saved</span>
                <Coins className="w-3.5 h-3.5 text-amber-400" />
              </div>
              <div className="text-xl font-mono font-bold text-white">
                {stats?.estimated_tokens_saved?.toLocaleString() ?? 0}
              </div>
              <div className="text-[11px] text-slate-500 font-mono mt-1">
                Avoided LLM cost on hits
              </div>
            </div>

            {/* Card 4: p95 Latency */}
            <div className="bg-slate-950 border border-slate-800 p-3 rounded-lg">
              <div className="flex items-center justify-between text-slate-400 mb-1">
                <span>p95 Latency</span>
                <Layers className="w-3.5 h-3.5 text-slate-400" />
              </div>
              <div className="text-lg font-mono font-bold text-slate-200">
                {stats?.p95_latency_ms_hit ? `${Math.round(stats.p95_latency_ms_hit)}ms` : '--'} /{' '}
                <span className="text-slate-500">{stats?.p95_latency_ms_miss ? `${Math.round(stats.p95_latency_ms_miss)}ms` : '--'}</span>
              </div>
              <div className="text-[11px] text-slate-500 font-mono mt-1">
                Hit vs Miss p95
              </div>
            </div>
          </div>
        </div>

        {/* Runtime Controls */}
        <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg space-y-4">
          <span className="text-[11px] font-mono uppercase text-slate-400 font-semibold tracking-wider block">
            Cache Tuning Parameters
          </span>

          {/* Threshold Control */}
          <div className="space-y-2">
            <div className="flex justify-between items-center font-mono">
              <label htmlFor="threshold-slider" className="text-slate-300">Similarity Threshold:</label>
              <span className="text-emerald-400 font-bold bg-slate-900 border border-slate-800 px-2 py-0.5 rounded">
                {threshold.toFixed(2)}
              </span>
            </div>
            <input
              id="threshold-slider"
              type="range"
              min="0.50"
              max="0.99"
              step="0.01"
              value={threshold}
              onChange={(e) => setThreshold(parseFloat(e.target.value))}
              className="w-full accent-emerald-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
            />
            <div className="flex gap-1.5 justify-end pt-1">
              {[0.80, 0.85, 0.90, 0.95].map((val) => (
                <button
                  key={val}
                  onClick={() => setThreshold(val)}
                  className={`px-2 py-0.5 rounded font-mono text-[10px] border ${
                    threshold === val
                      ? 'bg-emerald-950 text-emerald-300 border-emerald-700 font-bold'
                      : 'bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-800'
                  }`}
                >
                  {val.toFixed(2)}
                </button>
              ))}
            </div>
          </div>

          {/* Toggle Switches & Tags */}
          <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
            <div>
              <div className="font-medium text-slate-200">Dry Run Mode</div>
              <div className="text-slate-500 text-[11px]">Probe cache without calling LLM or caching</div>
            </div>
            <button
              onClick={() => setDryRun(!dryRun)}
              className={`w-10 h-5 rounded-full p-0.5 transition ${
                dryRun ? 'bg-amber-500' : 'bg-slate-800 border border-slate-700'
              }`}
            >
              <div
                className={`w-4 h-4 rounded-full bg-white transition-transform ${
                  dryRun ? 'translate-x-5' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          <div className="pt-2 border-t border-slate-800/80 space-y-1">
            <label htmlFor="eval-run-tag-input" className="text-slate-300 block font-mono text-[11px]">Evaluation Run Tag (optional):</label>
            <input
              id="eval-run-tag-input"
              type="text"
              value={runTag}
              onChange={(e) => setRunTag(e.target.value)}
              placeholder="e.g. baseline_eval_1"
              className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200 font-mono text-xs focus:outline-none focus:border-slate-600"
            />
          </div>

          {/* Cache Maintenance Buttons */}
          <div className="pt-3 border-t border-slate-800/80 flex gap-2">
            <button
              disabled={isActing}
              onClick={handlePrune}
              className="flex-1 flex items-center justify-center gap-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 px-3 py-1.5 rounded transition font-mono text-xs"
            >
              <Scissors className="w-3.5 h-3.5 text-amber-400" />
              <span>Prune Expired</span>
            </button>
            <button
              disabled={isActing}
              onClick={handleClear}
              className="flex-1 flex items-center justify-center gap-1.5 bg-rose-950/40 hover:bg-rose-950/70 border border-rose-900/60 text-rose-300 px-3 py-1.5 rounded transition font-mono text-xs"
            >
              <Trash2 className="w-3.5 h-3.5 text-rose-400" />
              <span>Clear Cache</span>
            </button>
          </div>
        </div>

        {/* Recent Request Logs */}
        <div>
          <span className="text-[11px] font-mono uppercase text-slate-400 font-semibold tracking-wider block mb-2">
            Recent Query Logs ({logs?.length ?? 0})
          </span>
          <div className="border border-slate-800 rounded-lg overflow-hidden bg-slate-950 max-h-60 overflow-y-auto">
            <table className="w-full text-left font-mono text-[11px]">
              <thead className="bg-slate-900 border-b border-slate-800 text-slate-400">
                <tr>
                  <th className="py-2 px-2.5">ID</th>
                  <th className="py-2 px-2.5">Question</th>
                  <th className="py-2 px-2.5">Status</th>
                  <th className="py-2 px-2.5">Score</th>
                  <th className="py-2 px-2.5 text-right">Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-900 text-slate-300">
                {logs && logs.length > 0 ? (
                  logs.map((row) => (
                    <tr key={row.id} className="hover:bg-slate-900/50">
                      <td className="py-1.5 px-2.5 text-slate-500">{row.id}</td>
                      <td className="py-1.5 px-2.5 truncate max-w-[160px]" title={row.question}>
                        {row.question}
                      </td>
                      <td className="py-1.5 px-2.5">
                        {row.cache_hit ? (
                          <span className="text-emerald-400 font-semibold">HIT</span>
                        ) : (
                          <span className="text-slate-500">MISS</span>
                        )}
                      </td>
                      <td className="py-1.5 px-2.5 text-slate-400">
                        {row.similarity ? row.similarity.toFixed(3) : '--'}
                      </td>
                      <td className="py-1.5 px-2.5 text-right font-mono text-slate-400">
                        {Math.round(row.latency_ms)}ms
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="py-4 text-center text-slate-600">
                      No logs available yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
