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

  // Check health on mount
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
      // Fall back to non-streaming
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
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center text-lg font-bold">
              L
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">LegacyLens</h1>
              <p className="text-xs text-gray-400">RAG for Legacy Codebases</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {health && (
              <span className={`text-xs px-2 py-1 rounded ${
                health.status === 'healthy'
                  ? 'bg-emerald-900/50 text-emerald-400'
                  : 'bg-red-900/50 text-red-400'
              }`}>
                {health.status === 'healthy' ? 'Connected' : 'Disconnected'}
              </span>
            )}
            <button
              onClick={handleIngest}
              disabled={loading}
              className="text-sm px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
            >
              Re-ingest
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Feature Selector */}
        <div className="flex gap-2 mb-4 flex-wrap">
          {FEATURES.map(f => (
            <button
              key={f.id || 'general'}
              onClick={() => setFeature(f.id)}
              className={`text-sm px-3 py-1.5 rounded-full transition-colors ${
                feature === f.id
                  ? 'bg-emerald-600 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Query Input */}
        <QueryInput
          onSubmit={handleQuery}
          loading={loading}
          query={query}
          setQuery={setQuery}
        />

        {/* Error */}
        {error && (
          <div className="mt-4 p-4 bg-red-900/30 border border-red-800 rounded-lg text-red-300">
            {error}
          </div>
        )}

        {/* Timings */}
        {timings && (
          <div className="mt-3 flex gap-4 text-xs text-gray-500">
            {timings.retrieval_ms && (
              <span>Retrieval: {timings.retrieval_ms}ms</span>
            )}
            {timings.total_ms && (
              <span>Total: {timings.total_ms}ms</span>
            )}
            {sources.length > 0 && (
              <span>{sources.length} sources found</span>
            )}
          </div>
        )}

        {/* Results Grid */}
        {(answer || sources.length > 0) && (
          <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Answer Panel */}
            <div className="lg:col-span-1">
              <AnswerPanel answer={answer} loading={loading} />
            </div>

            {/* Sources Panel */}
            <div className="lg:col-span-1">
              <ResultsPanel sources={sources} />
            </div>
          </div>
        )}

        {/* Empty State */}
        {!answer && sources.length === 0 && !loading && !error && (
          <div className="mt-16 text-center">
            <div className="text-6xl mb-4">🔍</div>
            <h2 className="text-xl font-semibold text-gray-300 mb-2">
              Query the GnuCOBOL Codebase
            </h2>
            <p className="text-gray-500 max-w-md mx-auto mb-8">
              Ask questions about the codebase in natural language. Get code snippets,
              explanations, and references.
            </p>
            <div className="flex flex-wrap gap-2 justify-center max-w-lg mx-auto">
              {[
                "Where is the main entry point of the compiler?",
                "How does COBOL file I/O work?",
                "What error handling patterns are used?",
                "Show me the parser implementation",
              ].map((example) => (
                <button
                  key={example}
                  onClick={() => {
                    setQuery(example)
                    handleQuery(example)
                  }}
                  className="text-sm px-3 py-2 bg-gray-800/50 border border-gray-700 rounded-lg hover:bg-gray-700 transition-colors text-gray-300"
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
