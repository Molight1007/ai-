import { useEffect, useState } from 'react'
import { Diagram } from './Diagram'
import { CodePanel } from './CodePanel'
import { FunctionDetail } from './FunctionDetail'
import { IssuesPanel, type IssueItem } from './IssuesPanel'
import { analyzeFiles, configureLlm, loadIR, loadLlmStatus, shutdownServer, updateIr, type LlmConfig, type LlmStatus } from './api'
import { ProjectInput } from './ProjectInput'
import { pickDirectory } from './fs'
import { SAMPLE_IR } from './data'
import type { DiagramNode, DiagramEdge } from './layout'
import type { FileNode, IR, Module } from './types'

type View = 'code' | 'function' | 'review'

function basename(p: string): string {
  return p.split('/').pop() ?? p
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + '…' : s
}

const SEV_RANK: Record<string, number> = { error: 0, warning: 1, info: 2 }

const CACHE_PREFIX = 'aicodeviz_ir_'

function AnalyzingPane() {
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setElapsed((e) => e + 1), 1000)
    return () => clearInterval(t)
  }, [])
  const budget = 60
  const pct = Math.min(92, Math.round((elapsed / budget) * 92))
  const stage =
    elapsed < 2
      ? '读取文件…'
      : elapsed < 5
        ? '静态分析：结构抽取 / 规则违规…'
        : 'AI 分析：定位代码板块 / 模块职责 / 功能描述 / bug 排查…'
  return (
    <div className="analyzing">
      <div className="an-title">{stage}</div>
      <div className="an-bar">
        <div className="an-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="an-meta">已用时 {elapsed}s · 预计 {budget}s 内完成</div>
    </div>
  )
}

export default function App() {
  const [view, setView] = useState<View>('code')
  const [path, setPath] = useState<string[]>(['project'])
  const [hl, setHl] = useState<{ fileId: string; line?: number } | null>(null)
  const [root, setRoot] = useState<string | null>(null)
  const [ir, setIr] = useState<IR | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const saved = localStorage.getItem('theme')
    if (saved === 'light' || saved === 'dark') return saved
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })
  const [fileContent, setFileContent] = useState<Map<string, string> | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [llmStatus, setLlmStatus] = useState<LlmStatus | null>(null)

  useEffect(() => {
    loadLlmStatus().then((s) => setLlmStatus(s))
  }, [])

  function analyze(r: string) {
    setRoot(r)
    setIr(null)
    setError(null)
    loadIR(r).then(setIr).catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }

  function loadDemo() {
    setRoot(null)
    setIr(SAMPLE_IR)
    setError(null)
    setPath(['project'])
  }

  async function doPick() {
    setError(null)
    setAnalyzing(true)
    try {
      const { project, files: picked, readme } = await pickDirectory()
      if (!picked.length) {
        setError('所选目录没有 .py 文件')
        return
      }
      const fc = new Map(picked.map((f) => [f.path, f.content]))
      setFileContent(fc)
      setRoot(null)
      setIr(null)
      setPath(['project'])
      // 有上次架构图 → 增量更新；否则全量生成
      const cached = localStorage.getItem(CACHE_PREFIX + project)
      let ir: IR
      if (cached) {
        try {
          ir = await updateIr(picked, project, readme, JSON.parse(cached) as IR)
        } catch {
          ir = await analyzeFiles(picked, project, readme)
        }
      } else {
        ir = await analyzeFiles(picked, project, readme)
      }
      localStorage.setItem(CACHE_PREFIX + project, JSON.stringify(ir))
      setIr(ir)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setAnalyzing(false)
    }
  }

  async function configureKey(cfg: LlmConfig) {
    try {
      await configureLlm(cfg)
      const s = await loadLlmStatus()
      setLlmStatus(s)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  async function shutdown() {
    await shutdownServer()
    setError('服务已终止')
  }

  function backToInput() {
    setRoot(null)
    setIr(null)
    setError(null)
    setPath(['project'])
    setFileContent(null)
  }

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  if (analyzing) {
    return (
      <div className="app">
        <AnalyzingPane />
      </div>
    )
  }

  if (!ir) {
    if (error) {
      return <ProjectInput initial={root ?? ''} error={error} llmStatus={llmStatus} onAnalyze={analyze} onPick={doPick} onConfigureKey={configureKey} onDemo={loadDemo} onShutdown={shutdown} />
    }
    if (root === null) {
      return <ProjectInput llmStatus={llmStatus} onAnalyze={analyze} onPick={doPick} onConfigureKey={configureKey} onDemo={loadDemo} onShutdown={shutdown} />
    }
    return (
      <div className="app">
        <div className="loading">加载项目结构…</div>
      </div>
    )
  }

  const moduleMap = new Map(ir.modules.map((m) => [m.id, m]))
  const fileMap = new Map(ir.files.map((f) => [f.id, f]))

  // id -> 显示名
  const nameById = new Map<string, string>()
  ir.modules.forEach((m) => nameById.set(m.id, m.label))
  ir.files.forEach((f) => nameById.set(f.id, basename(f.path)))
  ir.files.forEach((f) => f.functions.forEach((fn) => nameById.set(fn.id, fn.name)))
  const nameOf = (id: string) => nameById.get(id) ?? id

  // node id -> 所属文件 / 模块
  const funcToFile = new Map<string, string>()
  ir.files.forEach((f) => f.functions.forEach((fn) => funcToFile.set(fn.id, f.id)))
  const fileToModule = new Map<string, string>()
  ir.files.forEach((f) => fileToModule.set(f.id, f.module))

  // ---- 合并 issues ----
  const issues: IssueItem[] = []
  for (const v of ir.rule_violations ?? []) {
    const fid = funcToFile.get(v.node) ?? v.node
    const file = fileMap.get(fid)
    if (!file) continue
    issues.push({
      id: v.id, severity: v.severity ?? 'warning', title: v.detail ?? v.rule,
      suggestion: v.suggestion, fileId: fid, line: v.line,
      location: `${basename(file.path)}${v.line ? ':' + v.line : ''}`,
    })
  }
  for (const f of ir.findings ?? []) {
    const fid = funcToFile.get(f.node) ?? f.node
    const file = fileMap.get(fid)
    if (!file) continue
    issues.push({
      id: f.id, severity: f.severity, title: f.title, detail: f.detail,
      suggestion: f.suggestion, fileId: fid, line: f.line,
      location: `${basename(file.path)}${f.line ? ':' + f.line : ''}`,
    })
  }
  issues.sort((a, b) => SEV_RANK[a.severity] - SEV_RANK[b.severity])

  // ---- 风险角标 ----
  const fileBadge = new Map<string, { errors: number; warnings: number }>()
  ir.files.forEach((f) => fileBadge.set(f.id, { errors: 0, warnings: 0 }))
  for (const it of issues) {
    const b = fileBadge.get(it.fileId)
    if (!b) continue
    if (it.severity === 'error') b.errors++
    else b.warnings++
  }
  const moduleBadge = new Map<string, { errors: number; warnings: number }>()
  ir.modules.forEach((m) => moduleBadge.set(m.id, { errors: 0, warnings: 0 }))
  for (const f of ir.files) {
    const b = fileBadge.get(f.id)
    const mb = moduleBadge.get(f.module)
    if (b && mb) {
      mb.errors += b.errors
      mb.warnings += b.warnings
    }
  }

  const errCount = issues.filter((i) => i.severity === 'error').length
  const warnCount = issues.length - errCount
  const totalLines = ir.files.reduce((s, f) => s + (f.lines ?? 0), 0)
  const totalFuncs = ir.files.reduce((s, f) => s + f.functions.length, 0)

  const level = path.length

  // ---- 面包屑 ----
  const crumbs: { label: string; path: string[] }[] = [
    { label: ir.meta.project, path: ['project'] },
  ]
  if (path[1]) {
    const m = moduleMap.get(path[1])
    if (m) crumbs.push({ label: m.label, path: ['project', m.id] })
  }
  if (path[2]) {
    const f = fileMap.get(path[2])
    if (f) crumbs.push({ label: basename(f.path), path: ['project', path[1], f.id] })
  }

  // ---- L1 ----
  const moduleNodes: DiagramNode[] = ir.modules.map((m) => ({
    id: m.id,
    label: m.label,
    sub:
      view === 'function'
        ? truncate(m.summary ?? '', 14)
        : m.layer
          ? `${m.layer} · ${m.files.length} 文件`
          : `${m.files.length} 文件`,
    layer: m.layer,
    width: view === 'function' ? 200 : 168,
    height: 56,
    badge: view === 'review' ? moduleBadge.get(m.id) : undefined,
  }))
  const moduleEdges: DiagramEdge[] = (ir.module_dependencies ?? []).map((d) => ({
    from: d.from,
    to: d.to,
  }))

  // ---- L2 ----
  let currentModule: Module | undefined
  let fileNodes: DiagramNode[] = []
  let fileEdges: DiagramEdge[] = []
  if (path[1]) {
    currentModule = moduleMap.get(path[1])
    if (currentModule) {
      const ids = new Set(currentModule.files)
      const files = currentModule.files
        .map((id) => fileMap.get(id))
        .filter((f): f is FileNode => !!f)
      fileNodes = files.map((f) => ({
        id: f.id,
        label: basename(f.path),
        sub:
          view === 'function'
            ? truncate(f.summary ?? '', 14)
            : f.lines
              ? `${f.lines} 行`
              : f.summary,
        width: view === 'function' ? 200 : 168,
        height: 56,
        badge: view === 'review' ? fileBadge.get(f.id) : undefined,
      }))
      fileEdges = (ir.dependencies ?? [])
        .filter((d) => ids.has(d.from) && ids.has(d.to))
        .map((d) => ({ from: d.from, to: d.to }))
    }
  }

  // ---- L3 ----
  let currentFile: FileNode | undefined
  if (path[2]) currentFile = fileMap.get(path[2])
  const hlLine = hl && currentFile && hl.fileId === currentFile.id ? hl.line : undefined

  const jumpToIssue = (it: IssueItem) => {
    const mid = fileToModule.get(it.fileId)
    if (mid) setPath(['project', mid, it.fileId])
    setHl({ fileId: it.fileId, line: it.line })
  }

  // ---- 主体内容 ----
  let content: JSX.Element | null = null
  if (level === 1) {
    content = (
      <div className="l2-wrap">
        {ir.meta.overview && (
          <div className="module-bar">
            <span className="module-bar-label">项目概述</span>
            <span className="module-bar-desc">{ir.meta.overview}</span>
          </div>
        )}
        <div className="diagram-wrap">
          <Diagram
            nodes={moduleNodes}
            edges={moduleEdges}
            selectedId={path[1]}
            search={search}
            onNodeClick={(id) => setPath(['project', id])}
          />
        </div>
      </div>
    )
  } else if (level === 2 && currentModule) {
    content = (
      <div className="l2-wrap">
        {view === 'function' && (
          <div className="module-bar">
            <span className="module-bar-label">
              {currentModule.label}
              {currentModule.layer ? ` · ${currentModule.layer}` : ''}
            </span>
            <span className="module-bar-desc">
              {currentModule.description ?? currentModule.summary}
            </span>
          </div>
        )}
        <div className="diagram-wrap">
          <Diagram
            nodes={fileNodes}
            edges={fileEdges}
            selectedId={path[2]}
            search={search}
            onNodeClick={(id) => setPath(['project', currentModule!.id, id])}
          />
        </div>
      </div>
    )
  } else if (level === 3 && currentModule && currentFile) {
    content = (
      <div className="diagram-wrap">
        {view === 'function' ? (
          <FunctionDetail
            module={currentModule}
            file={currentFile}
            nameOf={nameOf}
            flows={ir.flows ?? []}
          />
        ) : (
          <CodePanel
            path={currentFile.path}
            root={root}
            fileContent={fileContent}
            lines={currentFile.lines}
            highlightLine={hlLine}
          />
        )}
      </div>
    )
  }

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand">{ir.meta.project}</span>
        <span className="tag">{ir.meta.language}</span>
        <input
          className="search"
          placeholder="搜索节点…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="spacer" />
        <button
          className={view === 'code' ? 'tab active' : 'tab'}
          onClick={() => setView('code')}
        >
          代码方面
        </button>
        <button
          className={view === 'function' ? 'tab active' : 'tab'}
          onClick={() => setView('function')}
        >
          功能方面
        </button>
        <button
          className={view === 'review' ? 'tab active' : 'tab'}
          onClick={() => setView('review')}
        >
          审查模式
        </button>
        <button className="theme-btn" onClick={backToInput}>换项目</button>
        <button
          className="theme-btn"
          onClick={() => setTheme((t) => (t === 'light' ? 'dark' : 'light'))}
        >
          {theme === 'light' ? '深色' : '浅色'}
        </button>
      </header>

      <nav className="crumbs">
        {crumbs.map((c, i) => (
          <span key={i}>
            {i > 0 && <span className="sep">/</span>}
            <span className="crumb" onClick={() => setPath(c.path)}>
              {c.label}
            </span>
          </span>
        ))}
      </nav>

      <main className="stage">
        {view === 'review' && (
          <div className="stats-bar">
            <div className="stat"><div className="stat-label">文件</div><div className="stat-num">{ir.files.length}</div></div>
            <div className="stat"><div className="stat-label">代码行</div><div className="stat-num">{totalLines}</div></div>
            <div className="stat"><div className="stat-label">函数</div><div className="stat-num">{totalFuncs}</div></div>
            <div className="stat stat-err"><div className="stat-label">确定 bug</div><div className="stat-num">{errCount}</div></div>
            <div className="stat stat-warn"><div className="stat-label">规范违规</div><div className="stat-num">{warnCount}</div></div>
          </div>
        )}

        {view === 'review' ? (
          <div className="review-split">
            <div className="review-main">{content}</div>
            <IssuesPanel issues={issues} onJump={jumpToIssue} />
          </div>
        ) : (
          content
        )}
      </main>
    </div>
  )
}
