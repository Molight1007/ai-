// IR 类型定义 —— 对齐 backend/ir/schema.py 的契约 v2

export type Severity = 'error' | 'warning' | 'info'

export interface MetaStats {
  files?: number
  lines?: number
  functions?: number
  errors?: number
  warnings?: number
}

export interface Meta {
  project: string
  language: string
  generated_by: string
  generated_at?: string
  rules_version?: string
  stats?: MetaStats
  overview?: string
}

export interface Module {
  id: string
  label: string
  layer?: string
  summary?: string
  description?: string
  category?: string
  files: string[]
}

export interface FunctionNode {
  id: string
  name: string
  line?: number
  end_line?: number
  signature?: string
  summary?: string
  description?: string
  calls?: string[]
  called_by?: string[]
}

export interface FileNode {
  id: string
  path: string
  module: string
  language?: string
  lines?: number
  summary?: string
  description?: string
  category?: string
  functions: FunctionNode[]
}

export interface Dependency {
  from: string
  to: string
  type?: string
}

export interface Flow {
  id: string
  label: string
  steps: string[]
}

export interface RuleViolation {
  id: string
  rule: string
  node: string
  line?: number
  detail?: string
  suggestion?: string
  severity?: Severity
}

export interface Finding {
  id: string
  severity: Severity
  type?: string
  node: string
  line?: number
  title: string
  detail?: string
  suggestion?: string
}

export interface IR {
  schema_version: number
  meta: Meta
  modules: Module[]
  files: FileNode[]
  dependencies?: Dependency[]
  module_dependencies?: Dependency[]
  flows?: Flow[]
  capabilities?: Capability[]
  rule_violations?: RuleViolation[]
  findings?: Finding[]
}

export interface Capability {
  id: string
  label: string
  summary?: string
  nodes: CapabilityNode[]
}

export interface CapabilityNode {
  id: string
  label: string
  summary?: string
  detail?: string
  files: string[]
}
