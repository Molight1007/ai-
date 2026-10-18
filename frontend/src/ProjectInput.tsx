import { useState } from 'react'

interface Props {
  initial?: string
  error?: string
  llmConfigured: boolean | null
  onAnalyze: (root: string) => void
  onPick: () => void
  onPickEnrich: () => void
  onDemo: () => void
  onShutdown: () => void
}

export function ProjectInput({
  initial,
  error,
  llmConfigured,
  onAnalyze,
  onPick,
  onPickEnrich,
  onDemo,
  onShutdown,
}: Props) {
  const [value, setValue] = useState(initial ?? '')

  return (
    <div className="app">
      <div className="project-input">
        <div className="pi-title">AI 代码可视化</div>
        <div className="pi-sub">把 AI 生成的 Python 代码变成可交互架构图</div>

        <div className="pi-card">
          <div className="pi-card-head">
            <span className="pi-card-title">快速分析</span>
            <span className="pi-badge pi-badge-ok">无需配置</span>
          </div>
          <div className="pi-card-desc">静态扫描代码结构 + 规则违规检测，不调用 AI，秒出结果</div>
          <button className="pi-pick" onClick={onPick}>
            选择文件夹
          </button>
        </div>

        <div className="pi-card">
          <div className="pi-card-head">
            <span className="pi-card-title">AI 增强分析</span>
            {llmConfigured === true && <span className="pi-badge pi-badge-ok">已配置</span>}
            {llmConfigured === false && <span className="pi-badge pi-badge-warn">未配置 Key</span>}
            {llmConfigured === null && <span className="pi-badge">检测中…</span>}
          </div>
          <div className="pi-card-desc">调用大模型补全模块职责、功能说明、语义 bug 排查</div>
          <button className="pi-pick pi-pick-alt" onClick={onPickEnrich}>
            选择文件夹并增强
          </button>
          {llmConfigured === false && (
            <div className="pi-hint">
              需在 backend/llm.toml 填入 DeepSeek API Key（或设置环境变量 LLM_API_KEY）
            </div>
          )}
        </div>

        <div className="pi-divider">或手动输入路径</div>

        <div className="pi-row">
          <input
            className="pi-field mono"
            placeholder="例如 D:/my-project"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && value.trim()) onAnalyze(value.trim())
            }}
          />
          <button
            className="pi-btn"
            disabled={!value.trim()}
            onClick={() => onAnalyze(value.trim())}
          >
            分析
          </button>
        </div>

        {error && <div className="pi-error">{error}</div>}

        <div className="pi-foot">
          <span className="pi-demo" onClick={onDemo}>
            查看内置示例
          </span>
          <span className="pi-shutdown" onClick={onShutdown}>
            终止服务
          </span>
        </div>
      </div>
    </div>
  )
}
