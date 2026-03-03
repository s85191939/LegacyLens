import React from 'react'

function CodeBlock({ code, language, startLine = 1 }) {
  const lines = code.split('\n')

  return (
    <div className="bg-gray-950 border border-gray-800 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="px-3 py-1.5 bg-gray-900 border-b border-gray-800 flex items-center justify-between">
        <span className="text-xs text-gray-500 font-mono">
          {language.toUpperCase()} | Lines {startLine}-{startLine + lines.length - 1}
        </span>
        <button
          onClick={() => navigator.clipboard.writeText(code)}
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          Copy
        </button>
      </div>
      {/* Code */}
      <div className="overflow-x-auto">
        <pre className="p-3 text-xs leading-5">
          {lines.map((line, i) => (
            <div key={i} className="flex hover:bg-gray-900/50">
              <span className="text-gray-600 select-none w-12 flex-shrink-0 text-right pr-3 border-r border-gray-800 mr-3">
                {startLine + i}
              </span>
              <span className="text-gray-300 whitespace-pre">
                {line}
              </span>
            </div>
          ))}
        </pre>
      </div>
    </div>
  )
}

export default CodeBlock
