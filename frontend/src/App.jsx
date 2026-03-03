import React, { useEffect, useState } from 'react'
import QueryInput from './components/QueryInput'
import AnswerPanel from './components/AnswerPanel'
import ResultsPanel from './components/ResultsPanel'

const API_BASE = '/api'

const FEATURES = [
  { id: null, label: 'GENERAL', hint: 'General search' },
  { id: 'explain', label: 'EXPLAIN', hint: 'Code explanation' },
  { id: 'dependencies', label: 'DEPENDENCIES', hint: 'Dependency mapping' },
  { id: 'patterns', label: 'PATTERNS', hint: 'Pattern detection' },
  { id: 'documentation', label: 'DOCS', hint: 'Documentation' },
  { id: 'business_logic', label: 'BUSINESS', hint: 'Business logic' },
]

function formatMenuTime(date) {
  const day = date.toLocaleDateString([], { weekday: 'short' })
  const month = date.toLocaleDateString([], { month: 'short' })
  const dayNum = date.getDate()
  const time = date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
  return `${day} ${month} ${dayNum} ${time}`
}

function App() {
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [feature, setFeature] = useState(null)
  const [timings, setTimings] = useState(null)
  const [health, setHealth] = useState(null)
  const [menuTime, setMenuTime] = useState(() => formatMenuTime(new Date()))

  const [showTerminal, setShowTerminal] = useState(true)
  const [isMinimized, setIsMinimized] = useState(false)
  const [isMaximized, setIsMaximized] = useState(false)
  const [showDonutWindow, setShowDonutWindow] = useState(false)

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch((err) => setHealth({ status: 'error', error: err.message }))
  }, [])

  useEffect(() => {
    const t = setInterval(() => setMenuTime(formatMenuTime(new Date())), 1000)
    return () => clearInterval(t)
  }, [])

  const handleQuery = async (queryText) => {
    setLoading(true)
    setError(null)
    setAnswer('')
    setSources([])
    setTimings(null)

    try {
      const response = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryText, feature, stream: true }),
      })

      if (!response.ok) {
        throw new Error(`Query failed: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let answerText = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value)
        const lines = text.split('\n').filter((l) => l.trim())

        for (const line of lines) {
          try {
            const data = JSON.parse(line)
            if (data.type === 'sources') {
              setSources(data.sources || [])
              setTimings((prev) => ({ ...prev, retrieval_ms: Math.round(data.retrieval_time_ms || 0) }))
            } else if (data.type === 'answer_chunk') {
              answerText += data.content
              setAnswer(answerText)
            } else if (data.type === 'done') {
              setTimings((prev) => ({ ...prev, total_ms: Math.round(data.total_time_ms || 0) }))
            }
          } catch (_) {
            // Ignore malformed partial line chunks
          }
        }
      }
    } catch (err) {
      try {
        const response = await fetch(`${API_BASE}/query`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: queryText, feature, stream: false }),
        })
        const data = await response.json()
        if (!response.ok) {
          throw new Error(data?.detail || data?.message || 'Query failed')
        }
        setAnswer(data.answer || '')
        setSources(data.sources || [])
        setTimings({
          retrieval_ms: Math.round(data.retrieval_time_ms || 0),
          total_ms: Math.round(data.total_time_ms || 0),
        })
      } catch (fallbackErr) {
        setError(fallbackErr.message)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleIngest = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reingest: true }),
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data?.detail || data?.message || 'Ingestion failed')
      }
      setAnswer(`[SYSTEM] Ingestion ${data.status}: ${data.message}`)
      setSources([])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const restoreTerminal = () => {
    setShowTerminal(true)
    setIsMinimized(false)
  }

  return (
    <div className="desktop-shell">
      {/* Top menu bar: rainbow banana logo (left) + toolbar + time (right) */}
      <header className="menu-bar">
        <div className="menu-bar-left">
          <span className="menu-bar-logo" aria-hidden="true">
            <svg className="rainbow-banana-logo" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="menu-banana-rainbow" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#22c55e" />
                  <stop offset="25%" stopColor="#eab308" />
                  <stop offset="40%" stopColor="#f97316" />
                  <stop offset="55%" stopColor="#ef4444" />
                  <stop offset="75%" stopColor="#a855f7" />
                  <stop offset="100%" stopColor="#3b82f6" />
                </linearGradient>
              </defs>
              <path fill="url(#menu-banana-rainbow)" d="M6 8 Q4 16 7 24 Q11 28 17 26 Q24 24 26 16 Q26 8 20 4 Q14 0 8 4 Q6 6 6 8 Z" />
              <text x="16" y="18" textAnchor="middle" fill="white" fontSize="12" fontWeight="bold">?</text>
            </svg>
          </span>
          <nav className="menu-bar-toolbar" aria-label="Main menu">
            <span className="menu-bar-item menu-bar-app">LegacyLens</span>
            <button type="button" className="menu-bar-item">File</button>
            <button type="button" className="menu-bar-item">Edit</button>
            <button type="button" className="menu-bar-item">View</button>
            <button type="button" className="menu-bar-item">Go</button>
            <button type="button" className="menu-bar-item" onClick={restoreTerminal}>Terminal</button>
            <button type="button" className="menu-bar-item">Window</button>
            <button type="button" className="menu-bar-item">Help</button>
          </nav>
        </div>
        <div className="menu-bar-right">
          <time dateTime={new Date().toISOString()} className="menu-bar-time" title={menuTime}>
            {menuTime}
          </time>
        </div>
      </header>

      <div className="desktop-icons-stack" aria-hidden="true">
        <button className="desktop-icon" onClick={() => setShowDonutWindow(true)}>
          <div className="cd-icon">
            <div className="cd-hole" />
          </div>
          <div className="desktop-icon-label">Donut?</div>
        </button>

        <button className="desktop-icon" onClick={restoreTerminal}>
          <div className="terminal-icon-box">&gt;_</div>
          <div className="desktop-icon-label">Terminal</div>
        </button>
      </div>

      {showTerminal && (
        <div className={`terminal-window ${isMaximized ? 'maximized' : ''}`}>
          <div className="window-bar">
            <div className="window-dots">
              <button className="dot red" title="Close" onClick={() => setShowTerminal(false)} />
              <button
                className="dot amber"
                title="Minimize"
                onClick={() => setIsMinimized((prev) => !prev)}
              />
              <button
                className="dot green"
                title="Maximize"
                onClick={() => setIsMaximized((prev) => !prev)}
              />
            </div>
            <div className="window-title">LegacyLens :: Terminal</div>
            <button onClick={handleIngest} disabled={loading} className="mini-btn">
              {loading ? 'BUSY' : 'REINDEX'}
            </button>
          </div>

          {!isMinimized && (
            <div className="terminal-body crt-overlay">
              <p className="line"># LegacyLens</p>

              <p className="line status-row">
                STATUS:{' '}
                <span className={health?.status === 'healthy' ? 'ok' : 'warn'}>
                  {health?.status ? health.status.toUpperCase() : 'CHECKING'}
                </span>
                {timings?.retrieval_ms ? ` | RETRIEVAL ${timings.retrieval_ms}ms` : ''}
                {timings?.total_ms ? ` | TOTAL ${timings.total_ms}ms` : ''}
                {sources.length ? ` | SOURCES ${sources.length}` : ''}
              </p>

              <div className="feature-row">
                <span className="feature-row-label">Query mode:</span>
                {FEATURES.map((f) => (
                  <button
                    key={f.id ?? 'general'}
                    type="button"
                    onClick={() => setFeature(f.id)}
                    className={`feature-chip ${feature === f.id ? 'active' : ''}`}
                    title={f.hint}
                  >
                    {f.label}
                  </button>
                ))}
                {feature != null && (
                  <span className="feature-hint">
                    ({FEATURES.find((x) => x.id === feature)?.hint ?? 'General'})
                  </span>
                )}
              </div>

              <QueryInput onSubmit={handleQuery} loading={loading} query={query} setQuery={setQuery} />

              {error && <div className="error-box">[ERROR] {error}</div>}

              {(answer || sources.length > 0 || loading) && (
                <div className="panels-grid">
                  <AnswerPanel answer={answer} loading={loading} />
                  <ResultsPanel sources={sources} />
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {showDonutWindow && (
        <div className="modal-backdrop" onClick={() => setShowDonutWindow(false)}>
          <div className="donut-window" onClick={(e) => e.stopPropagation()}>
            <div className="donut-title">About This OS</div>
            <p>OS built by Sanjit Rajendiran.</p>
            <button className="mini-btn" onClick={() => setShowDonutWindow(false)}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
