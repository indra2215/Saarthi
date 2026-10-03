import React, { useState, useEffect } from 'react'
import './index.css'
import ChatView from './components/ChatView'
import TeacherPortal from './components/TeacherPortal'
import EvalPage from './components/EvalPage'
import StudentAuthModal from './components/StudentAuthModal'

const ROLL_STORAGE_KEY = 'kmec_student_roll'
const NAME_STORAGE_KEY = 'kmec_student_name'

// ── Simple hash-based router ────────────────────────────────────────────
function getHash() {
  const h = window.location.hash.replace('#', '').replace(/^\//, '') || ''
  return h  // 'student' | 'faculty' | 'eval' | ''
}

function setHash(path) {
  window.location.hash = '/' + path
}

export default function App() {
  const [route, setRoute] = useState(getHash)

  // Listen for hash changes (back/forward, manual URL change)
  useEffect(() => {
    const handler = () => setRoute(getHash())
    window.addEventListener('hashchange', handler)
    return () => window.removeEventListener('hashchange', handler)
  }, [])

  const navigate = (path) => {
    setHash(path)
    setRoute(path)
  }

  const [indexReady, setIndexReady] = useState(false)
  const [student, setStudent] = useState(() => {
    const rollNo = localStorage.getItem(ROLL_STORAGE_KEY)
    const name   = localStorage.getItem(NAME_STORAGE_KEY)
    return rollNo ? { rollNo, name: name || 'Student' } : null
  })
  const [showAuthModal, setShowAuthModal] = useState(false)

  const sessionId = student?.rollNo ? `STU-${student.rollNo}` : 'STU-GUEST'

  useEffect(() => {
    fetch('/health').then(r => r.json()).then(d => {
      setIndexReady(d.indexes_loaded || false)
    }).catch(() => {})
  }, [])

  const handleStudentLogin = (studentData) => {
    setStudent(studentData)
    localStorage.setItem(ROLL_STORAGE_KEY, studentData.rollNo)
    localStorage.setItem(NAME_STORAGE_KEY, studentData.name)
    setShowAuthModal(false)
  }

  const handleStudentLogout = () => {
    localStorage.removeItem(ROLL_STORAGE_KEY)
    localStorage.removeItem(NAME_STORAGE_KEY)
    setStudent(null)
  }

  // ── Landing Page (no route) ─────────────────────────────────────────
  if (!route || route === '') {
    return (
      <div className="landing">
        <div className="landing-card">
          <img src="/logo.png" alt="KMEC Logo" className="landing-logo" />
          <div className="landing-title">KMEC Research Connect</div>
          <div className="landing-sub">Faculty Discovery &amp; Mentorship Platform — SAARTHI</div>

          <div className="landing-prompt">Select your portal</div>

          <div className="landing-options">
            <button className="landing-btn" onClick={() => navigate('student')}>
              <div className="landing-btn-icon">🎓</div>
              <div className="landing-btn-text">
                <strong>Student Portal</strong>
                <span>Search faculty, explore research, send meeting requests</span>
              </div>
              <div style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text3)', flexShrink: 0 }}>
                /#/student →
              </div>
            </button>

            <button className="landing-btn" onClick={() => navigate('faculty')}>
              <div className="landing-btn-icon">👨‍🏫</div>
              <div className="landing-btn-text">
                <strong>Faculty Portal</strong>
                <span>Login to manage student requests &amp; timetable</span>
              </div>
              <div style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text3)', flexShrink: 0 }}>
                /#/faculty →
              </div>
            </button>
          </div>

          <div style={{ marginTop: 24, padding: '12px 16px', background: 'var(--bg4)', borderRadius: 8, border: '1px solid var(--border)', textAlign: 'left' }}>
            <div style={{ fontSize: 10, color: 'var(--accent)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8 }}>
              Direct URLs
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <code style={{ fontSize: 11, color: 'var(--text2)' }}>localhost:5173/#/student</code>
              <code style={{ fontSize: 11, color: 'var(--text2)' }}>localhost:5173/#/faculty</code>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ── Faculty Portal Route ────────────────────────────────────────────
  if (route === 'faculty') {
    return (
      <div className="app">
        <aside className="sidebar">
          <div className="sidebar-header" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <img src="/logo.png" alt="KMEC Logo"
              style={{ width: 38, height: 38, borderRadius: 8, objectFit: 'cover', border: '1px solid var(--border)' }} />
            <div>
              <div className="sidebar-logo">Faculty Portal</div>
              <div className="sidebar-sub">KMEC Research Connect</div>
            </div>
          </div>

          <div className="sidebar-section">Navigation</div>
          <button className={`sidebar-btn active`}>
            <span className="dot" /> Dashboard
          </button>

          <div style={{ flex: 1 }} />

          <div style={{ padding: '14px 16px', borderTop: '1px solid var(--border)' }}>
            <div style={{ fontSize: 10, color: indexReady ? 'var(--text3)' : 'var(--danger)', marginBottom: 10 }}>
              {indexReady ? '● System Ready' : '● Index Loading...'}
            </div>
            <button onClick={() => navigate('')}
              style={{ background: 'none', border: 'none', color: 'var(--text3)', fontSize: 11, textDecoration: 'underline', cursor: 'pointer', padding: 0 }}>
              ← Back to Landing
            </button>
            <div style={{ marginTop: 8 }}>
              <a href="#/student" style={{ fontSize: 10, color: 'var(--text3)', textDecoration: 'underline' }}
                onClick={e => { e.preventDefault(); navigate('student') }}>
                Switch to Student Portal
              </a>
            </div>
          </div>
        </aside>

        <main className="main">
          <div className="topbar">
            <span className="topbar-title">Faculty Portal — Dashboard</span>
            <div className="topbar-right">
              <span className="badge accent">Faculty</span>
              <code style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)' }}>
                /#/faculty
              </code>
            </div>
          </div>
          <TeacherPortal />
        </main>
      </div>
    )
  }

  // ── Eval Route ──────────────────────────────────────────────────────
  if (route === 'eval') {
    return (
      <div className="app">
        <aside className="sidebar">
          <div className="sidebar-header" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <img src="/logo.png" alt="KMEC Logo"
              style={{ width: 38, height: 38, borderRadius: 8, objectFit: 'cover' }} />
            <div>
              <div className="sidebar-logo">Evaluation</div>
              <div className="sidebar-sub">KMEC Research Connect</div>
            </div>
          </div>
          <div style={{ flex: 1 }} />
          <div style={{ padding: '14px 16px', borderTop: '1px solid var(--border)' }}>
            <button onClick={() => navigate('')}
              style={{ background: 'none', border: 'none', color: 'var(--text3)', fontSize: 11, textDecoration: 'underline', cursor: 'pointer', padding: 0 }}>
              ← Back to Landing
            </button>
          </div>
        </aside>
        <main className="main">
          <div className="topbar">
            <span className="topbar-title">Evaluation Dashboard</span>
          </div>
          <EvalPage />
        </main>
      </div>
    )
  }

  // ── Student Portal Route (default) ──────────────────────────────────
  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <img src="/logo.png" alt="KMEC Logo"
            style={{ width: 38, height: 38, borderRadius: 8, objectFit: 'cover', border: '1px solid var(--border)' }} />
          <div>
            <div className="sidebar-logo">Student Portal</div>
            <div className="sidebar-sub">KMEC Research Connect</div>
          </div>
        </div>

        <div className="sidebar-section">Navigation</div>
        <button className="sidebar-btn active">
          <span className="dot" /> Research Search
        </button>
        <button className="sidebar-btn" onClick={() => navigate('eval')}>
          <span className="dot" /> Evaluation Data
        </button>

        <div style={{ flex: 1 }} />

        {/* Student Profile */}
        <div className="student-profile-block">
          {student ? (
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
              <div className="student-avatar">{student.name?.[0]?.toUpperCase() || 'S'}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{student.name}</div>
                <div style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)', marginTop: 1 }}>
                  {student.rollNo}
                </div>
                <div style={{ fontSize: 10, color: 'var(--text3)', marginTop: 1 }}>
                  {student.department || 'Engineering'}
                </div>
                <button onClick={handleStudentLogout}
                  style={{ background: 'none', border: 'none', color: 'var(--text3)', fontSize: 10, textDecoration: 'underline', cursor: 'pointer', padding: 0, marginTop: 5 }}>
                  Switch Student
                </button>
              </div>
            </div>
          ) : (
            <div>
              <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 6 }}>Not Logged In</div>
              <button className="btn secondary" style={{ width: '100%', fontSize: 11, padding: '5px 8px' }}
                onClick={() => setShowAuthModal(true)}>
                Enter Roll Number
              </button>
            </div>
          )}

          <div style={{ fontSize: 10, color: indexReady ? 'var(--success)' : 'var(--danger)', marginTop: 10, display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: indexReady ? 'var(--success)' : 'var(--danger)', display: 'inline-block' }} />
            {indexReady ? 'System Ready' : 'Index Loading...'}
          </div>

          <div style={{ marginTop: 8, display: 'flex', gap: 12 }}>
            <button onClick={() => navigate('')}
              style={{ background: 'none', border: 'none', color: 'var(--text3)', fontSize: 10, textDecoration: 'underline', cursor: 'pointer', padding: 0 }}>
              ← Home
            </button>
            <a href="#/faculty" style={{ fontSize: 10, color: 'var(--text3)', textDecoration: 'underline' }}
              onClick={e => { e.preventDefault(); navigate('faculty') }}>
              Faculty Login →
            </a>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="main">
        <div className="topbar">
          <span className="topbar-title">Research Discovery Chat</span>
          <div className="topbar-right">
            {student ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="badge accent" style={{ fontFamily: 'var(--mono)' }}>
                  {student.rollNo}
                </span>
                <span className="badge">{student.name}</span>
              </div>
            ) : (
              <button className="btn secondary" style={{ fontSize: 11, padding: '4px 10px' }}
                onClick={() => setShowAuthModal(true)}>
                Student Login
              </button>
            )}
            <code style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)' }}>
              /#/student
            </code>
          </div>
        </div>

        {!student && !showAuthModal ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', padding: 24, textAlign: 'center' }}>
            <img src="/logo.png" alt="KMEC Logo"
              style={{ width: 72, height: 72, borderRadius: 18, marginBottom: 20, border: '2px solid var(--border2)', boxShadow: '0 0 30px rgba(245,166,35,0.12)' }} />
            <h2 style={{ fontSize: 22, marginBottom: 8, fontWeight: 800 }}>KMEC Faculty Discovery</h2>
            <p style={{ color: 'var(--text2)', maxWidth: 480, fontSize: 14, marginBottom: 24, lineHeight: 1.6 }}>
              Authenticate with your 12-digit university Roll Number to discover faculty researchers
              and send meeting requests directly to their portal.
            </p>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center', marginBottom: 20 }}>
              {['IoT & Embedded Systems', 'Cybersecurity', 'Blockchain', 'Machine Learning', 'Cloud Computing'].map((t, i) => (
                <span key={i} className="chip" style={{ fontSize: 12, padding: '4px 12px' }}>{t}</span>
              ))}
            </div>
            <button className="btn" style={{ padding: '12px 28px', fontSize: 14 }}
              onClick={() => setShowAuthModal(true)}>
              Login with Roll Number →
            </button>
          </div>
        ) : (
          <ChatView sessionId={sessionId} indexReady={indexReady} student={student} />
        )}
      </main>

      {/* Auth Modal */}
      {showAuthModal && (
        <StudentAuthModal
          currentStudent={student}
          onLogin={handleStudentLogin}
          onCancel={student ? () => setShowAuthModal(false) : null}
        />
      )}
    </div>
  )
}
