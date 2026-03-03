import React, { useRef } from 'react'

function QueryInput({ onSubmit, loading, query, setQuery }) {
  const inputRef = useRef(null)

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
    <form onSubmit={handleSubmit} className="font-terminal">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-crt-green shrink-0 select-none">C:\LEGACYLENS&gt;</span>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="E.g. main entry point or file I/O"
          disabled={loading}
          className="flex-1 min-w-[200px] bg-transparent border border-crt-border text-crt-green placeholder-crt-green/40
                     focus:outline-none focus:border-crt-green px-2 py-1.5 text-lg font-terminal"
          style={{ caretColor: '#33ff33' }}
        />
        {loading && (
          <span className="text-crt-green/70 text-lg animate-pulse">[...]</span>
        )}
      </div>
    </form>
  )
}

export default QueryInput
