const rawBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
let API_BASE = rawBase.trim().replace(/\/+$/, '');
API_BASE = API_BASE.replace(/\/(health|docs|ask|stats|logs)$/i, '');

export async function askQuestion({ question, history = [], threshold = null, runTag = 'web_chat', dryRun = false }) {
  const res = await fetch(`${API_BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      history,
      threshold: threshold ? parseFloat(threshold) : null,
      run_tag: runTag,
      dry_run: dryRun,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'API Error' }));
    throw new Error(err.detail || `Server error (${res.status})`);
  }
  return res.json();
}

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) {
      console.warn(`Health check failed with status ${res.status}`);
      throw new Error(`Health check failed with status ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error(`Failed to reach API at ${API_BASE}/health:`, err);
    throw err;
  }
}

export async function fetchStats(runTag = null) {
  const url = runTag ? `${API_BASE}/stats?run_tag=${encodeURIComponent(runTag)}` : `${API_BASE}/stats`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

export async function fetchLogs(limit = 20) {
  const res = await fetch(`${API_BASE}/logs?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch logs');
  return res.json();
}

export async function clearCache() {
  const res = await fetch(`${API_BASE}/cache/clear`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to clear cache');
  return res.json();
}

export async function pruneCache() {
  const res = await fetch(`${API_BASE}/cache/prune`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to prune cache');
  return res.json();
}
