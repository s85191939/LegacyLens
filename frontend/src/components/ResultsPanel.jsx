import React, { useState } from 'react'
import CodeBlock from './CodeBlock'

function ResultsPanel({ sources }) {
  const [expanded, setExpanded] = useState(null)

  return (
    <section className="terminal-panel">
      <div className="panel-head">[SOURCES] {sources?.length || 0}</div>
      <div className="panel-body sources-body">
        {!sources || sources.length === 0 ? (
          <p className="dim">No citations yet.</p>
        ) : (
          sources.map((s, i) => (
            <div key={`${s.file_path}-${i}`} className="source-item">
              <button className="source-toggle" onClick={() => setExpanded(expanded === i ? null : i)}>
                <span className="source-title">{s.file_path}</span>
                <span className="source-meta">L{s.start_line}-{s.end_line} | {(s.score * 100).toFixed(1)}%</span>
              </button>
              {expanded === i && (
                <div className="source-code-wrap">
                  <CodeBlock code={s.content} language={s.language || 'text'} startLine={s.start_line} />
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </section>
  )
}

export default ResultsPanel
