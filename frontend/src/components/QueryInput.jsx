import React from 'react'

function QueryInput({ onSubmit, loading, query, setQuery }) {
  const handleSubmit = (e) => {
    e.preventDefault()
    if (query.trim() && !loading) {
      onSubmit(query.trim())
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="prompt-row">
      <label htmlFor="legacy-query" className="prompt-label">
        C:\\LEGACYLENS&gt;
      </label>
      <div className="prompt-input-wrap">
        <input
          id="legacy-query"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. show parser implementation"
          className="prompt-input"
          disabled={loading}
        />
        <span className="cursor-block" aria-hidden="true" />
      </div>
      <button type="submit" className="query-submit" disabled={loading || !query.trim()}>
        {loading ? 'RUNNING' : 'RUN'}
      </button>
    </form>
  )
}

export default QueryInput
