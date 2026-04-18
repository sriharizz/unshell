import { useState, useEffect } from 'react'

const STEPS = [
  { icon: '🏛️', label: 'Fetching company registry data...',        color: 'var(--teal)' },
  { icon: '🕸️', label: 'Building corporate ownership graph...',    color: 'var(--purple)' },
  { icon: '🔄', label: 'Running cycle detection algorithms...',    color: 'var(--coral)' },
  { icon: '📊', label: 'Calculating multi-vector risk scores...',  color: 'var(--amber)' },
  { icon: '🛡️', label: 'Screening against OFAC sanctions database...', color: 'var(--coral)' },
  { icon: '📋', label: 'Compiling forensic investigation report...', color: 'var(--green)' },
]

export default function LoadingScreen() {
  const [completedSteps, setCompletedSteps] = useState(new Set())
  const [currentStep, setCurrentStep] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStep(prev => {
        const next = prev + 1
        setCompletedSteps(cs => new Set([...cs, prev]))
        if (next >= STEPS.length) clearInterval(interval)
        return next
      })
    }, 4000)
    return () => clearInterval(interval)
  }, [])

  const progress = (completedSteps.size / STEPS.length) * 100

  return (
    <div style={{
      minHeight: '100vh', display: 'flex',
      background: 'var(--cream)',
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      {/* Left dark strip — matches gateway layout */}
      <div style={{
        width: 380, flexShrink: 0,
        background: 'var(--dark)',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        padding: '40px 36px',
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 48 }}>
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

        {/* Spinning ring */}
        <div style={{ position: 'relative', width: 100, height: 100, marginBottom: 32 }}>
          {/* Outer ring */}
          <div style={{
            position: 'absolute', inset: 0,
            border: '3px solid var(--dark-3)', borderRadius: '50%',
          }} />
          <div
            className="spinner"
            style={{
              position: 'absolute', inset: 0,
              border: '3px solid transparent',
              borderTopColor: 'var(--coral)',
              borderRightColor: 'var(--purple)',
              borderRadius: '50%',
            }}
          />
          {/* Inner ring counter-spin */}
          <div style={{
            position: 'absolute', inset: 14,
            border: '2px solid var(--dark-3)', borderRadius: '50%',
          }} />
          <div
            className="spinner"
            style={{
              position: 'absolute', inset: 14,
              border: '2px solid transparent',
              borderTopColor: 'var(--teal)',
              borderRadius: '50%',
              animationDirection: 'reverse',
              animationDuration: '0.8s',
            }}
          />
          {/* Center dot */}
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--coral)' }} />
          </div>
        </div>

        <div style={{ color: 'var(--text-light)', fontSize: 16, fontWeight: 600, textAlign: 'center', marginBottom: 6 }}>
          Analysing
        </div>
        <div style={{ color: 'var(--text-dim)', fontSize: 12, textAlign: 'center' }}>
          Autonomous pipeline running
        </div>
      </div>

      {/* Right cream panel */}
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '40px 48px',
      }}>
        <div style={{ width: '100%', maxWidth: 440 }}>
          <h2 style={{ color: 'var(--text-dark)', fontSize: 22, fontWeight: 700, marginBottom: 6 }}>
            Investigating Corporate Structure
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 32 }}>
            Multi-agent pipeline tracing ownership across jurisdictions
          </p>

          {/* Steps */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 36 }}>
            {STEPS.map((step, idx) => {
              const isDone    = completedSteps.has(idx)
              const isActive  = idx === currentStep
              const isPending = idx > currentStep
              return (
                <div key={idx} style={{
                  display: 'flex', alignItems: 'center', gap: 14,
                  padding: '12px 16px',
                  background: isDone ? 'rgba(92,184,122,0.06)' : isActive ? 'var(--white)' : 'transparent',
                  border: `1px solid ${isDone ? 'rgba(92,184,122,0.25)' : isActive ? 'var(--border-light)' : 'transparent'}`,
                  borderRadius: 'var(--r-md)',
                  boxShadow: isActive ? 'var(--shadow-sm)' : 'none',
                  opacity: isPending ? 0.45 : 1,
                  transition: 'all 0.4s ease',
                }}>
                  {/* Status icon */}
                  <div style={{ width: 28, height: 28, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {isDone && (
                      <div style={{ width: 22, height: 22, borderRadius: '50%', background: 'var(--green-muted)', border: '1.5px solid var(--green)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <span style={{ color: 'var(--green)', fontSize: 11, fontWeight: 700 }}>✓</span>
                      </div>
                    )}
                    {isActive && (
                      <div
                        className="spinner"
                        style={{ width: 20, height: 20, border: '2.5px solid var(--cream-2)', borderTopColor: step.color, borderRadius: '50%' }}
                      />
                    )}
                    {isPending && (
                      <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--border-light)' }} />
                    )}
                  </div>

                  <span style={{ fontSize: 14 }}>{step.icon}</span>
                  <span style={{
                    fontSize: 13, fontWeight: isActive ? 600 : 400,
                    color: isDone ? 'var(--green)' : isActive ? 'var(--text-dark)' : 'var(--text-muted)',
                    transition: 'color 0.4s',
                  }}>
                    {step.label}
                  </span>
                </div>
              )
            })}
          </div>

          {/* Progress bar */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 500 }}>Progress</span>
              <span style={{ fontSize: 11, color: 'var(--text-mid)', fontWeight: 600 }}>{completedSteps.size}/{STEPS.length} steps</span>
            </div>
            <div style={{ height: 6, background: 'var(--cream-2)', borderRadius: 'var(--r-pill)', overflow: 'hidden' }}>
              <div style={{
                height: '100%', borderRadius: 'var(--r-pill)',
                width: `${progress}%`,
                background: 'linear-gradient(90deg, var(--coral), var(--purple))',
                transition: 'width 1s ease',
                boxShadow: '0 0 8px rgba(224,107,90,0.4)',
              }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
