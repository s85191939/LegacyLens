import React from 'react'
import ReactMarkdown from 'react-markdown'

function AnswerPanel({ answer, loading }) {
  return (
    <section className="terminal-panel">
      <div className="panel-head">[ANSWER]</div>
      <div className="panel-body">
        {loading && !answer && <p className="dim">Thinking...</p>}
        {!loading && !answer && <p className="dim">No answer yet. Run a query.</p>}
        {answer && (
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="md-p">{children}</p>,
              strong: ({ children }) => <strong className="md-strong">{children}</strong>,
              code: ({ inline, children, ...props }) =>
                inline ? (
                  <code className="md-inline" {...props}>
                    {children}
                  </code>
                ) : (
                  <pre className="md-pre">
                    <code {...props}>{children}</code>
                  </pre>
                ),
              ul: ({ children }) => <ul className="md-list">{children}</ul>,
              ol: ({ children }) => <ol className="md-list-ordered">{children}</ol>,
              li: ({ children }) => <li>{children}</li>,
              h1: ({ children }) => <h1 className="md-h">{children}</h1>,
              h2: ({ children }) => <h2 className="md-h">{children}</h2>,
              h3: ({ children }) => <h3 className="md-h">{children}</h3>,
            }}
          >
            {answer}
          </ReactMarkdown>
        )}
      </div>
    </section>
  )
}

export default AnswerPanel
