import { useRef, useState } from 'react'
import type { DiagramNode, DiagramEdge } from './layout'
import { layoutNodes } from './layout'

// 按层着色（浅色主题：50 填充 + 600 描边 + 800 标题）
const LAYER_STYLE: Record<string, { fill: string; stroke: string; text: string; sub: string }> = {
  L5: { fill: '#EEEDFE', stroke: '#534AB7', text: '#3C3489', sub: '#534AB7' },
  L4: { fill: '#E6F1FB', stroke: '#185FA5', text: '#0C447C', sub: '#185FA5' },
  L3: { fill: '#FAEEDA', stroke: '#854F0B', text: '#633806', sub: '#854F0B' },
  L2: { fill: '#EAF3DE', stroke: '#3B6D11', text: '#27500A', sub: '#3B6D11' },
  L1: { fill: '#F1EFE8', stroke: '#888780', text: '#444441', sub: '#888780' },
  L0: { fill: '#F1EFE8', stroke: '#888780', text: '#444441', sub: '#888780' },
}

const NEUTRAL = { fill: '#F1EFE8', stroke: '#888780', text: '#444441', sub: '#888780' }

interface Props {
  nodes: DiagramNode[]
  edges: DiagramEdge[]
  selectedId?: string
  search?: string
  onNodeClick: (id: string) => void
}

export function Diagram({ nodes, edges, selectedId, search, onNodeClick }: Props) {
  const { nodes: placed, edges: placedEdges, width, height } = layoutNodes(nodes, edges)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const svgRef = useRef<SVGSVGElement>(null)

  const dragStart = useRef<{ x: number; y: number; px: number; py: number } | null>(null)
  const moved = useRef(false)
  const query = (search ?? '').toLowerCase()

  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15
    setZoom((z) => Math.min(4, Math.max(0.1, z * factor)))
  }

  const onMouseDown = (e: React.MouseEvent) => {
    dragStart.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y }
    moved.current = false
  }
  const onMouseMove = (e: React.MouseEvent) => {
    if (!dragStart.current) return
    const dx = e.clientX - dragStart.current.x
    const dy = e.clientY - dragStart.current.y
    if (Math.abs(dx) + Math.abs(dy) > 3) moved.current = true
    setPan({ x: dragStart.current.px + dx, y: dragStart.current.py + dy })
  }
  const onMouseUp = () => {
    dragStart.current = null
  }

  const fit = () => {
    setZoom(1)
    setPan({ x: 0, y: 0 })
  }

  const exportSvg = () => {
    const svg = svgRef.current
    if (!svg) return
    const xml = new XMLSerializer().serializeToString(svg)
    const blob = new Blob([xml], { type: 'image/svg+xml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'diagram.svg'
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleNodeClick = (id: string) => {
    if (moved.current) return
    onNodeClick(id)
  }

  return (
    <div className="diagram-zoom">
      <div className="zoom-controls">
        <button onClick={() => setZoom((z) => Math.min(4, z * 1.2))} title="放大">+</button>
        <button onClick={() => setZoom((z) => Math.max(0.1, z / 1.2))} title="缩小">−</button>
        <button onClick={fit} title="适应">适应</button>
        <button onClick={exportSvg} title="导出 SVG">导出</button>
      </div>
      <div
        className="zoom-pane"
        onWheel={onWheel}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
      >
        <svg
          ref={svgRef}
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          style={{
            display: 'block',
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: '0 0',
          }}
          role="img"
        >
          <defs>
            <marker
              id="arrow"
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path
                d="M2 1L8 5L2 9"
                fill="none"
                stroke="context-stroke"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </marker>
          </defs>

          {placedEdges.map((e, i) => (
            <polyline
              key={i}
              points={e.points.map((p) => `${p.x},${p.y}`).join(' ')}
              fill="none"
              stroke="#B4B2A9"
              strokeWidth="1.5"
              markerEnd="url(#arrow)"
            />
          ))}

          {placed.map((n) => {
            const s = LAYER_STYLE[n.layer ?? ''] ?? NEUTRAL
            const selected = n.id === selectedId
            const dimmed = query !== '' && !n.label.toLowerCase().includes(query)
            const showErr = (n.badge?.errors ?? 0) > 0
            const showWarn = (n.badge?.warnings ?? 0) > 0
            return (
              <g
                key={n.id}
                transform={`translate(${n.x},${n.y})`}
                onClick={() => handleNodeClick(n.id)}
                opacity={dimmed ? 0.3 : 1}
                style={{ cursor: 'pointer' }}
              >
                <rect
                  width={n.width}
                  height={n.height}
                  rx={10}
                  fill={s.fill}
                  stroke={selected ? '#378ADD' : s.stroke}
                  strokeWidth={selected ? 2 : 1}
                />
                <text
                  x={n.width / 2}
                  y={n.sub ? n.height / 2 - 6 : n.height / 2}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={13}
                  fontWeight={500}
                  fill={s.text}
                >
                  {n.label}
                </text>
                {n.sub && (
                  <text
                    x={n.width / 2}
                    y={n.height / 2 + 14}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize={11}
                    fill={s.sub}
                  >
                    {n.sub}
                  </text>
                )}
                {showErr && (
                  <g transform={`translate(${n.width - 10}, 10)`}>
                    <circle r={9} fill="#E24B4A" />
                    <text textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={500} fill="#fff">
                      {n.badge!.errors}
                    </text>
                  </g>
                )}
                {showWarn && (
                  <g transform={`translate(${n.width - (showErr ? 30 : 10)}, 10)`}>
                    <circle r={9} fill="#EF9F27" />
                    <text textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={500} fill="#fff">
                      {n.badge!.warnings}
                    </text>
                  </g>
                )}
              </g>
            )
          })}
        </svg>
      </div>
    </div>
  )
}
