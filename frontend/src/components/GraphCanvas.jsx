import { useMemo, useEffect } from 'react'
import {
  ReactFlow, Background, Controls,
  useReactFlow, ReactFlowProvider,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'
import CustomNode from './CustomNode'

const nodeTypes = { customNode: CustomNode }

function applyDagreLayout(nodes, edges) {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'TB', nodesep: 90, ranksep: 130, marginx: 50, marginy: 50 })
  nodes.forEach(n => g.setNode(n.id, { width: n.type === 'person' ? 148 : 168, height: n.type === 'person' ? 52 : 68 }))
  edges.forEach(e => g.setEdge(e.source, e.target))
  dagre.layout(g)
  return nodes.map(n => {
    const pos = g.node(n.id)
    return { ...n, position: { x: pos.x - (n.type === 'person' ? 74 : 84), y: pos.y - (n.type === 'person' ? 26 : 34) } }
  })
}

// Use backend spring_layout positions if available, Dagre only as fallback
function resolveLayout(nodes, edges) {
  const hasBackendPos = nodes.some(n => n.position != null)
  if (hasBackendPos) {
    // All nodes that got backend positions — use them directly
    // Any orphan without a position gets Dagre placement
    const dagreFallback = applyDagreLayout(nodes, edges)
    const dagreMap = Object.fromEntries(dagreFallback.map(n => [n.id, n.position]))
    return nodes.map(n => ({
      ...n,
      position: n.position ?? dagreMap[n.id] ?? { x: 0, y: 0 },
    }))
  }
  return applyDagreLayout(nodes, edges)
}

function toFlowNodes(apiNodes, apiEdges, activeFilters) {
  return resolveLayout(apiNodes, apiEdges).map(n => ({
    id: n.id, type: 'customNode', position: n.position,
    data: { label: n.label, type: n.type, jurisdiction: n.jurisdiction, risk_level: n.risk_level, risk_score: n.risk_score, tags: n.tags || [] },
    style: {
      opacity: activeFilters.length === 0 ? 1 : activeFilters.some(f => (n.tags || []).includes(f)) ? 1 : 0.15,
      transition: 'opacity 0.3s ease',
    },
  }))
}

function toFlowEdges(apiEdges) {
  return apiEdges.map(e => {
    // Color by trust: solid gold = API-verified | dashed orange = AI-extracted | dotted red = unverified
    const strokeColor = e.trust_score === 1.0 ? '#8B7CE8' : e.trust_score === 0.4 ? '#E8A848' : '#E06B5A'
    const strokeWidth = 2
    const strokeDash  = e.trust_score === 1.0 ? '0' : e.trust_score === 0.4 ? '8 5' : '4 4'
    return {
      id: e.id, source: e.source, target: e.target, type: 'smoothstep',
      label: e.ownership_pct != null ? `${e.ownership_pct}%` : e.label,
      labelStyle: { fill: '#E2D9CC', fontSize: 10, fontWeight: 600 },
      labelBgStyle: { fill: '#1C1814', fillOpacity: 0.95, rx: 6, ry: 6 },
      labelBgPadding: [4, 8],
      markerEnd: {
        type: 'arrowclosed',
        width: 14,
        height: 14,
        color: strokeColor,
      },
      style: {
        stroke: strokeColor,
        strokeWidth,
        strokeDasharray: strokeDash,
      },
      animated: e.trust_score === 0.0,
      data: e,
    }
  })
}

function GraphInner({ nodes, edges, activeFilters, focusNodeId, onEdgeClick, onPaneClick }) {
  const { setCenter } = useReactFlow()
  const flowNodes = useMemo(() => toFlowNodes(nodes, edges, activeFilters), [nodes, edges, activeFilters])
  const flowEdges = useMemo(() => toFlowEdges(edges), [edges])

  useEffect(() => {
    if (focusNodeId) {
      const node = flowNodes.find(n => n.id === focusNodeId)
      if (node) setCenter(node.position.x + 84, node.position.y + 34, { duration: 500, zoom: 1.6 })
    }
  }, [focusNodeId, flowNodes, setCenter])

  return (
    <div style={{ width: '100%', height: '100%', background: '#13111F', borderRadius: 0 }}>
      <ReactFlow
        nodes={flowNodes} edges={flowEdges} nodeTypes={nodeTypes}
        onEdgeClick={(_, edge) => onEdgeClick(edge.data)}
        onPaneClick={onPaneClick}
        fitView fitViewOptions={{ padding: 0.25 }}
        minZoom={0.25} maxZoom={3}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#252340" gap={28} size={1} />
        <Controls />
      </ReactFlow>
    </div>
  )
}

export default function GraphCanvas(props) {
  return (
    <ReactFlowProvider>
      <GraphInner {...props} />
    </ReactFlowProvider>
  )
}
