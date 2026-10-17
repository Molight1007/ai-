export interface IssueItem {
  id: string
  severity: 'error' | 'warning' | 'info'
  title: string
  detail?: string
  suggestion?: string
  fileId: string
  line?: number
  location: string
}

const SEV_META: Record<
  IssueItem['severity'],
  { label: string; color: string; border: string; bg: string }
> = {
  error: { label: 'bug', color: '#A32D2D', border: '#E24B4A', bg: '#FCEBEB' },
  warning: { label: '警告', color: '#854F0B', border: '#EF9F27', bg: '#FAEEDA' },
  info: { label: '提示', color: '#5F5E5A', border: '#888780', bg: '#F1EFE8' },
}

interface Props {
  issues: IssueItem[]
  onJump: (issue: IssueItem) => void
}

export function IssuesPanel({ issues, onJump }: Props) {
  const errors = issues.filter((i) => i.severity === 'error').length
  const warns = issues.length - errors

  return (
    <div className="issues-panel">
      <div className="issues-head">
        <span>问题清单</span>
        <span className="issues-count">
          {errors} bug · {warns} 警告
        </span>
      </div>
      <div className="issues-body">
        {issues.length === 0 && <div className="issues-empty">无问题</div>}
        {issues.map((it) => {
          const m = SEV_META[it.severity]
          return (
            <div
              key={it.id}
              className="issue-card"
              style={{ borderLeft: `3px solid ${m.border}` }}
              onClick={() => onJump(it)}
            >
              <div className="issue-title">
                <span className="issue-badge" style={{ background: m.bg, color: m.color }}>
                  {m.label}
                </span>
                <span className="issue-loc mono">{it.location}</span>
              </div>
              <div className="issue-text">{it.title}</div>
              {it.suggestion && <div className="issue-sug">建议：{it.suggestion}</div>}
            </div>
          )
        })}
      </div>
    </div>
  )
}
