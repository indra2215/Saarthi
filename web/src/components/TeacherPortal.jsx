import React, { useState, useEffect, useRef, useCallback } from 'react'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
const POLL_INTERVAL_MS = 6000   // Poll for new requests every 6 seconds

// Test faculty accounts mapped to real profiles in faculty.json
const DEMO_TEACHERS = [
  { faculty_id: 'FAC-1-2',  email: 'teacher1@kmec.edu.in', password: 'teacher1', label: 'Dr. P. Balakrishna', dept: 'CSE · Big Data Analytics' },
  { faculty_id: 'FAC-1-1',  email: 'teacher2@kmec.edu.in', password: 'teacher2', label: 'Dr. Ch. Rathan Kumar', dept: 'CSE (HOD) · Cloud Computing' },
  { faculty_id: 'FAC-1-29', email: 'teacher3@kmec.edu.in', password: 'teacher3', label: 'Mrs. Madhavi Anisetty', dept: 'CSE · Cloud Systems' },
  { faculty_id: 'FAC-1-4',  email: 'teacher4@kmec.edu.in', password: 'teacher4', label: 'Dr. Aparna Rajesh', dept: 'CSE · Cybersecurity' },
  { faculty_id: 'FAC-2-4',  email: 'teacher5@kmec.edu.in', password: 'teacher5', label: 'Dr. Madhavi', dept: 'CSE-AIML · Artificial Intelligence' },
]

// Seeded demo timetable for demo teachers
const DEMO_TIMETABLE = [
  { day: 'Mon', start: '09:00', end: '10:00', type: 'class',   room: 'LH-201' },
  { day: 'Mon', start: '11:00', end: '12:00', type: 'lab',     room: 'CS-Lab3' },
  { day: 'Tue', start: '10:00', end: '11:00', type: 'class',   room: 'LH-301' },
  { day: 'Wed', start: '09:00', end: '09:30', type: 'meeting', room: 'Faculty Room' },
  { day: 'Thu', start: '14:00', end: '15:00', type: 'tutorial',room: 'LH-201' },
  { day: 'Fri', start: '11:00', end: '12:00', type: 'class',   room: 'LH-202' },
]

export default function TeacherPortal() {
  const [tab, setTab]             = useState('login')
  const [token, setToken]         = useState(() => localStorage.getItem('teacher_token') || '')
  const [facultyId, setFacultyId] = useState(() => localStorage.getItem('teacher_fid') || '')
  const [teacherName, setTeacherName] = useState(() => localStorage.getItem('teacher_name') || '')
  const [email, setEmail]         = useState('')
  const [password, setPassword]   = useState('')
  const [selectedFid, setSelectedFid] = useState('')
  const [allFaculty, setAllFaculty] = useState([])
  const [loginError, setLoginError] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)
  const [requests, setRequests]   = useState([])
  const [timetable, setTimetable] = useState([])
  const [ttEntry, setTtEntry]     = useState({ day: 'Mon', start: '09:00', end: '10:00', type: 'class', room: '' })
  const [activeTab, setActiveTab] = useState('requests')
  const [newCount, setNewCount]   = useState(0)     // new requests since last view
  const [lastSeen, setLastSeen]   = useState(0)     // timestamp of last check
  const [notification, setNotification] = useState(null)  // transient "New request!" banner
  const pollRef = useRef(null)
  const sseRef = useRef(null)

  // ── Fetch all faculty roster on mount ───────────────────────────────
  useEffect(() => {
    fetch('/faculty')
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data)) setAllFaculty(data)
      })
      .catch(() => {})
  }, [])

  // ── Auto-resume session ─────────────────────────────────────────────
  useEffect(() => {
    if (token && facultyId) {
      setTab('dashboard')
      loadDashboard(facultyId, token)
      startPolling(facultyId, token)
      connectSSE(facultyId, token)
    }
    return () => {
      if (sseRef.current) sseRef.current.close()
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  // ── SSE real-time push connection ──────────────────────────────────
  const connectSSE = useCallback((fid) => {
    if (!fid) return
    if (sseRef.current) sseRef.current.close()
    const es = new EventSource(`/events/requests/${fid}`)
    sseRef.current = es
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'new_request') {
          setRequests(prev => {
            if (prev.find(r => r.request_id === data.request_id)) return prev
            setNewCount(c => c + 1)
            setNotification(`🔔 New request from ${data.student_name} (${data.session_id}) about "${data.topic}"`)
            setTimeout(() => setNotification(null), 7000)
            return [data, ...prev]
          })
        }
      } catch (_) {}
    }
    es.onerror = () => {
      es.close()
    }
  }, [])

  // ── Real-time polling ───────────────────────────────────────────────
  const startPolling = useCallback((fid, tok) => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/teacher/requests/${fid}`, {
          headers: { Authorization: `Bearer ${tok}` }
        })
        if (!res.ok) return
        const data = await res.json()
        if (!Array.isArray(data)) return

        setRequests(prev => {
          const newItems = data.filter(r =>
            !prev.find(p => p.request_id === r.request_id)
          )
          if (newItems.length > 0) {
            setNewCount(c => c + newItems.length)
            setNotification(`🔔 ${newItems.length} new request${newItems.length > 1 ? 's' : ''} received!`)
            setTimeout(() => setNotification(null), 5000)
          }
          return data
        })
      } catch (_) {}
    }, POLL_INTERVAL_MS)
  }, [])

  // ── Auth Execution ──────────────────────────────────────────────────
  const doLogin = async (loginEmail, loginPass, fid) => {
    setLoginError('')
    setLoginLoading(true)

    try {
      const res = await fetch('/teacher/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: loginEmail,
          password: loginPass,
          faculty_id: fid || undefined
        })
      })
      const data = await res.json()
      if (data.token) {
        const matchedFac = allFaculty.find(f => f.faculty_id === data.faculty_id)
        const name = data.faculty_name || matchedFac?.display_name || loginEmail

        setToken(data.token)
        setFacultyId(data.faculty_id)
        setTeacherName(name)
        localStorage.setItem('teacher_token', data.token)
        localStorage.setItem('teacher_fid',   data.faculty_id)
        localStorage.setItem('teacher_name',  name)
        setTab('dashboard')
        await loadDashboard(data.faculty_id, data.token)
        startPolling(data.faculty_id, data.token)
        connectSSE(data.faculty_id)
      } else {
        setLoginError(data.detail || 'Login failed. Please try again.')
      }
    } catch (e) {
      setLoginError('Connection error — is the server running?')
    }
    setLoginLoading(false)
  }

  const handleCustomLogin = () => {
    const e = email.trim() || 'teacher1@kmec.edu.in'
    const p = password || 'teacher1'
    doLogin(e, p, selectedFid || undefined)
  }

  const quickLoginAs = (demo) => {
    setEmail(demo.email)
    setPassword(demo.password)
    setSelectedFid(demo.faculty_id)
    doLogin(demo.email, demo.password, demo.faculty_id)
  }

  const loadDashboard = async (fid = facultyId, tok = token) => {
    const headers = { Authorization: `Bearer ${tok}` }
    try {
      const [reqRes, ttRes] = await Promise.all([
        fetch(`/teacher/requests/${fid}`, { headers }).then(r => r.json()),
        fetch(`/teacher/timetable/${fid}`).then(r => r.json()),
      ])
      const reqs = Array.isArray(reqRes) ? reqRes : []
      setRequests(reqs)

      let tt = Array.isArray(ttRes) ? ttRes : []
      if (tt.length === 0) {
        tt = DEMO_TIMETABLE
        await fetch(`/teacher/timetable/${fid}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${tok}` },
          body: JSON.stringify({ timetable: DEMO_TIMETABLE })
        }).catch(() => {})
      }
      setTimetable(tt)
      setLastSeen(Date.now())
    } catch (_) {}
  }

  const addTimetableEntry = async () => {
    const newTt = [...timetable, ttEntry]
    try {
      await fetch(`/teacher/timetable/${facultyId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ timetable: newTt })
      })
      setTimetable(newTt)
    } catch (_) {}
  }

  const removeEntry = async (i) => {
    const newTt = timetable.filter((_, idx) => idx !== i)
    try {
      await fetch(`/teacher/timetable/${facultyId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ timetable: newTt })
      })
      setTimetable(newTt)
    } catch (_) {}
  }

  const respondToRequest = async (reqId, accept) => {
    try {
      await fetch(`/teacher/request/${reqId}/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          accept,
          message: accept
            ? 'Your meeting request has been accepted! Please meet at my office or during published free slots.'
            : 'Thank you for your interest. I am unable to accommodate this request at this time.'
        })
      })
      setRequests(r => r.map(req =>
        req.request_id === reqId
          ? { ...req, status: accept ? 'accepted' : 'declined' }
          : req
      ))
    } catch (_) {}
  }

  const logout = () => {
    if (pollRef.current) clearInterval(pollRef.current)
    if (sseRef.current) sseRef.current.close()
    setToken('')
    setFacultyId('')
    setTeacherName('')
    localStorage.removeItem('teacher_token')
    localStorage.removeItem('teacher_fid')
    localStorage.removeItem('teacher_name')
    setTab('login')
    setRequests([])
    setTimetable([])
  }

  const handleTabChange = (t) => {
    setActiveTab(t)
    if (t === 'requests') {
      setNewCount(0)
      setLastSeen(Date.now())
    }
  }

  const pendingCount   = requests.filter(r => r.status === 'pending').length
  const acceptedCount  = requests.filter(r => r.status === 'accepted').length
  const declinedCount  = requests.filter(r => r.status === 'declined').length

  // ── Login screen ───────────────────────────────────────────────────
  if (tab === 'login') {
    return (
      <div className="teacher-portal" style={{ maxWidth: 680, margin: '20px auto' }}>
        <div className="teacher-login-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
            <div style={{ fontSize: 36 }}>👨‍🏫</div>
            <div>
              <h2 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>Faculty Portal Login</h2>
              <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 3 }}>
                View and respond to student research meeting requests in real-time · <span style={{ color: 'var(--accent)' }}>/#/faculty</span>
              </div>
            </div>
          </div>

          {/* Quick Login Test Accounts */}
          <div style={{ padding: 14, background: 'var(--bg4)', borderRadius: 10, border: '1px solid var(--accent)', marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <div style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                ⚡ One-Click Test Faculty Login
              </div>
              <span style={{ fontSize: 10, color: 'var(--text3)' }}>Direct access with pre-mapped requests</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {DEMO_TEACHERS.map((demo) => (
                <div key={demo.faculty_id} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '10px 12px', background: 'var(--bg3)', borderRadius: 8,
                  border: '1px solid var(--border)', transition: 'border-color 0.2s'
                }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>
                      {demo.label}
                      <span className="chip" style={{ marginLeft: 8, fontSize: 10 }}>{demo.faculty_id}</span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 2 }}>
                      {demo.dept} · <code style={{ color: 'var(--text2)' }}>{demo.email}</code>
                    </div>
                  </div>
                  <button className="btn" style={{ fontSize: 11, padding: '6px 14px', whiteSpace: 'nowrap' }}
                    onClick={() => quickLoginAs(demo)} disabled={loginLoading}>
                    Login →
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Custom Credentials or Profile Picker */}
          <div style={{ padding: 16, background: 'var(--bg2)', borderRadius: 10, border: '1px solid var(--border)' }}>
            <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 12, color: 'var(--text)' }}>
              Or Login as Any KMEC Faculty Member
            </div>

            {/* Faculty Dropdown */}
            {allFaculty.length > 0 && (
              <div className="form-group" style={{ marginBottom: 12 }}>
                <label className="form-label">Select Faculty Profile</label>
                <select className="filter-select" style={{ width: '100%', fontSize: 12 }}
                  value={selectedFid}
                  onChange={e => {
                    const fid = e.target.value
                    setSelectedFid(fid)
                    const fac = allFaculty.find(f => f.faculty_id === fid)
                    if (fac) {
                      setEmail(`${fid.toLowerCase()}@kmec.edu.in`)
                      setPassword('teacher')
                    }
                  }}>
                  <option value="">-- Choose from all {allFaculty.length} KMEC Faculty --</option>
                  {allFaculty.map(f => (
                    <option key={f.faculty_id} value={f.faculty_id}>
                      {f.display_name} ({f.department_code}) — {f.faculty_id}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="form-group" style={{ marginBottom: 10 }}>
              <label className="form-label">Email Address</label>
              <input className="form-input" type="email" value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="faculty@kmec.edu.in"
                onKeyDown={e => e.key === 'Enter' && handleCustomLogin()} />
            </div>

            <div className="form-group" style={{ marginBottom: 14 }}>
              <label className="form-label">Password</label>
              <input className="form-input" type="password" value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter password (any password accepted for demo)"
                onKeyDown={e => e.key === 'Enter' && handleCustomLogin()} />
            </div>

            {loginError && (
              <div style={{ color: 'var(--danger)', fontSize: 12, marginBottom: 12, padding: '8px 12px', background: 'rgba(224,80,80,0.08)', borderRadius: 8, border: '1px solid rgba(224,80,80,0.2)' }}>
                {loginError}
              </div>
            )}

            <button className="btn" style={{ width: '100%', fontSize: 13, padding: '10px 0' }}
              onClick={handleCustomLogin} disabled={loginLoading}>
              {loginLoading ? <><span className="spinner" /> &nbsp;Authenticating...</> : 'Login to Dashboard'}
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── Dashboard ──────────────────────────────────────────────────────
  return (
    <div className="teacher-portal">
      {/* Live notification banner */}
      {notification && (
        <div style={{
          position: 'fixed', top: 20, right: 20, zIndex: 9999,
          background: 'linear-gradient(135deg, var(--accent), var(--accent2))',
          color: '#0d0c0a', padding: '14px 22px', borderRadius: 10,
          fontWeight: 800, fontSize: 13, boxShadow: '0 8px 30px rgba(245,166,35,0.45)',
          animation: 'slideUp 0.3s ease-out', display: 'flex', alignItems: 'center', gap: 10
        }}>
          <span>{notification}</span>
        </div>
      )}

      {/* Header with Switch Faculty */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h2 style={{ marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>Faculty Dashboard</span>
            <span className="chip" style={{ fontSize: 11, background: 'var(--bg3)', borderColor: 'var(--accent)' }}>
              {facultyId}
            </span>
          </h2>
          <div style={{ fontSize: 13, color: 'var(--text2)' }}>
            Logged in as <strong style={{ color: 'var(--text)' }}>{teacherName}</strong>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--success)', display: 'inline-block' }} />
            Real-time SSE push connected · Polling fallback {POLL_INTERVAL_MS / 1000}s
            {lastSeen > 0 && ` · Last sync: ${new Date(lastSeen).toLocaleTimeString()}`}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Quick-switch dropdown for testing */}
          <select className="filter-select" style={{ fontSize: 11, padding: '6px 10px' }}
            value={facultyId}
            onChange={e => {
              const fid = e.target.value
              const demo = DEMO_TEACHERS.find(d => d.faculty_id === fid)
              if (demo) {
                quickLoginAs(demo)
              } else {
                doLogin(`${fid.toLowerCase()}@kmec.edu.in`, 'teacher', fid)
              }
            }}>
            <option disabled value="">Switch Faculty Account...</option>
            {DEMO_TEACHERS.map(d => (
              <option key={d.faculty_id} value={d.faculty_id}>
                {d.label} ({d.faculty_id})
              </option>
            ))}
          </select>

          <button className="btn secondary" style={{ fontSize: 11, padding: '7px 12px' }}
            onClick={() => loadDashboard()}>
            ↻ Refresh
          </button>
          <button className="btn danger" style={{ fontSize: 11, padding: '7px 12px' }}
            onClick={logout}>
            Logout
          </button>
        </div>
      </div>

      {/* Stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 10, marginBottom: 20 }}>
        {[
          { label: 'Total Requests', value: requests.length, color: 'var(--text)',    icon: '📬' },
          { label: 'Pending',        value: pendingCount,     color: 'var(--accent)',  icon: '⏳' },
          { label: 'Accepted',       value: acceptedCount,    color: 'var(--success)', icon: '✅' },
          { label: 'Declined',       value: declinedCount,    color: 'var(--danger)',  icon: '❌' },
        ].map(stat => (
          <div key={stat.label} style={{
            background: 'var(--bg3)', border: '1px solid var(--border)',
            borderRadius: 10, padding: '12px 14px',
            display: 'flex', alignItems: 'center', gap: 10
          }}>
            <div style={{ fontSize: 22 }}>{stat.icon}</div>
            <div>
              <div style={{ fontSize: 24, fontWeight: 800, color: stat.color, lineHeight: 1 }}>
                {stat.value}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text3)', marginTop: 2 }}>{stat.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="tabs">
        <div
          className={`tab ${activeTab === 'requests' ? 'active' : ''}`}
          onClick={() => handleTabChange('requests')}
          style={{ position: 'relative' }}
        >
          Meeting Requests
          {newCount > 0 && (
            <span style={{
              marginLeft: 6, background: 'var(--accent)', color: '#0d0c0a',
              borderRadius: 99, fontSize: 10, fontWeight: 800,
              padding: '1px 7px', display: 'inline-block'
            }}>{newCount} new</span>
          )}
          {pendingCount > 0 && newCount === 0 && (
            <span style={{
              marginLeft: 6, background: 'var(--bg4)', color: 'var(--accent)',
              borderRadius: 99, fontSize: 10, fontWeight: 700,
              padding: '1px 7px', border: '1px solid var(--accent)', display: 'inline-block'
            }}>{pendingCount}</span>
          )}
        </div>
        <div className={`tab ${activeTab === 'timetable' ? 'active' : ''}`}
          onClick={() => handleTabChange('timetable')}>
          My Timetable &amp; Slots
        </div>
      </div>

      {/* ── Meeting Requests tab ────────────────────────────────────────── */}
      {activeTab === 'requests' && (
        <div>
          {requests.length === 0 && (
            <div className="empty-state" style={{ padding: 36, textAlign: 'center', background: 'var(--bg3)', borderRadius: 10, border: '1px solid var(--border)' }}>
              <div className="empty-icon" style={{ fontSize: 40, marginBottom: 10 }}>📭</div>
              <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8 }}>No meeting requests yet for {teacherName}</div>
              <div style={{ fontSize: 12, color: 'var(--text2)', maxWidth: 420, margin: '0 auto 16px', lineHeight: 1.5 }}>
                When students search in the Student Portal and click <strong>"Send Meeting Request"</strong> on your profile ({facultyId}),
                requests will appear here instantly.
              </div>
              <a href="#/student" target="_blank" rel="noreferrer" className="btn" style={{ fontSize: 12, padding: '7px 16px', textDecoration: 'none' }}>
                Open Student Portal to send a test request →
              </a>
            </div>
          )}

          {/* Group: Pending first, then Accepted, then Declined */}
          {['pending', 'accepted', 'declined'].map(status => {
            const group = requests.filter(r => r.status === status)
            if (!group.length) return null
            const labels = { pending: '⏳ Pending Requests', accepted: '✅ Accepted Requests', declined: '❌ Declined Requests' }
            return (
              <div key={status} style={{ marginBottom: 24 }}>
                <div style={{ fontSize: 12, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, fontWeight: 700 }}>
                  {labels[status]} ({group.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {group.map(req => (
                    <div key={req.request_id} className="request-card"
                      style={{
                        padding: 16, background: 'var(--bg3)', borderRadius: 10,
                        border: req.status === 'pending' ? '1px solid var(--accent)' : '1px solid var(--border)',
                        position: 'relative'
                      }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
                        <div>
                          <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--text)' }}>
                            {req.student_name}
                            <span className="chip" style={{ marginLeft: 8, fontSize: 11, fontFamily: 'var(--mono)' }}>
                              {req.session_id || req.student_email?.split('@')[0]}
                            </span>
                          </div>
                          <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 2 }}>
                            Email: <span style={{ color: 'var(--text2)' }}>{req.student_email}</span>
                            {req.created_at && (
                              <span> · {new Date(req.created_at * 1000).toLocaleString()}</span>
                            )}
                          </div>
                        </div>

                        <span className={`badge ${req.status === 'accepted' ? 'both' : req.status === 'declined' ? 'inferred' : 'stated'}`}>
                          {req.status.toUpperCase()}
                        </span>
                      </div>

                      {/* Topic & Slot */}
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
                        <span className="chip" style={{ background: 'var(--bg2)', color: 'var(--accent)', borderColor: 'var(--accent)' }}>
                          📌 Topic: {req.topic}
                        </span>
                        {req.slot && (
                          <span className="chip" style={{ background: 'var(--bg2)' }}>
                            🕒 Requested Slot: {req.slot}
                          </span>
                        )}
                      </div>

                      {/* Message Body */}
                      <div style={{
                        padding: '10px 14px', background: 'var(--bg2)', borderRadius: 8,
                        border: '1px solid var(--border)', fontSize: 12, color: 'var(--text)',
                        lineHeight: 1.5, marginBottom: 12
                      }}>
                        <div style={{ fontSize: 10, color: 'var(--text3)', textTransform: 'uppercase', marginBottom: 4 }}>
                          Student Note:
                        </div>
                        {req.message}
                      </div>

                      {/* Response actions for pending requests */}
                      {req.status === 'pending' ? (
                        <div style={{ display: 'flex', gap: 8 }}>
                          <button className="btn" style={{ fontSize: 12, padding: '6px 16px' }}
                            onClick={() => respondToRequest(req.request_id, true)}>
                            ✓ Accept Request
                          </button>
                          <button className="btn secondary" style={{ fontSize: 12, padding: '6px 14px' }}
                            onClick={() => respondToRequest(req.request_id, false)}>
                            ✕ Decline
                          </button>
                        </div>
                      ) : (
                        <div style={{ fontSize: 11, color: 'var(--text3)' }}>
                          Status: <strong style={{ color: req.status === 'accepted' ? 'var(--success)' : 'var(--danger)' }}>
                            {req.status.toUpperCase()}
                          </strong>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* ── Timetable tab ──────────────────────────────────────────────── */}
      {activeTab === 'timetable' && (
        <div>
          <div style={{ padding: 16, background: 'var(--bg3)', borderRadius: 10, border: '1px solid var(--border)', marginBottom: 20 }}>
            <h4 style={{ margin: '0 0 12px', fontSize: 14 }}>Schedule New Free Slot / Commitment</h4>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
              <select className="filter-select" value={ttEntry.day}
                onChange={e => setTtEntry({ ...ttEntry, day: e.target.value })}>
                {DAYS.map(d => <option key={d} value={d}>{d}</option>)}
              </select>

              <input className="form-input" style={{ width: 100, fontSize: 12 }} type="time"
                value={ttEntry.start}
                onChange={e => setTtEntry({ ...ttEntry, start: e.target.value })} />

              <span style={{ color: 'var(--text3)', fontSize: 12 }}>to</span>

              <input className="form-input" style={{ width: 100, fontSize: 12 }} type="time"
                value={ttEntry.end}
                onChange={e => setTtEntry({ ...ttEntry, end: e.target.value })} />

              <select className="filter-select" value={ttEntry.type}
                onChange={e => setTtEntry({ ...ttEntry, type: e.target.value })}>
                <option value="class">Class</option>
                <option value="lab">Lab</option>
                <option value="meeting">Meeting</option>
                <option value="tutorial">Tutorial</option>
              </select>

              <input className="form-input" style={{ width: 120, fontSize: 12 }}
                placeholder="Room / Venue"
                value={ttEntry.room}
                onChange={e => setTtEntry({ ...ttEntry, room: e.target.value })} />

              <button className="btn" style={{ fontSize: 12, padding: '7px 16px' }}
                onClick={addTimetableEntry}>
                + Add Slot
              </button>
            </div>
          </div>

          {/* Current schedule display */}
          <div style={{ background: 'var(--bg3)', borderRadius: 10, border: '1px solid var(--border)', padding: 16 }}>
            <h4 style={{ margin: '0 0 14px', fontSize: 14 }}>Weekly Calendar Entries</h4>
            {timetable.length === 0 ? (
              <div style={{ color: 'var(--text3)', fontSize: 12 }}>No timetable entries recorded.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {timetable.map((item, idx) => (
                  <div key={idx} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '8px 12px', background: 'var(--bg2)', borderRadius: 6,
                    border: '1px solid var(--border)'
                  }}>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                      <span className="badge stated" style={{ width: 42, textAlign: 'center' }}>{item.day}</span>
                      <span style={{ fontSize: 12, fontWeight: 700, fontFamily: 'var(--mono)', color: 'var(--text)' }}>
                        {item.start} – {item.end}
                      </span>
                      <span className="chip" style={{ textTransform: 'capitalize', fontSize: 10 }}>{item.type}</span>
                      {item.room && <span style={{ fontSize: 11, color: 'var(--text3)' }}>📍 {item.room}</span>}
                    </div>
                    <button onClick={() => removeEntry(idx)}
                      style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', fontSize: 12, padding: '2px 8px' }}>
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
