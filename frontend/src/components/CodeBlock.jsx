import React from 'react'

function CodeBlock({ code, language, startLine = 1 }) {
  const lines = code.split('\n')

  return (
    <div className="border border-crt-border">
      <div className="px-3 py-1.5 border-b border-crt-border flex items-center justify-between text-sm text-crt-green/70">
        <span>
          {language.toUpperCase()} | L{startLine}-{startLine + lines.length - 1}
        </span>
        <button
          type="button"
          onClick={() => navigator.clipboard.writeText(code)}
          className="text-crt-green/60 hover:text-crt-green transition-colors"
        >
          [COPY]
        </button>
      </div>
      <div className="overflow-x-auto">
        <pre className="p-3 text-sm leading-relaxed font-mono">
          {lines.map((line, i) => (
            <div key={i} className="flex hover:bg-crt-dim/30">
              <span className="text-crt-green/40 select-none w-10 flex-shrink-0 text-right pr-3 border-r border-crt-border mr-3">
                {startLine + i}
              </span>
              <span className="text-crt-green/90 whitespace-pre">
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
