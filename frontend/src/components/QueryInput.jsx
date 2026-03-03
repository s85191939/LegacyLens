import React from 'react'

function QueryInput({ onSubmit, loading, query, setQuery, disabled }) {
  const handleSubmit = (e) => {
    e.preventDefault()
    if (query.trim() && !loading && !disabled) {
      onSubmit(query.trim())
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const isDisabled = loading || disabled

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
          disabled={isDisabled}
        />
        <span className="cursor-block" aria-hidden="true" />
      </div>
      <button type="submit" className="query-submit" disabled={isDisabled || !query.trim()}>
        {loading ? 'RUNNING' : 'RUN'}
      </button>
    </form>
  )
}

export default QueryInput
