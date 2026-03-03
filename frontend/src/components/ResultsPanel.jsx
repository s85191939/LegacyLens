import React, { useState } from 'react'
import CodeBlock from './CodeBlock'

function ResultsPanel({ sources }) {
  const [expandedIndex, setExpandedIndex] = useState(null)

  if (!sources || sources.length === 0) return null

  return (
    <div className="border border-crt-border bg-crt-bg/80">
      <div className="px-3 py-2 border-b border-crt-border text-crt-green/80 text-sm">
        &gt; SOURCES ({sources.length})
      </div>
      <div className="overflow-auto max-h-[500px]">
        {sources.map((source, index) => (
          <div
            key={index}
            className="border-b border-crt-border last:border-b-0"
          >
            <button
              type="button"
              onClick={() => setExpandedIndex(expandedIndex === index ? null : index)}
              className="w-full px-4 py-3 text-left hover:bg-crt-dim/50 transition-colors text-crt-green/90"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-crt-green/70">
                      [{source.language}] {source.chunk_type}
                    </span>
                  </div>
                  <p className="font-mono text-crt-green mt-0.5 truncate text-sm">
                    {source.file_path}
                  </p>
                  <div className="flex items-center gap-3 mt-0.5 text-crt-green/60 text-sm">
                    <span>L{source.start_line}-{source.end_line}</span>
                    {source.name && (
                      <span className="text-crt-green/80">{source.name}</span>
                    )}
                    <span className="text-crt-green/50">
                      {(source.score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <span className="text-crt-green/50 shrink-0">
                  {expandedIndex === index ? '[-]' : '[+]'}
                </span>
              </div>
              {source.dependencies && source.dependencies.length > 0 && (
                <div className="flex gap-1 mt-2 flex-wrap text-xs text-crt-green/50">
                  {source.dependencies.slice(0, 5).map((dep, i) => (
                    <span key={i}>{dep}</span>
                  ))}
                  {source.dependencies.length > 5 && (
                    <span>+{source.dependencies.length - 5}</span>
                  )}
                </div>
              )}
            </button>

            {expandedIndex === index && (
              <div className="px-4 pb-4 bg-crt-bg/50">
                <CodeBlock
                  code={source.content}
                  language={source.language}
                  startLine={source.start_line}
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default ResultsPanel
