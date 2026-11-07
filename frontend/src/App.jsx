import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import ChatMessage from './components/ChatMessage';
import MetricsDrawer from './components/MetricsDrawer';
import { askQuestion, fetchHealth, fetchStats, fetchLogs } from './api';
import { Send, CornerDownLeft, Sparkles, AlertCircle } from 'lucide-react';

const SUGGESTIONS = [
  "What is Article 21 of the Indian Constitution?",
  "What exceptions does it have?",
  "Which article is right to education?",
  "Explain freedom of speech under Article 19.",
];

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        'Welcome. I am your Indian Constitution AI Assistant, accelerated by a Qdrant semantic cache. Ask any question about articles, fundamental rights, or legal provisions.',
      meta: null,
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Cache & telemetry controls
  const [threshold, setThreshold] = useState(0.90);
  const [dryRun, setDryRun] = useState(false);
  const [runTag, setRunTag] = useState('web_chat');

  // Backend telemetry state
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([]);
  const [isMetricsOpen, setIsMetricsOpen] = useState(false);

  const messagesEndRef = useRef(null);

  const refreshData = async () => {
    try {
      const [h, s, l] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchStats(runTag || null).catch(() => null),
        fetchLogs(30).catch(() => []),
      ]);
      setHealth(h);
      setStats(s);
      setLogs(l);
    } catch {
      // ignore background poll errors
    }
  };

  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 10000);
    return () => clearInterval(interval);
  }, [runTag]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (textToSend = null) => {
    const query = (textToSend || input).trim();
    if (!query || loading) return;

    setError(null);
    setInput('');

    // Append user message
    const userMsg = { role: 'user', content: query };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      // Build conversation history from prior messages (excluding initial greeting)
      const historyTurns = messages
        .filter((_, idx) => idx > 0)
        .map((m) => ({ role: m.role, content: m.content }));

      const res = await askQuestion({
        question: query,
        history: historyTurns,
        threshold,
        runTag: runTag || 'web_chat',
        dryRun,
      });

      const assistantMsg = {
        role: 'assistant',
        content: res.answer || (dryRun ? '[Dry Run: Cache Miss - No LLM invoked]' : 'No answer generated.'),
        meta: {
          standalone_question: res.standalone_question,
          cache_hit: res.cache_hit,
          similarity: res.similarity,
          matched_question: res.matched_question,
          sources: res.sources,
          latency_ms: res.latency_ms,
          input_tokens: res.input_tokens,
          output_tokens: res.output_tokens,
        },
      };

      setMessages((prev) => [...prev, assistantMsg]);
      refreshData();
    } catch (err) {
      setError(err.message || 'Failed to get answer from API backend.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleResetChat = () => {
    setMessages([
      {
        role: 'assistant',
        content: 'Conversation history reset. The semantic cache remains active for standalone queries.',
        meta: null,
      },
    ]);
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-slate-950 text-slate-100 overflow-hidden font-sans">
      <Header
        health={health}
        threshold={threshold}
        onResetChat={handleResetChat}
        isMetricsOpen={isMetricsOpen}
        setIsMetricsOpen={setIsMetricsOpen}
      />

      <div className="flex-1 flex overflow-hidden relative">
        {/* Main Chat Flow */}
        <div className="flex-1 flex flex-col h-full max-w-4xl mx-auto w-full px-4">
          {/* Scrollable messages container */}
          <div className="flex-1 overflow-y-auto py-6 px-1 space-y-2">
            {messages.map((msg, idx) => (
              <ChatMessage key={idx} message={msg} />
            ))}

            {loading && (
              <div className="flex items-center gap-2 text-xs font-mono text-slate-400 bg-slate-900 border border-slate-800 p-3 rounded-lg max-w-sm">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                <span>Checking semantic cache & retrieving context...</span>
              </div>
            )}

            {error && (
              <div className="flex items-center gap-2 text-xs font-mono text-rose-300 bg-rose-950/40 border border-rose-900/60 p-3 rounded-lg">
                <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Suggestions (if only greeting present) */}
          {messages.length <= 1 && (
            <div className="pb-3 flex flex-wrap gap-2 justify-center">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(s)}
                  className="text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 hover:border-slate-700 px-3 py-1.5 rounded-full transition font-mono flex items-center gap-1.5"
                >
                  <Sparkles className="w-3 h-3 text-slate-400" />
                  <span>{s}</span>
                </button>
              ))}
            </div>
          )}

          {/* Input Box Footer */}
          <div className="pb-5 pt-2">
            <div className="bg-slate-900 border border-slate-800 focus-within:border-slate-700 rounded-xl p-2.5 flex flex-col gap-2 shadow-lg">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={2}
                placeholder="Ask about the Constitution of India (e.g., What is Article 21? What exceptions apply?)"
                className="w-full bg-transparent text-sm text-slate-100 placeholder-slate-500 focus:outline-none resize-none px-2"
              />

              <div className="flex items-center justify-between border-t border-slate-800/80 pt-2 px-1 text-xs text-slate-500 font-mono">
                <div className="flex items-center gap-2">
                  {dryRun && (
                    <span className="text-amber-400 bg-amber-950/60 border border-amber-800 px-1.5 py-0.5 rounded text-[10px]">
                      DRY RUN ACTIVE
                    </span>
                  )}
                  <span>Shift + Enter for new line</span>
                </div>

                <button
                  onClick={() => handleSend()}
                  disabled={!input.trim() || loading}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded font-sans text-xs font-medium transition ${
                    input.trim() && !loading
                      ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm'
                      : 'bg-slate-800 text-slate-500 cursor-not-allowed'
                  }`}
                >
                  <span>Send</span>
                  <CornerDownLeft className="w-3 h-3" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Telemetry & Cache Controls Drawer */}
        <MetricsDrawer
          isOpen={isMetricsOpen}
          onClose={() => setIsMetricsOpen(false)}
          stats={stats}
          logs={logs}
          onRefreshStats={refreshData}
          threshold={threshold}
          setThreshold={setThreshold}
          dryRun={dryRun}
          setDryRun={setDryRun}
          runTag={runTag}
          setRunTag={setRunTag}
        />
      </div>
    </div>
  );
}
