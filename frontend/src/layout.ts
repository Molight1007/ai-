// dagre 分层布局封装：输入节点/边，输出带坐标的节点 + 带折线点的边。

import * as dagre from '@dagrejs/dagre'

export interface DiagramNode {
  id: string
  label: string
  sub?: string
  layer?: string
  width: number
  height: number
  badge?: { errors: number; warnings: number }
}

export interface DiagramEdge {
  from: string
  to: string
  label?: string
}

export interface PlacedNode extends DiagramNode {
  x: number
  y: number
}

export interface PlacedEdge extends DiagramEdge {
  points: { x: number; y: number }[]
}

export interface LayoutResult {
  nodes: PlacedNode[]
  edges: PlacedEdge[]
  width: number
  height: number
}

export function layoutNodes(
  nodes: DiagramNode[],
  edges: DiagramEdge[],
  direction: 'LR' | 'TB' = 'LR',
): LayoutResult {
  const g = new dagre.graphlib.Graph()
  g.setGraph({
    rankdir: direction,
    nodesep: 44,
    ranksep: 90,
    marginx: 24,
    marginy: 24,
  })
  g.setDefaultEdgeLabel(() => ({}))

  for (const n of nodes) {
    g.setNode(n.id, { width: n.width, height: n.height })
  }
  for (const e of edges) {
    g.setEdge(e.from, e.to)
  }

  dagre.layout(g)

  const placed: PlacedNode[] = nodes.map((n) => {
    const p = g.node(n.id)
    return { ...n, x: p.x - n.width / 2, y: p.y - n.height / 2 }
  })

  const placedEdges: PlacedEdge[] = edges.map((e) => {
    const ge = g.edge(e.from, e.to)
    return { ...e, points: ge.points ?? [] }
  })

  let width = 0
  let height = 0
  for (const n of placed) {
    width = Math.max(width, n.x + n.width)
    height = Math.max(height, n.y + n.height)
  }
  width += 24
  height += 24

  return { nodes: placed, edges: placedEdges, width, height }
}
