import { useState } from 'react'
import GraphCanvas from './GraphCanvas'
import EvidencePanel from './EvidencePanel'
import RiskScoreboard from './RiskScoreboard'
import EntitySidebar from './EntitySidebar'

// ─── MOCK DATA (removed) ──────────────────────────────────────────────────────

export default function InvestigationView({ data, crn = '', onReset = () => {} }) {
  const [selectedEdge,   setSelectedEdge]   = useState(null)
  const [selectedNodeId, setSelectedNodeId] = useState(null)
  const [activeFilters,  setActiveFilters]  = useState([])

  const targetName = data.graph?.nodes?.[0]?.label || data.resolved_ubo || 'Investigation'
  const panelWidth = selectedEdge ? 300 : 0

  return (
    <div style={{
      width: '100vw', height: '100vh',
      display: 'flex', flexDirection: 'column',
      background: '#0D0B09', overflow: 'hidden',
    }}>

      {/* ── Top bar ─────────────────────────────────────────────────────────── */}
      <div style={{
        height: 52,
        background: 'rgba(21, 18, 16, 0.95)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderBottom: '1px solid #1E1B15',
        display: 'flex', alignItems: 'center',
        flexShrink: 0, zIndex: 20,
        padding: '0 16px',
        gap: 0,
      }}>

        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginRight: 16 }}>
          {/* Icon mark */}
          <div style={{
            width: 28, height: 28, borderRadius: 8,
            background: 'linear-gradient(135deg, #C53030 0%, #7C3AED 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 13, fontWeight: 800, color: '#fff',
            letterSpacing: '-0.03em', flexShrink: 0,
            boxShadow: '0 2px 8px rgba(197,48,48,0.4)',
          }}>U</div>
          <span style={{
            color: '#F0EAE0', fontSize: 13, fontWeight: 700,
            letterSpacing: '0.14em',
          }}>UNSHELL</span>
        </div>

        {/* Divider */}
        <div style={{ width: 1, height: 18, background: '#2C271F', marginRight: 16 }} />

        {/* Target */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginRight: 'auto' }}>
          <span style={{ color: '#625C52', fontSize: 11 }}>Investigating</span>
          <span style={{
            background: '#1C1814', border: '1px solid #2C271F',
            color: '#A89E90', fontSize: 11, fontWeight: 500,
            padding: '2px 10px', borderRadius: 9999,
          }}>
            {targetName}
          </span>
          {crn && (
            <span style={{
              background: 'transparent', border: '1px solid #2C271F',
              color: '#4A4238', fontSize: 10, fontWeight: 600,
              padding: '2px 8px', borderRadius: 9999, letterSpacing: '0.08em',
              fontFamily: 'monospace',
            }}>
              #{crn}
            </span>
          )}
        </div>

        {/* Compact scoreboard + UBO in top bar */}
        <RiskScoreboard
          compact
          riskScore={data.risk_score}
          riskLabel={data.risk_label}
          resolvedUbo={data.resolved_ubo}
          sanctionsHit={data.sanctions_hit}
        />

        {/* Divider */}
        <div style={{ width: 1, height: 18, background: '#2C271F', margin: '0 16px' }} />

        {/* CTA */}
        <button
          onClick={onReset}
          style={{
            background: '#1C1814', border: '1px solid #302B22',
            color: '#A89E90', fontSize: 12, fontWeight: 500,
            padding: '6px 16px', borderRadius: 9999,
            cursor: 'pointer', fontFamily: 'inherit',
            transition: 'all 0.18s ease', letterSpacing: '0.01em',
            whiteSpace: 'nowrap',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = '#242018'
            e.currentTarget.style.borderColor = '#4A4238'
            e.currentTarget.style.color = '#F0EAE0'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = '#1C1814'
            e.currentTarget.style.borderColor = '#302B22'
            e.currentTarget.style.color = '#A89E90'
          }}
        >
          New Investigation
        </button>
      </div>

      {/* ── 3-column grid ───────────────────────────────────────────────────── */}
      <div style={{
        flex: 1, minHeight: 0,
        display: 'grid',
        gridTemplateColumns: `220px 1fr ${panelWidth}px`,
        transition: 'grid-template-columns 0.28s cubic-bezier(0.4,0,0.2,1)',
        overflow: 'hidden',
      }}>
        <EntitySidebar
          nodes={data.graph.nodes}
          stats={data.stats}
          fatalFlags={data.fatal_flags}
          resolvedUbo={data.resolved_ubo}
          activeFilters={activeFilters}
          onFilterChange={setActiveFilters}
          onEntityClick={id => setSelectedNodeId(id)}
        />

        <GraphCanvas
          nodes={data.graph.nodes}
          edges={data.graph.edges}
          activeFilters={activeFilters}
          focusNodeId={selectedNodeId}
          onEdgeClick={edge => setSelectedEdge(edge)}
          onPaneClick={() => setSelectedEdge(null)}
        />

        <div style={{ overflow: 'hidden' }}>
          {selectedEdge && (
            <EvidencePanel
              edge={selectedEdge}
              nodes={data.graph.nodes}
              stats={data.stats}
              onClose={() => setSelectedEdge(null)}
            />
          )}
        </div>
      </div>

      {/* ── Bottom scoreboard ────────────────────────────────────────────────── */}
      {/* 
      <RiskScoreboard
        riskScore={data.risk_score}
        riskLabel={data.risk_label}
        fatalFlags={data.fatal_flags}
        cumulativeVectors={data.cumulative_vectors}
        confidence={data.confidence ?? null}
        sanctionsHit={data.sanctions_hit}
        sanctionsDetail={data.sanctions_detail}
        resolvedUbo={data.resolved_ubo}
      />
      */}
    </div>
  )
}
