import { useState } from 'react'

interface Props {
  initial?: string
  error?: string
  onAnalyze: (root: string) => void
  onPick: () => void
  onPickEnrich: () => void
  onDemo: () => void
  onShutdown: () => void
}

export function ProjectInput({
  initial,
  error,
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
        <div className="pi-sub">选择或输入本地 Python 项目文件夹，分析其代码结构</div>

        <div className="pi-pick-row">
          <button className="pi-pick" onClick={onPick}>
            选择文件夹
          </button>
          <button className="pi-pick pi-pick-alt" onClick={onPickEnrich}>
            AI 增强分析
          </button>
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

        <div className="pi-demo" onClick={onDemo}>
          或查看内置示例数据
        </div>

        <div className="pi-shutdown" onClick={onShutdown}>
          终止服务
        </div>
      </div>
    </div>
  )
}
