import React, { useState } from 'react';
import { Zap, Cpu, Clock, Coins, ChevronDown, ChevronRight, BookOpen, Copy, Check } from 'lucide-react';

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (isUser) {
    return (
      <div className="flex justify-end my-4">
        <div className="max-w-2xl bg-slate-800 text-slate-100 border border-slate-700/80 rounded-lg px-4 py-2.5 shadow-sm">
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  const { meta } = message;

  return (
    <div className="flex flex-col my-4 max-w-3xl">
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 shadow-sm space-y-3">
        {/* Contextualized query pill (if rephrased) */}
        {meta?.standalone_question && (
          <div className="flex items-center gap-1.5 text-xs text-slate-400 bg-slate-950/70 border border-slate-800 px-2.5 py-1 rounded font-mono">
            <span className="text-slate-500 font-semibold uppercase text-[10px]">Contextualized:</span>
            <span className="text-slate-300 italic truncate">"{meta.standalone_question}"</span>
          </div>
        )}

        {/* Answer text */}
        <div className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap selection:bg-slate-700">
          {message.content}
        </div>

        {/* Performance & Cache Telemetry Bar */}
        {meta && (
          <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
            <div className="flex items-center gap-2">
              {meta.cache_hit ? (
                <span className="inline-flex items-center gap-1 bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 px-2 py-0.5 rounded text-[11px] font-semibold">
                  <Zap className="w-3 h-3 fill-emerald-400" />
                  CACHE HIT
                  {meta.similarity && (
                    <span className="text-emerald-300/80 font-normal">
                      ({(meta.similarity * 100).toFixed(1)}% match)
                    </span>
                  )}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 bg-slate-800 text-slate-300 border border-slate-700 px-2 py-0.5 rounded text-[11px] font-semibold">
                  <Cpu className="w-3 h-3 text-slate-400" />
                  LLM GENERATION
                </span>
              )}

              <span className="inline-flex items-center gap-1 text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                <Clock className="w-3 h-3 text-slate-500" />
                {meta.latency_ms} ms
              </span>

              <span className="inline-flex items-center gap-1 text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                <Coins className="w-3 h-3 text-slate-500" />
                {meta.input_tokens + meta.output_tokens} tok
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleCopy}
                className="text-slate-400 hover:text-slate-200 p-1 rounded hover:bg-slate-800 transition"
                title="Copy response"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              </button>

              {meta.sources && meta.sources.length > 0 && (
                <button
                  onClick={() => setSourcesOpen(!sourcesOpen)}
                  className="flex items-center gap-1 text-slate-400 hover:text-slate-200 px-2 py-0.5 rounded hover:bg-slate-800 border border-transparent hover:border-slate-700 transition text-[11px]"
                >
                  <BookOpen className="w-3 h-3" />
                  <span>{meta.sources.length} Sources</span>
                  {sourcesOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                </button>
              )}
            </div>
          </div>
        )}

        {/* Collapsible Document Sources */}
        {sourcesOpen && meta?.sources && (
          <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-2">
            <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-400 block font-mono">
              Retrieved Context Snippets:
            </span>
            <div className="grid grid-cols-1 gap-2">
              {meta.sources.map((src, idx) => (
                <div key={idx} className="bg-slate-950 border border-slate-800 p-2.5 rounded text-xs">
                  <div className="flex items-center gap-2 mb-1">
                    {src.page && (
                      <span className="bg-slate-800 text-slate-300 font-mono text-[10px] px-1.5 py-0.5 rounded border border-slate-700">
                        Page {src.page}
                      </span>
                    )}
                    {src.article && (
                      <span className="bg-slate-800 text-slate-300 font-mono text-[10px] px-1.5 py-0.5 rounded border border-slate-700 font-semibold">
                        {src.article}
                      </span>
                    )}
                  </div>
                  <p className="text-slate-400 text-xs leading-relaxed font-mono whitespace-pre-wrap">
                    {src.snippet}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
