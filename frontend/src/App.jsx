import React, { useEffect, useState, useRef } from 'react'
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
  const [terminalVisible, setTerminalVisible] = useState(true)
  const [isFullScreen, setIsFullScreen] = useState(false)
  const [showCreditsWindow, setShowCreditsWindow] = useState(false)
  const [windowPos, setWindowPos] = useState({ x: 40, y: 40 })
  const [isDragging, setIsDragging] = useState(false)
  const [currentTime, setCurrentTime] = useState(() => formatMenuBarTime(new Date()))
  const dragRef = useRef({ startX: 0, startY: 0, startLeft: 0, startTop: 0 })
  const isDraggingRef = useRef(false)

  function formatMenuBarTime(date) {
    const day = date.toLocaleDateString([], { weekday: 'short' })
    const month = date.toLocaleDateString([], { month: 'short' })
    const dayNum = date.getDate()
    const time = date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
    return `${day} ${month} ${dayNum} ${time}`
  }

  useEffect(() => {
    const tick = () => setCurrentTime(formatMenuBarTime(new Date()))
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

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

  const handleBarMouseDown = (e) => {
    if (e.button !== 0) return
    isDraggingRef.current = true
    setIsDragging(true)
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      startLeft: windowPos.x,
      startTop: windowPos.y,
    }
  }

  useEffect(() => {
    const onMove = (e) => {
      if (!isDraggingRef.current) return
      setWindowPos({
        x: dragRef.current.startLeft + (e.clientX - dragRef.current.startX),
        y: dragRef.current.startTop + (e.clientY - dragRef.current.startY),
      })
    }
    const onUp = () => {
      isDraggingRef.current = false
      setIsDragging(false)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [])

  const handleRedDot = (e) => {
    e.stopPropagation()
    setTerminalVisible(false)
  }
  const handleAmberDot = (e) => {
    e.stopPropagation()
    setTerminalVisible(false)
  }
  const handleGreenDot = (e) => {
    e.stopPropagation()
    setIsFullScreen((prev) => !prev)
  }

  return (
    <div className="desktop-shell">
      {/* Top bar: logo + toolbar (menus) + time */}
      <header className="menu-bar">
        <div className="menu-bar-left">
          <span className="menu-bar-logo" aria-hidden="true">
            <svg className="rainbow-banana-logo" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="menu-banana-rainbow" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#ff3366" />
                  <stop offset="20%" stopColor="#ff9933" />
                  <stop offset="40%" stopColor="#ffff33" />
                  <stop offset="60%" stopColor="#33cc66" />
                  <stop offset="80%" stopColor="#3366ff" />
                  <stop offset="100%" stopColor="#ff3366" />
                </linearGradient>
              </defs>
              <path fill="url(#menu-banana-rainbow)" d="M6 8 Q4 16 7 24 Q11 28 17 26 Q24 24 26 16 Q26 8 20 4 Q14 0 8 4 Q6 6 6 8 Z" />
            </svg>
          </span>
          <nav className="menu-bar-toolbar" aria-label="Main menu">
            <button type="button" className="menu-bar-item">LegacyLens</button>
            <button type="button" className="menu-bar-item">File</button>
            <button type="button" className="menu-bar-item">Edit</button>
            <button type="button" className="menu-bar-item">View</button>
            <button type="button" className="menu-bar-item">Go</button>
            <button type="button" className="menu-bar-item" onClick={() => setTerminalVisible(true)}>Terminal</button>
            <button type="button" className="menu-bar-item">Window</button>
            <button type="button" className="menu-bar-item">Help</button>
          </nav>
        </div>
        <div className="menu-bar-right">
          <time dateTime={new Date().toISOString()} className="menu-bar-time" title={currentTime}>
            {currentTime}
          </time>
        </div>
      </header>

      <div className="desktop-icons">
        {/* Terminal icon: click to bring window back */}
        <button
          type="button"
          className="desktop-icon"
          onClick={() => setTerminalVisible(true)}
          title="Terminal"
          aria-label="Open Terminal"
        >
          <span className="desktop-icon-emoji">⌘</span>
          <span className="desktop-icon-label">Terminal</span>
        </button>

        {/* CD / Donut icon: click for credits */}
        <button
          type="button"
          className="desktop-icon"
          onClick={() => setShowCreditsWindow(true)}
          title="About"
          aria-label="About"
        >
          <div className="cd-icon">
            <div className="cd-hole" />
          </div>
          <span className="desktop-icon-label">Donut</span>
        </button>
      </div>

      {/* Credits window */}
      {showCreditsWindow && (
        <div
          className="credits-overlay"
          onClick={() => setShowCreditsWindow(false)}
          role="presentation"
        >
          <div
            className="credits-window"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label="About"
          >
            <div className="window-bar credits-bar">
              <div className="window-dots">
                <span className="dot red" />
                <span className="dot amber" />
                <span className="dot green" />
              </div>
              <div className="window-title">About</div>
              <button
                type="button"
                className="mini-btn"
                onClick={() => setShowCreditsWindow(false)}
              >
                Close
              </button>
            </div>
            <div className="credits-body">
              <p className="credits-text">OS built by Sanjit Rajendiran</p>
            </div>
          </div>
        </div>
      )}

      {/* Terminal window (hidden when closed/minimized) */}
      {terminalVisible && (
        <div
          className={`terminal-window ${isFullScreen ? 'terminal-fullscreen' : ''}`}
          style={{
            position: 'fixed',
            left: isFullScreen ? 0 : windowPos.x,
            top: isFullScreen ? 0 : windowPos.y,
            margin: 0,
            width: isFullScreen ? '100vw' : undefined,
            height: isFullScreen ? '100vh' : undefined,
            maxWidth: isFullScreen ? '100vw' : undefined,
          }}
        >
          <div
            className="window-bar"
            onMouseDown={handleBarMouseDown}
            style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
            role="button"
            aria-label="Drag window"
          >
            <div className="window-dots" onClick={(e) => e.stopPropagation()}>
              <button type="button" className="dot red" onClick={handleRedDot} aria-label="Close" />
              <button type="button" className="dot amber" onClick={handleAmberDot} aria-label="Minimize" />
              <button type="button" className="dot green" onClick={handleGreenDot} aria-label={isFullScreen ? 'Exit full screen' : 'Full screen'} />
            </div>
          <div className="window-title">LegacyLens :: Terminal</div>
          <button onClick={handleIngest} disabled={loading} className="mini-btn">
            {loading ? 'BUSY' : 'REINDEX'}
          </button>
        </div>

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
      </div>
      )}
    </div>
  )
}

export default App
