import React, { useEffect, useRef, useState } from 'react'
import QueryInput from './components/QueryInput'
import AnswerPanel from './components/AnswerPanel'
import ResultsPanel from './components/ResultsPanel'

const API_BASE = '/api'

const FEATURES_WITH_PROMPTS = [
  {
    id: null,
    label: 'GENERAL',
    prompts: [
      'Where is the main entry point of the compiler?',
      'How does COBOL file I/O work?',
      'What error handling patterns are used?',
      'Show me the parser implementation.',
      'How are COBOL divisions and sections parsed?',
      'Where is symbol table or name resolution handled?',
      'How does the code generator emit output?',
      'What data structures represent the AST or parse tree?',
      'How are COPY and REPLACING directives processed?',
      'Where is numeric or decimal arithmetic implemented?',
      'Find the main program or driver routine.',
      'How is memory management done?',
      'Where are compiler flags or options parsed?',
      'Show error message formatting or reporting.',
      'How is the symbol table built?',
    ],
  },
  {
    id: 'explain',
    label: 'EXPLAIN',
    prompts: [
      'Explain what the main compilation loop does.',
      'Explain how COBOL paragraphs are compiled.',
      'Explain the role of the lexer and parser.',
      'Explain how data division is processed.',
      'Explain code generation for PERFORM.',
      'Explain how CALL statements are handled.',
      'Explain the preprocessor or COPY handling.',
      'Explain error recovery in the parser.',
      'Explain how literals and constants are stored.',
      'Explain the runtime library interface.',
    ],
  },
  {
    id: 'dependencies',
    label: 'DEPENDENCIES',
    prompts: [
      'What calls the main entry point?',
      'What does the parser depend on?',
      'Show PERFORM/CALL/COPY dependencies for the compiler.',
      'What modules does code generation depend on?',
      'Map dependencies of the symbol table.',
      'What are the dependencies of the scanner?',
      'Show call graph for error handling.',
      'What does the optimizer depend on?',
      'Dependencies of the code emitter.',
      'What external libraries does the compiler use?',
    ],
  },
  {
    id: 'patterns',
    label: 'PATTERNS',
    prompts: [
      'Find all file I/O operations.',
      'Find error handling patterns in this codebase.',
      'Show similar code patterns for PERFORM.',
      'Find all places that modify the symbol table.',
      'Patterns for parsing identifiers.',
      'Find recursive or nested parsing patterns.',
      'Show patterns for emitting machine code.',
      'Find all COPY or INCLUDE usage.',
      'Patterns for type checking or validation.',
      'Find similar error message formatting.',
    ],
  },
  {
    id: 'documentation',
    label: 'DOCS',
    prompts: [
      'Generate a short doc for the main compilation flow.',
      'Document the chunking or parsing pipeline.',
      'Summarize the public API of the code generator.',
      'Document how to add a new COBOL construct.',
      'Document the embedding or vector storage usage.',
      'Document error codes and meanings.',
      'Document the symbol table structure.',
      'Document the AST node types.',
      'Document configuration or build options.',
      'Document the runtime interface.',
    ],
  },
  {
    id: 'business_logic',
    label: 'BUSINESS',
    prompts: [
      'What business rules does the compiler enforce?',
      'Where are language semantics enforced?',
      'What validation happens during compilation?',
      'Where are COBOL standards checked?',
      'What decisions affect code generation?',
      'Where are compiler limits or quotas applied?',
      'What runtime behavior is guaranteed?',
      'Where are dialect or extension rules?',
      'What optimization decisions are made?',
      'Where is diagnostic or reporting policy?',
    ],
  },
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
  const [openDropdown, setOpenDropdown] = useState(null) // 'general' | 'explain' | ... | null
  const [windowPosition, setWindowPosition] = useState({ x: 96, y: 52 })

  const terminalRef = useRef(null)
  const dragRef = useRef(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    if (openDropdown == null) return
    const close = (e) => {
      if (!e.target.closest('.feature-dropdown-wrap')) setOpenDropdown(null)
    }
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [openDropdown])

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

  useEffect(() => {
    return () => {
      window.removeEventListener('mousemove', handleWindowDrag)
      window.removeEventListener('mouseup', endWindowDrag)
    }
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

  const endWindowDrag = () => {
    dragRef.current = null
    window.removeEventListener('mousemove', handleWindowDrag)
    window.removeEventListener('mouseup', endWindowDrag)
  }

  const handleWindowDrag = (event) => {
    if (!dragRef.current || !terminalRef.current || isMaximized) return
    const rect = terminalRef.current.getBoundingClientRect()
    const maxX = Math.max(8, window.innerWidth - rect.width - 8)
    const maxY = Math.max(36, window.innerHeight - rect.height - 8)
    const nextX = Math.min(maxX, Math.max(8, event.clientX - dragRef.current.offsetX))
    const nextY = Math.min(maxY, Math.max(36, event.clientY - dragRef.current.offsetY))
    setWindowPosition({ x: nextX, y: nextY })
  }

  const startWindowDrag = (event) => {
    if (event.button !== 0 || isMaximized || !terminalRef.current) return
    const rect = terminalRef.current.getBoundingClientRect()
    dragRef.current = {
      offsetX: event.clientX - rect.left,
      offsetY: event.clientY - rect.top,
    }
    window.addEventListener('mousemove', handleWindowDrag)
    window.addEventListener('mouseup', endWindowDrag)
  }

  return (
    <div className="desktop-shell">
      {/* Toolbar: banana logo (image joke) + app menu + time */}
      <header className="menu-bar banana-toolbar" aria-label="App toolbar">
        <div className="menu-bar-left">
          <span className="menu-bar-logo" aria-hidden="true">
            <svg className="rainbow-banana-logo" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
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
              {/* Curved banana shape (stem left, tip right) */}
              <path
                fill="url(#menu-banana-rainbow)"
                d="M6 8 C8 4 16 2 24 8 C30 14 28 22 22 26 C14 28 6 22 6 16 C6 12 6 8 6 8 Z"
              />
            </svg>
          </span>
          <span className="menu-bar-sep" aria-hidden="true">|</span>
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
        <div
          ref={terminalRef}
          className={`terminal-window ${isMaximized ? 'maximized' : ''}`}
          style={isMaximized ? undefined : { left: `${windowPosition.x}px`, top: `${windowPosition.y}px` }}
        >
          <div className="window-bar" onMouseDown={startWindowDrag}>
            <div className="window-dots" onMouseDown={(e) => e.stopPropagation()}>
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
            <button onMouseDown={(e) => e.stopPropagation()} onClick={handleIngest} disabled={loading} className="mini-btn">
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
                {FEATURES_WITH_PROMPTS.map((f) => {
                  const key = f.id ?? 'general'
                  const isOpen = openDropdown === key
                  return (
                    <div key={key} className="feature-dropdown-wrap">
                      <button
                        type="button"
                        className={`feature-chip ${feature === f.id ? 'active' : ''} ${isOpen ? 'open' : ''}`}
                        onClick={(e) => {
                          e.stopPropagation()
                          setOpenDropdown(isOpen ? null : key)
                        }}
                        aria-expanded={isOpen}
                        aria-haspopup="listbox"
                        aria-label={`${f.label} prompts`}
                      >
                        {f.label}
                        <span className="feature-chip-chevron" aria-hidden>▾</span>
                      </button>
                      {isOpen && (
                        <div className="feature-panel" role="listbox">
                          <div className="feature-panel-title">{f.label}</div>
                          <div className="feature-panel-list">
                            {f.prompts.map((p) => (
                              <button
                                key={p}
                                type="button"
                                className="feature-panel-item"
                                role="option"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setFeature(f.id)
                                  setQuery(p)
                                  handleQuery(p)
                                  setOpenDropdown(null)
                                }}
                              >
                                {p}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
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
