import { useState, useRef } from 'react'

const CRN_DEMOS = [
  { label: 'Monzo', crn: '09446231', tag: 'Fintech' },
  { label: 'IBS', crn: '01683457', tag: 'Finance' },
  { label: 'Seabon', crn: '06026625', tag: '⚠ High Risk' },
]

// UK CRN format: 8 digits, or 2-letter prefix + 6 digits (SC, NI, OC, SO, NC, R etc.)
const CRN_REGEX = /^([A-Z]{2}\d{6}|\d{8})$/i

function ErrorModal({ message, onClose }) {
  if (!message) return null
  const isRateLimit = message.toLowerCase().includes('rate limit') || message.toLowerCase().includes('quota')
  const isNotFound = message.toLowerCase().includes('not found')
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#fff', borderRadius: 16, padding: '32px 36px',
          maxWidth: 420, width: '90%', boxShadow: '0 24px 80px rgba(0,0,0,0.25)',
          border: `2px solid ${isRateLimit ? '#ff9800' : '#e06b5a'}`,
          textAlign: 'center',
          animation: 'fadeInScale 0.18s ease',
        }}
      >
        <div style={{ fontSize: 40, marginBottom: 12 }}>
          {isRateLimit ? '⏳' : isNotFound ? '🔍' : '⚠️'}
        </div>
        <div style={{ fontSize: 17, fontWeight: 700, color: '#1a1a2e', marginBottom: 10 }}>
          {isRateLimit ? 'API Rate Limit Reached' : isNotFound ? 'Company Not Found' : 'Investigation Failed'}
        </div>
        <div style={{ fontSize: 13, color: '#64748b', lineHeight: 1.6, marginBottom: 24 }}>
          {message}
        </div>
        {isRateLimit && (
          <div style={{
            background: '#fff8e1', border: '1px solid #ffe082',
            borderRadius: 8, padding: '8px 14px', fontSize: 12,
            color: '#856404', marginBottom: 20,
          }}>
            💡 Tip: Use one of the demo CRNs (Monzo, IBS, Seabon) to test with cached responses.
          </div>
        )}
        <button
          onClick={onClose}
          style={{
            background: 'linear-gradient(135deg, #e06b5a 0%, #7c3aed 100%)',
            color: '#fff', border: 'none', borderRadius: 8,
            padding: '10px 28px', fontSize: 13, fontWeight: 600,
            cursor: 'pointer', fontFamily: 'inherit',
          }}
        >
          Got it
        </button>
      </div>
    </div>
  )
}

export default function DualEntryGateway({ onInvestigateAPI, onInvestigateDocument, error }) {
  const [mode, setMode] = useState('crn')
  const [crnValue, setCrnValue] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [modalError, setModalError] = useState(null)
  const fileInputRef = useRef(null)

  // Show backend errors in modal too
  const displayError = modalError || error

  function validateAndInvestigate(crn) {
    const trimmed = crn.trim().toUpperCase()
    if (!trimmed) return
    if (!CRN_REGEX.test(trimmed)) {
      setModalError(
        `"${crn.trim()}" is not a valid UK Companies House number.\n\nA valid CRN is either:\n• 8 digits (e.g. 09446231)\n• 2-letter prefix + 6 digits (e.g. SC123456)`
      )
      return
    }
    onInvestigateAPI(trimmed)
  }

  function handleCrnKeyDown(e) {
    if (e.key === 'Enter') validateAndInvestigate(crnValue)
  }
  function handleDragOver(e) { e.preventDefault(); setIsDragging(true) }
  function handleDragLeave() { setIsDragging(false) }
  function handleDrop(e) {
    e.preventDefault(); setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file && file.type === 'application/pdf') setSelectedFile(file)
  }
  function handleFileChange(e) { if (e.target.files[0]) setSelectedFile(e.target.files[0]) }
  function formatSize(b) { return b < 1048576 ? `${(b/1024).toFixed(1)} KB` : `${(b/1048576).toFixed(1)} MB` }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex',
      background: 'var(--cream)',
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      <style>{`
        @keyframes fadeInScale {
          from { opacity: 0; transform: scale(0.93); }
          to   { opacity: 1; transform: scale(1); }
        }
      `}</style>

      <ErrorModal message={displayError} onClose={() => setModalError(null)} />

      {/* ── LEFT PANEL — brand / info pane ─────────────────────────── */}
      <div style={{
        width: 380, flexShrink: 0,
        background: 'var(--dark)',
        display: 'flex', flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '40px 36px',
      }}>
        {/* Logo */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 40 }}>
            <div style={{
              width: 40, height: 40, borderRadius: 10,
              background: 'linear-gradient(135deg, var(--coral) 0%, var(--purple) 100%)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 18, fontWeight: 800, color: '#fff',
              boxShadow: '0 4px 16px rgba(224,107,90,0.4)',
            }}>U</div>
            <div>
              <div style={{ color: 'var(--text-light)', fontSize: 16, fontWeight: 700, letterSpacing: '0.08em' }}>UNSHELL</div>
              <div style={{ color: 'var(--text-dim)', fontSize: 10, letterSpacing: '0.12em' }}>PROJECT FUSION</div>
            </div>
          </div>

          <h2 style={{ color: 'var(--text-light)', fontSize: 22, fontWeight: 700, lineHeight: 1.4, marginBottom: 12 }}>
            AML &amp; KYB<br />Intelligence Graph
          </h2>
          <p style={{ color: 'var(--text-dim)', fontSize: 13, lineHeight: 1.7, marginBottom: 36 }}>
            Autonomously traces corporate ownership chains, detects circular loops, and screens against global sanctions databases.
          </p>

          {/* Feature list */}
          {[
            { icon: '🔍', color: 'var(--teal)',   label: 'Deep Graph Traversal',   desc: 'Recursively maps 6+ layers deep' },
            { icon: '⚡', color: 'var(--coral)',  label: 'Real-time Sanctions',    desc: 'OFAC SDN + EU HM Treasury live' },
            { icon: '📄', color: 'var(--amber)',  label: 'Document Fusion',        desc: 'AI-extracts PDF ownership data' },
            { icon: '🔒', color: 'var(--green)',  label: 'Zero Data Retention',    desc: 'No PII stored or transmitted' },
          ].map(f => (
            <div key={f.label} style={{ display: 'flex', gap: 12, marginBottom: 18 }}>
              <div style={{
                width: 34, height: 34, borderRadius: 8, flexShrink: 0,
                background: f.color + '22',
                border: `1px solid ${f.color}44`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 15,
              }}>{f.icon}</div>
              <div>
                <div style={{ color: 'var(--text-light)', fontSize: 12, fontWeight: 600 }}>{f.label}</div>
                <div style={{ color: 'var(--text-dim)', fontSize: 11, marginTop: 2 }}>{f.desc}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Bottom badges */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {['Composite AI', 'Math-Verified', 'LangGraph'].map(b => (
            <span key={b} style={{
              background: 'var(--dark-3)', border: '1px solid var(--border-dark)',
              borderRadius: 'var(--r-pill)', padding: '3px 10px',
              fontSize: 10, color: 'var(--text-dim)', fontWeight: 500,
            }}>{b}</span>
          ))}
        </div>
      </div>

      {/* ── RIGHT PANEL — input form ────────────────────────────────── */}
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '40px 48px',
      }}>
        <div style={{ width: '100%', maxWidth: 440 }}>

          <h1 style={{ color: 'var(--text-dark)', fontSize: 24, fontWeight: 700, marginBottom: 6 }}>
            Start Investigation
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 30 }}>
            Enter a UK company number or upload a PDF document to begin forensic analysis.
          </p>

          {/* Error shown as modal now - no inline banner */}

          {/* Mode Toggle */}
          <div style={{
            display: 'flex', gap: 0,
            background: 'var(--cream-2)', border: '1px solid var(--border-light)',
            borderRadius: 'var(--r-md)', padding: 4, marginBottom: 24,
          }}>
            {[
              { id: 'crn',      icon: '🏢', label: 'Company Number' },
              { id: 'document', icon: '📄', label: 'Upload PDF' },
            ].map(tab => (
              <button key={tab.id} id={`tab-${tab.id}`} onClick={() => setMode(tab.id)} style={{
                flex: 1, padding: '9px 16px', borderRadius: 7, border: 'none',
                background: mode === tab.id ? 'var(--white)' : 'transparent',
                color: mode === tab.id ? 'var(--text-dark)' : 'var(--text-muted)',
                fontSize: 13, fontWeight: mode === tab.id ? 600 : 400,
                cursor: 'pointer', transition: 'all 0.2s',
                fontFamily: 'inherit',
                boxShadow: mode === tab.id ? 'var(--shadow-sm)' : 'none',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              }}>
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>

          {/* PANEL A — CRN */}
          {mode === 'crn' && (
            <div className="fade-up">
              <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-mid)', display: 'block', marginBottom: 6 }}>
                Companies House Registration Number
              </label>
              <input
                id="crn-input" type="text" value={crnValue}
                onChange={e => setCrnValue(e.target.value)}
                onKeyDown={handleCrnKeyDown}
                placeholder="e.g. 09446231"
                style={{
                  width: '100%', height: 46,
                  background: 'var(--white)',
                  border: '1.5px solid var(--border-light)',
                  borderRadius: 'var(--r-md)', padding: '0 14px',
                  color: 'var(--text-dark)', fontSize: 14, fontFamily: 'inherit',
                  outline: 'none', transition: 'border-color 0.2s',
                  boxShadow: 'var(--shadow-sm)',
                }}
                onFocus={e => e.target.style.borderColor = 'var(--coral)'}
                onBlur={e => e.target.style.borderColor = 'var(--border-light)'}
              />

              {/* Quick picks */}
              <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 11, color: 'var(--text-muted)', alignSelf: 'center' }}>Try:</span>
                {CRN_DEMOS.map(d => (
                  <button key={d.crn} id={`demo-${d.crn}`} onClick={() => setCrnValue(d.crn)} style={{
                    background: 'var(--white)', border: '1px solid var(--border-light)',
                    borderRadius: 'var(--r-pill)', padding: '4px 12px',
                    fontSize: 11, color: 'var(--text-mid)', cursor: 'pointer',
                    fontFamily: 'inherit', transition: 'all 0.18s',
                    display: 'flex', alignItems: 'center', gap: 4,
                    boxShadow: 'var(--shadow-sm)',
                  }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--coral)'; e.currentTarget.style.color = 'var(--coral)' }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-light)'; e.currentTarget.style.color = 'var(--text-mid)' }}
                  >
                    {d.label}
                    {d.tag === '⚠ High Risk' && <span style={{ color: 'var(--coral)', fontSize: 9 }}>⚠</span>}
                  </button>
                ))}
              </div>

              <button
                id="btn-investigate-api" disabled={!crnValue.trim()}
                onClick={() => validateAndInvestigate(crnValue)}
                style={{
                  width: '100%', height: 48, marginTop: 20,
                  background: crnValue.trim()
                    ? 'linear-gradient(135deg, var(--coral) 0%, var(--purple) 100%)'
                    : 'var(--cream-2)',
                  color: crnValue.trim() ? '#fff' : 'var(--text-muted)',
                  border: 'none', borderRadius: 'var(--r-md)',
                  fontSize: 13, fontWeight: 700, letterSpacing: '0.06em',
                  cursor: crnValue.trim() ? 'pointer' : 'not-allowed',
                  fontFamily: 'inherit', transition: 'opacity 0.2s, transform 0.1s',
                  boxShadow: crnValue.trim() ? '0 4px 20px rgba(224,107,90,0.35)' : 'none',
                }}
                onMouseEnter={e => { if (crnValue.trim()) { e.currentTarget.style.opacity = '0.9'; e.currentTarget.style.transform = 'translateY(-1px)' }}}
                onMouseLeave={e => { if (crnValue.trim()) { e.currentTarget.style.opacity = '1'; e.currentTarget.style.transform = 'none' }}}
              >
                Investigate →
              </button>
            </div>
          )}

          {/* PANEL B — Document */}
          {mode === 'document' && (
            <div className="fade-up">
              <div
                id="document-drop-zone"
                onClick={() => fileInputRef.current?.click()}
                onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}
                style={{
                  width: '100%', height: 154,
                  border: `2px dashed ${isDragging ? 'var(--coral)' : 'var(--border-light)'}`,
                  borderRadius: 'var(--r-lg)',
                  background: isDragging ? 'rgba(224,107,90,0.04)' : 'var(--white)',
                  display: 'flex', flexDirection: 'column',
                  alignItems: 'center', justifyContent: 'center',
                  gap: 6, cursor: 'pointer', transition: 'all 0.2s',
                  boxShadow: 'var(--shadow-sm)',
                }}
              >
                <div style={{
                  width: 44, height: 44, borderRadius: 10,
                  background: isDragging ? 'var(--coral-muted)' : 'var(--cream)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 18,
                }}>📄</div>
                <span style={{ fontSize: 14, color: 'var(--text-dark)', fontWeight: 500 }}>Drop PDF here</span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>or <span style={{ color: 'var(--coral)', fontWeight: 600 }}>click to browse</span></span>
                <input ref={fileInputRef} type="file" accept=".pdf" style={{ display: 'none' }} onChange={handleFileChange} />
              </div>

              {selectedFile && (
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 10, marginTop: 10,
                  background: 'var(--green-muted)', border: '1px solid rgba(92,184,122,0.4)',
                  borderRadius: 'var(--r-md)', padding: '8px 12px',
                }}>
                  <span style={{ color: 'var(--green)', fontSize: 15 }}>✓</span>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-dark)' }}>{selectedFile.name}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{formatSize(selectedFile.size)}</div>
                  </div>
                </div>
              )}

              <button
                id="btn-analyse-document" disabled={!selectedFile}
                onClick={() => onInvestigateDocument(selectedFile)}
                style={{
                  width: '100%', height: 48, marginTop: 16,
                  background: selectedFile
                    ? 'linear-gradient(135deg, var(--coral) 0%, var(--purple) 100%)'
                    : 'var(--cream-2)',
                  color: selectedFile ? '#fff' : 'var(--text-muted)',
                  border: 'none', borderRadius: 'var(--r-md)',
                  fontSize: 13, fontWeight: 700, letterSpacing: '0.06em',
                  cursor: selectedFile ? 'pointer' : 'not-allowed',
                  fontFamily: 'inherit', transition: 'opacity 0.2s, transform 0.1s',
                  boxShadow: selectedFile ? '0 4px 20px rgba(224,107,90,0.35)' : 'none',
                }}
                onMouseEnter={e => { if (selectedFile) { e.currentTarget.style.opacity = '0.9'; e.currentTarget.style.transform = 'translateY(-1px)' }}}
                onMouseLeave={e => { if (selectedFile) { e.currentTarget.style.opacity = '1'; e.currentTarget.style.transform = 'none' }}}
              >
                Analyse Document →
              </button>
            </div>
          )}

          {/* Stats row */}
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 12, marginTop: 36,
          }}>
            {[
              { value: '99.2%',  label: 'Accuracy', color: 'var(--green)' },
              { value: '<3s',    label: 'Avg. Time', color: 'var(--teal)' },
              { value: '180+',   label: 'Jurisdictions', color: 'var(--amber)' },
            ].map(s => (
              <div key={s.label} style={{
                background: 'var(--white)', border: '1px solid var(--border-light)',
                borderRadius: 'var(--r-md)', padding: '12px',
                textAlign: 'center', boxShadow: 'var(--shadow-sm)',
              }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: s.color }}>{s.value}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2, fontWeight: 500 }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
