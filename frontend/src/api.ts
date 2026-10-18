// 数据源统一入口：带 root（用户选择的本地项目目录）请求后端。
// root 为空时回退到内置示例数据（便于无后端时预览）。

import { FILE_CONTENTS, SAMPLE_IR } from './data'
import type { IR } from './types'

export async function loadIR(root: string | null): Promise<IR> {
  if (!root) return SAMPLE_IR
  const res = await fetch(`/api/ir?root=${encodeURIComponent(root)}`)
  if (!res.ok) {
    throw new Error(`加载项目失败（${res.status}）`)
  }
  const data = await res.json()
  if (data && Array.isArray(data.modules) && Array.isArray(data.files)) {
    return data as IR
  }
  if (data && data.error) throw new Error(data.error)
  throw new Error('返回数据格式不符')
}

export async function loadFile(root: string | null, path: string): Promise<string> {
  if (!root) return FILE_CONTENTS[path] ?? ''
  const res = await fetch(
    `/api/file?root=${encodeURIComponent(root)}&path=${encodeURIComponent(path)}`,
  )
  if (!res.ok) return ''
  const data = await res.json()
  return typeof data.content === 'string' ? data.content : ''
}
