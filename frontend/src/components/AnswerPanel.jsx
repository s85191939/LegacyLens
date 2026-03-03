import React from 'react'
import ReactMarkdown from 'react-markdown'

function AnswerPanel({ answer, loading }) {
  if (!answer && !loading) return null

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-emerald-400" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
        </svg>
        <h3 className="text-sm font-semibold text-gray-300">Answer</h3>
        {loading && (
          <span className="text-xs text-gray-500 animate-pulse">Generating...</span>
        )}
      </div>
      <div className="p-4 prose prose-invert prose-sm max-w-none overflow-auto max-h-[600px]">
        <ReactMarkdown
          components={{
            code({ node, inline, className, children, ...props }) {
              if (inline) {
                return (
                  <code className="bg-gray-800 px-1.5 py-0.5 rounded text-emerald-300 text-xs" {...props}>
                    {children}
                  </code>
                )
              }
              return (
                <pre className="bg-gray-950 border border-gray-800 rounded-lg p-3 overflow-x-auto">
                  <code className="text-gray-300 text-xs" {...props}>
                    {children}
                  </code>
                </pre>
              )
            },
            p({ children }) {
              return <p className="text-gray-300 mb-3 leading-relaxed text-sm">{children}</p>
            },
            h1({ children }) {
              return <h1 className="text-lg font-bold text-white mb-2">{children}</h1>
            },
            h2({ children }) {
              return <h2 className="text-base font-semibold text-white mb-2">{children}</h2>
            },
            h3({ children }) {
              return <h3 className="text-sm font-semibold text-gray-200 mb-1">{children}</h3>
            },
            ul({ children }) {
              return <ul className="list-disc list-inside text-gray-300 mb-3 text-sm">{children}</ul>
            },
            ol({ children }) {
              return <ol className="list-decimal list-inside text-gray-300 mb-3 text-sm">{children}</ol>
            },
            li({ children }) {
              return <li className="mb-1">{children}</li>
            },
            strong({ children }) {
              return <strong className="text-emerald-300 font-semibold">{children}</strong>
            },
          }}
        >
          {answer}
        </ReactMarkdown>
        {loading && !answer && (
          <div className="flex items-center gap-2 text-gray-500">
            <div className="flex gap-1">
              <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
              <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
              <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            </div>
            <span className="text-sm">Thinking...</span>
          </div>
        )}
      </div>
    </div>
  )
}

export default AnswerPanel
