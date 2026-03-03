import React from 'react'
import ReactMarkdown from 'react-markdown'

function AnswerPanel({ answer, loading }) {
  if (!answer && !loading) return null

  return (
    <div className="border border-crt-border bg-crt-bg/80">
      <div className="px-3 py-2 border-b border-crt-border text-crt-green/80 text-sm">
        &gt; ANSWER {loading && <span className="animate-pulse">[...]</span>}
      </div>
      <div className="p-4 overflow-auto max-h-[500px] font-terminal text-crt-green text-lg leading-relaxed">
        <ReactMarkdown
          components={{
            code({ node, inline, className, children, ...props }) {
              if (inline) {
                return (
                  <code className="text-crt-green/90 border border-crt-border px-1" {...props}>
                    {children}
                  </code>
                )
              }
              return (
                <pre className="border border-crt-border p-3 my-2 overflow-x-auto text-base">
                  <code className="text-crt-green/90" {...props}>
                    {children}
                  </code>
                </pre>
              )
            },
            p({ children }) {
              return <p className="mb-3">{children}</p>
            },
            h1({ children }) {
              return <h1 className="text-xl mb-2 text-crt-green">{children}</h1>
            },
            h2({ children }) {
              return <h2 className="text-lg mb-2 text-crt-green">{children}</h2>
            },
            h3({ children }) {
              return <h3 className="text-base mb-1 text-crt-green">{children}</h3>
            },
            ul({ children }) {
              return <ul className="list-disc list-inside mb-3">{children}</ul>
            },
            ol({ children }) {
              return <ol className="list-decimal list-inside mb-3">{children}</ol>
            },
            li({ children }) {
              return <li className="mb-0.5">{children}</li>
            },
            strong({ children }) {
              return <strong className="text-crt-green">{children}</strong>
            },
          }}
        >
          {answer}
        </ReactMarkdown>
        {loading && !answer && (
          <div className="flex items-center gap-2 text-crt-green/70">
            <span className="animate-pulse">_</span>
            <span>Thinking...</span>
          </div>
        )}
      </div>
    </div>
  )
}

export default AnswerPanel
