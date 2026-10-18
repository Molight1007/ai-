// 用 File System Access API 点选本地文件夹，遍历读取 .py 文件内容。
// 仅 Chrome / Edge 支持；不支持时抛错由调用方兜底。

export interface ProjectFile {
  path: string
  content: string
}

export async function pickDirectory(): Promise<{ project: string; files: ProjectFile[] }> {
  const w = window as unknown as { showDirectoryPicker?: () => Promise<any> }
  if (typeof w.showDirectoryPicker !== 'function') {
    throw new Error('当前浏览器不支持文件夹选择（需 Chrome/Edge）')
  }
  const handle = await w.showDirectoryPicker()
  const files: ProjectFile[] = []
  await walk(handle, '', files)
  return { project: handle.name, files }
}

async function walk(dirHandle: any, prefix: string, out: ProjectFile[]) {
  for await (const entry of dirHandle.values()) {
    const rel = prefix ? `${prefix}/${entry.name}` : entry.name
    if (entry.kind === 'file') {
      if (entry.name.endsWith('.py')) {
        const file = await entry.getFile()
        out.push({ path: rel, content: await file.text() })
      }
    } else if (entry.kind === 'directory') {
      await walk(entry, rel, out)
    }
  }
}
