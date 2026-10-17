// 数据源统一入口：优先走后端接口，失败时回退到内置 mock（便于无后端时预览）。

import { FILE_CONTENTS, SAMPLE_IR } from './data'
import type { IR } from './types'

export async function loadIR(): Promise<IR> {
  try {
    const res = await fetch('/api/ir')
    if (res.ok) {
      const data = await res.json()
      if (data && Array.isArray(data.modules) && Array.isArray(data.files)) {
        return data as IR
      }
    }
  } catch {
    // 后端未启动 → 回退 mock
  }
  return SAMPLE_IR
}

export async function loadFile(path: string): Promise<string> {
  try {
    const res = await fetch(`/api/file?path=${encodeURIComponent(path)}`)
    if (res.ok) {
      const data = await res.json()
      if (typeof data.content === 'string') return data.content
    }
  } catch {
    // 后端未启动 → 回退 mock
  }
  return FILE_CONTENTS[path] ?? ''
}
