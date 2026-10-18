import { useState } from 'react'

interface Props {
  initial?: string
  error?: string
  onAnalyze: (root: string) => void
  onDemo: () => void
}

export function ProjectInput({ initial, error, onAnalyze, onDemo }: Props) {
  const [value, setValue] = useState(initial ?? '')

  return (
    <div className="app">
      <div className="project-input">
        <div className="pi-title">AI 代码可视化</div>
        <div className="pi-sub">输入本地项目文件夹的绝对路径，分析其代码结构</div>
        <div className="pi-row">
          <input
            className="pi-field mono"
            placeholder="例如 D:/my-project 或 /home/user/code"
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
      </div>
    </div>
  )
}
