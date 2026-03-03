import React, { useState } from 'react'
import CodeBlock from './CodeBlock'

function ResultsPanel({ sources }) {
  const [expandedIndex, setExpandedIndex] = useState(null)

  if (!sources || sources.length === 0) return null

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
        </svg>
        <h3 className="text-sm font-semibold text-gray-300">
          Sources ({sources.length})
        </h3>
      </div>
      <div className="overflow-auto max-h-[600px]">
        {sources.map((source, index) => (
          <div
            key={index}
            className="border-b border-gray-800 last:border-b-0"
          >
            {/* Source Header */}
            <button
              onClick={() => setExpandedIndex(expandedIndex === index ? null : index)}
              className="w-full px-4 py-3 text-left hover:bg-gray-800/50 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-1.5 py-0.5 rounded font-mono ${
                      source.language === 'cobol'
                        ? 'bg-purple-900/50 text-purple-300'
                        : source.language === 'c'
                        ? 'bg-blue-900/50 text-blue-300'
                        : 'bg-gray-800 text-gray-400'
                    }`}>
                      {source.language}
                    </span>
                    <span className="text-xs text-gray-500 capitalize">
                      {source.chunk_type}
                    </span>
                  </div>
                  <p className="text-sm font-mono text-gray-200 mt-1 truncate">
                    {source.file_path}
                  </p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-gray-500">
                      Lines {source.start_line}-{source.end_line}
                    </span>
                    {source.name && (
                      <span className="text-xs text-emerald-400">
                        {source.name}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-mono px-2 py-1 rounded ${
                    source.score >= 0.7
                      ? 'bg-emerald-900/50 text-emerald-300'
                      : source.score >= 0.4
                      ? 'bg-yellow-900/50 text-yellow-300'
                      : 'bg-red-900/50 text-red-300'
                  }`}>
                    {(source.score * 100).toFixed(1)}%
                  </span>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className={`h-4 w-4 text-gray-500 transition-transform ${
                      expandedIndex === index ? 'rotate-180' : ''
                    }`}
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>
              {/* Dependencies */}
              {source.dependencies && source.dependencies.length > 0 && (
                <div className="flex gap-1 mt-2 flex-wrap">
                  {source.dependencies.slice(0, 5).map((dep, i) => (
                    <span key={i} className="text-xs bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded">
                      {dep}
                    </span>
                  ))}
                  {source.dependencies.length > 5 && (
                    <span className="text-xs text-gray-500">
                      +{source.dependencies.length - 5} more
                    </span>
                  )}
                </div>
              )}
            </button>

            {/* Expanded Code View */}
            {expandedIndex === index && (
              <div className="px-4 pb-4">
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
