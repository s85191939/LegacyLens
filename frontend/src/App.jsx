import React, { useEffect, useState } from 'react'
import QueryInput from './components/QueryInput'
import AnswerPanel from './components/AnswerPanel'
import ResultsPanel from './components/ResultsPanel'

const API_BASE = '/api'

const FEATURES = [
  { id: null, label: 'GENERAL' },
  { id: 'explain', label: 'EXPLAIN' },
  { id: 'dependencies', label: 'DEPENDENCIES' },
  { id: 'patterns', label: 'PATTERNS' },
  { id: 'documentation', label: 'DOCS' },
  { id: 'business_logic', label: 'BUSINESS' },
]

function App() {
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [feature, setFeature] = useState(null)
  const [timings, setTimings] = useState(null)
  const [health, setHealth] = useState(null)

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
                {FEATURES.map((f) => (
                  <button
                    key={f.id || 'general'}
                    onClick={() => setFeature(f.id)}
                    className={`feature-chip ${feature === f.id ? 'active' : ''}`}
                  >
                    {f.label}
                  </button>
                ))}
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
