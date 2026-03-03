import React, { useState, useEffect } from 'react'
import QueryInput from './components/QueryInput'
import AnswerPanel from './components/AnswerPanel'
import ResultsPanel from './components/ResultsPanel'

const API_BASE = '/api'

const FEATURES = [
  { id: null, label: 'General Query' },
  { id: 'explain', label: 'Code Explanation' },
  { id: 'dependencies', label: 'Dependency Mapping' },
  { id: 'patterns', label: 'Pattern Detection' },
  { id: 'documentation', label: 'Documentation Gen' },
  { id: 'business_logic', label: 'Business Logic' },
]

function App() {
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState(null)
  const [feature, setFeature] = useState(null)
  const [timings, setTimings] = useState(null)
  const [health, setHealth] = useState(null)

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then(res => res.json())
      .then(data => setHealth(data))
      .catch(err => setHealth({ status: 'error', error: err.message }))
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
        body: JSON.stringify({
          query: queryText,
          feature: feature,
          stream: true,
        }),
      })

      if (!response.ok) {
        throw new Error(`Query failed: ${response.statusText}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let answerText = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value)
        const lines = text.split('\n').filter(l => l.trim())

        for (const line of lines) {
          try {
            const data = JSON.parse(line)
            if (data.type === 'sources') {
              setSources(data.sources)
              setTimings(prev => ({
                ...prev,
                retrieval_ms: Math.round(data.retrieval_time_ms),
              }))
            } else if (data.type === 'answer_chunk') {
              answerText += data.content
              setAnswer(answerText)
            } else if (data.type === 'done') {
              setTimings(prev => ({
                ...prev,
                total_ms: Math.round(data.total_time_ms),
              }))
            }
          } catch (e) {
            // Skip malformed lines
          }
        }
      }
    } catch (err) {
      setError(err.message)
      try {
        const response = await fetch(`${API_BASE}/query`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: queryText,
            feature: feature,
            stream: false,
          }),
        })
        const data = await response.json()
        setAnswer(data.answer)
        setSources(data.sources)
        setTimings({
          retrieval_ms: Math.round(data.retrieval_time_ms),
          total_ms: Math.round(data.total_time_ms),
        })
        setError(null)
      } catch (e2) {
        setError(e2.message)
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
      setAnswer(`Ingestion ${data.status}: ${data.message}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-crt-bg text-crt-green font-terminal relative">
      <div className="crt-overlay fixed inset-0 z-[100]" aria-hidden="true" />

      <main className="max-w-4xl mx-auto px-4 py-8 relative z-10">
        {/* Header - faux terminal title */}
        <header className="mb-8">
          <h1 className="text-3xl text-crt-green mb-1"># LegacyLens</h1>
          <p className="text-crt-green/90 text-lg">
            Would you like to play a game? — RAG-powered legacy codebase explorer.
          </p>
          <div className="flex items-center gap-4 mt-3 text-sm text-crt-green/70">
            {health && (
              <span>
                [{health.status === 'healthy' ? 'ONLINE' : 'DEGRADED'}]
              </span>
            )}
            <button
              type="button"
              onClick={handleIngest}
              disabled={loading}
              className="hover:text-crt-green transition-colors disabled:opacity-50 underline"
            >
              re-ingest
            </button>
          </div>
        </header>

        {/* Feature toggles - terminal style */}
        <div className="flex gap-2 mb-4 flex-wrap text-sm">
          {FEATURES.map(f => (
            <button
              key={f.id || 'general'}
              type="button"
              onClick={() => setFeature(f.id)}
              className={`px-2 py-0.5 border transition-colors ${
                feature === f.id
                  ? 'border-crt-green text-crt-green'
                  : 'border-crt-border text-crt-green/70 hover:border-crt-green/50'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Command line input */}
        <div className="mb-6">
          <QueryInput
            onSubmit={handleQuery}
            loading={loading}
            query={query}
            setQuery={setQuery}
          />
        </div>

        {error && (
          <div className="mb-4 text-red-400 border border-red-800/50 px-3 py-2 text-sm">
            ERROR: {error}
          </div>
        )}

        {timings && (
          <div className="mb-4 flex gap-4 text-sm text-crt-green/60">
            {timings.retrieval_ms != null && (
              <span>retrieval: {timings.retrieval_ms}ms</span>
            )}
            {timings.total_ms != null && (
              <span>total: {timings.total_ms}ms</span>
            )}
            {sources.length > 0 && (
              <span>{sources.length} source(s)</span>
            )}
          </div>
        )}

        {(answer || sources.length > 0) && (
          <div className="mt-6 space-y-6">
            {answer && (
              <AnswerPanel answer={answer} loading={loading} />
            )}
            {sources.length > 0 && (
              <ResultsPanel sources={sources} />
            )}
          </div>
        )}

        {!answer && sources.length === 0 && !loading && !error && (
          <div className="mt-12 space-y-6">
            <p className="text-crt-green/80 text-lg">
              Query the GnuCOBOL codebase. Examples:
            </p>
            <div className="flex flex-wrap gap-2">
              {[
                'Where is the main entry point of the compiler?',
                'How does COBOL file I/O work?',
                'What error handling patterns are used?',
                'Show me the parser implementation',
              ].map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => {
                    setQuery(example)
                    handleQuery(example)
                  }}
                  className="text-left text-sm px-3 py-2 border border-crt-border text-crt-green/90 hover:border-crt-green hover:text-crt-green transition-colors max-w-md"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
