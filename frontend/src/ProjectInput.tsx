import { useState } from 'react'

interface Props {
  initial?: string
  error?: string
  llmConfigured: boolean | null
  onAnalyze: (root: string) => void
  onPick: () => void
  onConfigureKey: (key: string) => void
  onDemo: () => void
  onShutdown: () => void
}

export function ProjectInput({
  initial,
  error,
  llmConfigured,
  onAnalyze,
  onPick,
  onConfigureKey,
  onDemo,
  onShutdown,
}: Props) {
  const [value, setValue] = useState(initial ?? '')
  const [keyValue, setKeyValue] = useState('')

  return (
    <div className="app">
      <div className="project-input">
        <div className="pi-title">AI 代码可视化</div>
        <div className="pi-sub">点一下按钮，自动审核代码并生成完整架构图</div>

        <div className="pi-card">
          <div className="pi-card-head">
            <span className="pi-card-title">① 配置 DeepSeek API Key</span>
            {llmConfigured === true && <span className="pi-badge pi-badge-ok">已配置</span>}
            {llmConfigured === false && <span className="pi-badge pi-badge-warn">未配置</span>}
            {llmConfigured === null && <span className="pi-badge">检测中…</span>}
          </div>
          {llmConfigured === false ? (
            <div className="pi-config">
              <input
                className="pi-key-input mono"
                placeholder="粘贴 DeepSeek API Key（sk-...）"
                value={keyValue}
                onChange={(e) => setKeyValue(e.target.value)}
              />
              <button
                className="pi-key-save"
                disabled={!keyValue.trim()}
                onClick={() => onConfigureKey(keyValue.trim())}
              >
                保存
              </button>
              <div className="pi-hint">Key 保存在本地 backend/llm.toml，不会提交到 GitHub</div>
            </div>
          ) : (
            <div className="pi-card-desc">已就绪，下一步选择项目文件夹即可</div>
          )}
        </div>

        <div className="pi-card">
          <div className="pi-card-head">
            <span className="pi-card-title">② 选择项目文件夹</span>
          </div>
          <div className="pi-card-desc">
            自动读取代码 + README → 定位 AI 代码板块 → 按规范生成架构图
          </div>
          <button
            className="pi-pick"
            onClick={onPick}
            disabled={llmConfigured !== true}
          >
            选择文件夹生成架构图
          </button>
          {llmConfigured !== true && (
            <div className="pi-hint">请先完成第 ① 步配置 API Key</div>
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
