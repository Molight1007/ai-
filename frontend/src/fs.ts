// 用 File System Access API 点选本地文件夹，遍历读取 .py 文件内容 + 根目录 README。
// 仅 Chrome / Edge 支持；不支持时抛错由调用方兜底。
// 非代码文件（图片/文档/配置等）自动忽略。

export interface ProjectFile {
  path: string
  content: string
}

export async function pickDirectory(): Promise<{
  project: string
  files: ProjectFile[]
  readme?: string
}> {
  const w = window as unknown as { showDirectoryPicker?: () => Promise<any> }
  if (typeof w.showDirectoryPicker !== 'function') {
    throw new Error('当前浏览器不支持文件夹选择（需 Chrome/Edge）')
  }
  const handle = await w.showDirectoryPicker()
  const files: ProjectFile[] = []
  let readme: string | undefined
  await walk(handle, '', files, (c) => {
    if (!readme) readme = c
  })
  return { project: handle.name, files, readme }
}

function isReadmeName(name: string): boolean {
  const n = name.toLowerCase()
  return n === 'readme.md' || n === 'readme.txt' || n === 'readme' || n.startsWith('readme.')
}

async function walk(
  dirHandle: any,
  prefix: string,
  out: ProjectFile[],
  onReadme: (content: string) => void,
) {
  for await (const entry of dirHandle.values()) {
    const rel = prefix ? `${prefix}/${entry.name}` : entry.name
    if (entry.kind === 'file') {
      if (entry.name.endsWith('.py')) {
        const file = await entry.getFile()
        out.push({ path: rel, content: await file.text() })
      } else if (!prefix && isReadmeName(entry.name)) {
        const file = await entry.getFile()
        onReadme(await file.text())
      }
    } else if (entry.kind === 'directory') {
      await walk(entry, rel, out, onReadme)
    }
  }
}
