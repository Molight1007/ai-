import { useEffect, useState, type ReactNode } from 'react'
import { loadFile } from './api'

const KW = new Set([
  'def', 'class', 'return', 'if', 'elif', 'else', 'for', 'while', 'import', 'from', 'as',
  'with', 'try', 'except', 'finally', 'raise', 'pass', 'break', 'continue', 'in', 'is',
  'not', 'and', 'or', 'None', 'True', 'False', 'lambda', 'yield', 'global', 'nonlocal',
  'async', 'await',
])

const TOKEN_RE =
  /(#.*$)|("""[\s\S]*?"""|'''(?:[\s\S])*?'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|(\b[a-zA-Z_]\w*\b)|(\b\d+(?:\.\d+)?\b)/g

function highlight(line: string): ReactNode[] {
  const out: ReactNode[] = []
  let last = 0
  let k = 0
  for (const m of line.matchAll(TOKEN_RE)) {
    const idx = m.index ?? 0
    if (idx > last) out.push(line.slice(last, idx))
    const full = m[0]
    if (m[1]) out.push(<span key={k++} className="tok-comment">{m[1]}</span>)
    else if (m[2]) out.push(<span key={k++} className="tok-string">{m[2]}</span>)
    else if (m[3] && KW.has(m[3])) out.push(<span key={k++} className="tok-kw">{m[3]}</span>)
    else if (m[4]) out.push(<span key={k++} className="tok-num">{m[4]}</span>)
    else out.push(full)
    last = idx + full.length
  }
  if (last < line.length) out.push(line.slice(last))
  return out
}

interface Props {
  path: string
  root: string | null
  lines?: number
  highlightLine?: number
}

export function CodePanel({ path, root, lines, highlightLine }: Props) {
  const [code, setCode] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    loadFile(root, path).then((c) => {
      if (alive) setCode(c)
    })
    return () => {
      alive = false
    }
  }, [root, path])

  if (code === null) {
    return <div className="code-loading">加载中…</div>
  }

  const rows = code.split('\n')
  return (
    <div className="code-panel">
      <div className="code-head">
        <span className="mono">{path}</span>
        {lines != null && <span className="muted">{lines} 行</span>}
      </div>
      <div className="code-body mono">
        {rows.map((row, i) => {
          const no = i + 1
          return (
            <div key={i} className={no === highlightLine ? 'code-row hl' : 'code-row'}>
              <span className="lineno">{no}</span>
              <span className="code">{highlight(row)}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
