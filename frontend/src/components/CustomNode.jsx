import { Handle, Position } from '@xyflow/react'
import { getRiskColor } from '../constants/riskColors'

const TAG_CONFIG = {
  LOOP:     { bg: 'rgba(197,48,48,0.28)',  text: '#FC8181', border: 'rgba(197,48,48,0.6)',  symbol: '↻' },
  OFFSHORE: { bg: 'rgba(29,78,216,0.28)',  text: '#93C5FD', border: 'rgba(29,78,216,0.6)',  symbol: '⚓' },
  PUPPET:   { bg: 'rgba(194,65,12,0.28)',  text: '#FDBA74', border: 'rgba(194,65,12,0.6)',  symbol: '♟' },
  OFAC:     { bg: 'rgba(127,0,0,0.45)',    text: '#FCA5A5', border: 'rgba(197,48,48,0.7)',  symbol: '⚠' },
  DEAD_END: { bg: 'rgba(50,15,15,0.55)',   text: '#F87171', border: 'rgba(127,29,29,0.6)',  symbol: '✕' },
}

// Left-border accent color per risk level — makes nodes instantly scannable
const ACCENT = {
  AUTO_APPROVE: '#5CB87A',
  MEDIUM_RISK:  '#E8A848',
  HIGH_RISK:    '#8B7CE8',
  CRITICAL:     '#E06B5A',
}

export default function CustomNode({ data }) {
  const isPerson = data.type === 'person'
  const color  = getRiskColor(data.risk_level)
  const accent = ACCENT[data.risk_level] ?? '#4A4238'

  const width  = isPerson ? 152 : 172
  const height = isPerson ? 56  : 72
  const radius = isPerson ? 28  : 10

  const pulseClass = color.pulse
    ? data.risk_level === 'CRITICAL' ? 'pulse-critical' : 'pulse-high'
    : ''

  const tags = (data.tags || []).filter(t => TAG_CONFIG[t])

  return (
    <div
      className={pulseClass}
      style={{
        width, height,
        borderRadius: radius,
        background: color.bg,
        border: `1.5px solid ${color.border}`,
        borderLeft: `3px solid ${accent}`,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        position: 'relative',
        padding: '0 14px 0 16px',
        cursor: 'pointer',
        transition: 'transform 0.15s ease, border-color 0.15s ease',
        boxShadow: `0 4px 20px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.04)`,
      }}
    >
      {/* Flow IN — connections arrive at top */}
      <Handle type="target" position={Position.Top}
        style={{ width: 8, height: 8, background: accent, border: `1.5px solid ${color.border}`, borderRadius: '50%', top: -4 }} />

      {/* Tag badges */}
      {tags.length > 0 && (
        <div style={{
          position: 'absolute', top: -8, right: -4,
          display: 'flex', gap: 3, flexDirection: 'row-reverse',
        }}>
          {tags.map(tag => {
            const cfg = TAG_CONFIG[tag]
            return (
              <div key={tag} title={tag} style={{
                width: 16, height: 16, borderRadius: '50%',
                background: cfg.bg, color: cfg.text,
                border: `1px solid ${cfg.border}`,
                fontSize: 8, fontWeight: 700,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                backdropFilter: 'blur(4px)',
              }}>
                {cfg.symbol}
              </div>
            )
          })}
        </div>
      )}

      {/* Label */}
      <div style={{
        color: '#F0EAE0', fontSize: 11, fontWeight: 600,
        textAlign: 'center', width: '100%',
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        letterSpacing: '0.01em',
      }}>
        {isPerson ? '👤 ' : '🏢 '}{data.label}
      </div>

      {/* Jurisdiction */}
      <div style={{
        color: '#A89E90', fontSize: 9.5, marginTop: 3,
        textAlign: 'center', width: '100%',
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
      }}>
        {data.jurisdiction}
      </div>

      {/* Flow OUT — arrows leave from bottom */}
      <Handle type="source" position={Position.Bottom}
        style={{ width: 8, height: 8, background: accent, border: `1.5px solid ${color.border}`, borderRadius: '50%', bottom: -4 }} />
    </div>
  )
}
