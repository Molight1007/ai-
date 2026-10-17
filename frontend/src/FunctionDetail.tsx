import type { FileNode, Flow, Module } from './types'

interface Props {
  module: Module
  file: FileNode
  nameOf: (id: string) => string
  flows: Flow[]
}

export function FunctionDetail({ module, file, nameOf, flows }: Props) {
  const relatedFlows = flows.filter((f) =>
    f.steps.some((s) => file.functions.some((fn) => fn.id === s)),
  )

  return (
    <div className="func-detail">
      <section className="fd-block">
        <div className="fd-headline">
          <span className="fd-title">{module.label}</span>
          {module.layer && <span className="fd-layer">{module.layer}</span>}
        </div>
        <p className="fd-desc">{module.description ?? module.summary}</p>
      </section>

      <section className="fd-block">
        <div className="fd-file mono">{file.path}</div>
        <p className="fd-desc">{file.description ?? file.summary}</p>
        {file.lines != null && <div className="fd-meta">约 {file.lines} 行</div>}
      </section>

      <section className="fd-block">
        <h3 className="fd-h">包含的功能</h3>
        {file.functions.map((fn) => (
          <div key={fn.id} className="fn-card">
            <div className="fn-name mono">{fn.name}</div>
            {fn.signature && <div className="fn-sig mono">{fn.signature}</div>}
            <p className="fn-desc">{fn.description ?? fn.summary}</p>
            {(fn.calls?.length || fn.called_by?.length) ? (
              <div className="fn-rel">
                {fn.calls?.length ? <span>调用：{fn.calls.map(nameOf).join('、')}</span> : null}
                {fn.called_by?.length ? <span>被调用：{fn.called_by.map(nameOf).join('、')}</span> : null}
              </div>
            ) : null}
          </div>
        ))}
      </section>

      {relatedFlows.length > 0 && (
        <section className="fd-block">
          <h3 className="fd-h">相关主流程</h3>
          {relatedFlows.map((f) => (
            <div key={f.id} className="flow-row">
              <span className="flow-label">{f.label}</span>
              <span className="flow-steps mono">{f.steps.map(nameOf).join(' → ')}</span>
            </div>
          ))}
        </section>
      )}
    </div>
  )
}
