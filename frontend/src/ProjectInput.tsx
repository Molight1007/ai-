import { useState } from 'react'
import type { LlmConfig } from './api'

interface Provider {
  name: string
  base_url: string
  models: string[]
  note?: string
}

const PROVIDERS: Provider[] = [
  {
    name: 'DeepSeek',
    base_url: 'https://api.deepseek.com',
    models: ['deepseek-chat', 'deepseek-reasoner', 'deepseek-v4-pro', 'deepseek-v4-flash', 'deepseek-v4.1-flash'],
  },
  {
    name: '通义千问 Qwen',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: ['qwen3-coder-plus', 'qwen-coder-plus', 'qwen-plus'],
  },
  {
    name: '智谱 GLM',
    base_url: 'https://open.bigmodel.cn/api/paas/v4',
    models: ['glm-5', 'glm-4.5', 'glm-4-flash'],
  },
  {
    name: 'Kimi（月之暗面）',
    base_url: 'https://api.moonshot.cn/v1',
    models: ['kimi-k2', 'moonshot-v1-8k'],
  },
  {
    name: 'MiniMax',
    base_url: 'https://api.minimaxi.com/v1',
    models: ['MiniMax-M3', 'MiniMax-M2.5'],
  },
  {
    name: '腾讯混元',
    base_url: 'https://api.hunyuan.cloud.tencent.com/v1',
    models: ['hunyuan-turbo', 'hunyuan-pro'],
  },
  {
    name: '文心 ERNIE（百度千帆）',
    base_url: 'https://qianfan.baidubce.com/v2',
    models: ['ernie-4.0-8k', 'ernie-3.5-8k'],
  },
  {
    name: '讯飞星火',
    base_url: 'https://spark-api-open.xf-yun.com/v1',
    models: ['4.0Ultra', 'generalv3.5'],
  },
  {
    name: '阶跃星辰 Step',
    base_url: 'https://api.stepfun.com/v1',
    models: ['step-2', 'step-1.5v'],
  },
  {
    name: '百川 Baichuan',
    base_url: 'https://api.baichuan-ai.com/v1',
    models: ['Baichuan4', 'Baichuan3-Turbo'],
  },
  {
    name: '豆包（火山方舟）',
    base_url: 'https://ark.cn-beijing.volces.com/api/v3',
    models: [],
    note: '需先在火山方舟控制台创建「推理接入点」，模型处填接入点 ID（如 ep-xxx）',
  },
  { name: '自定义（任意 OpenAI 兼容端点）', base_url: '', models: [] },
]

interface Props {
  initial?: string
  error?: string
  llmConfigured: boolean | null
  onAnalyze: (root: string) => void
  onPick: () => void
  onConfigureKey: (cfg: LlmConfig) => void
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
  const [providerIdx, setProviderIdx] = useState(0)
  const [baseUrl, setBaseUrl] = useState(PROVIDERS[0].base_url)
  const [model, setModel] = useState(PROVIDERS[0].models[0])
  const [keyValue, setKeyValue] = useState('')
  const [showConfig, setShowConfig] = useState(false)

  function onProviderChange(i: number) {
    setProviderIdx(i)
    setBaseUrl(PROVIDERS[i].base_url)
    setModel(PROVIDERS[i].models[0] ?? '')
  }

  function save() {
    onConfigureKey({ api_key: keyValue.trim(), model: model.trim(), base_url: baseUrl.trim() })
  }

  const needConfig = llmConfigured === false || (llmConfigured === true && showConfig)

  return (
    <div className="app">
      <div className="project-input">
        <div className="pi-title">AI 代码可视化</div>
        <div className="pi-sub">点一下按钮，自动审核代码并生成完整架构图</div>

        <div className="pi-card">
          <div className="pi-card-head">
            <span className="pi-card-title">① 配置大模型</span>
            {llmConfigured === true && !showConfig && <span className="pi-badge pi-badge-ok">已配置</span>}
            {llmConfigured === false && <span className="pi-badge pi-badge-warn">未配置</span>}
            {llmConfigured === null && <span className="pi-badge">检测中…</span>}
          </div>

          {needConfig ? (
            <div className="pi-config">
              <div className="pi-field-label">服务商</div>
              <select
                className="pi-select"
                value={providerIdx}
                onChange={(e) => onProviderChange(Number(e.target.value))}
              >
                {PROVIDERS.map((p, i) => (
                  <option key={i} value={i}>
                    {p.name}
                  </option>
                ))}
              </select>
              {PROVIDERS[providerIdx].note && (
                <div className="pi-hint">{PROVIDERS[providerIdx].note}</div>
              )}

              <div className="pi-field-label">Base URL</div>
              <input
                className="pi-key-input mono"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="OpenAI 兼容端点"
              />

              <div className="pi-field-label">模型</div>
              <input
                className="pi-key-input mono"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="模型名"
                list="model-options"
              />
              <datalist id="model-options">
                {PROVIDERS[providerIdx].models.map((m) => (
                  <option key={m} value={m} />
                ))}
              </datalist>

              <div className="pi-field-label">API Key</div>
              <input
                className="pi-key-input mono"
                type="password"
                value={keyValue}
                onChange={(e) => setKeyValue(e.target.value)}
                placeholder="sk-..."
              />

              <button className="pi-key-save" disabled={!keyValue.trim()} onClick={save}>
                保存
              </button>
              <div className="pi-hint">配置保存在本地 backend/llm.toml，不会提交到 GitHub</div>
            </div>
          ) : (
            <div className="pi-card-desc">
              已就绪，下一步选择项目文件夹即可
              <span className="pi-relink" onClick={() => setShowConfig(true)}>
                重新配置
              </span>
            </div>
          )}
        </div>

        <div className="pi-card">
          <div className="pi-card-head">
            <span className="pi-card-title">② 选择项目文件夹</span>
          </div>
          <div className="pi-card-desc">
            自动读取代码 + README → 定位 AI 代码板块 → 按规范生成架构图
          </div>
          <button className="pi-pick" onClick={onPick} disabled={llmConfigured !== true}>
            选择文件夹生成架构图
          </button>
          {llmConfigured !== true && <div className="pi-hint">请先完成第 ① 步配置大模型</div>}
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
