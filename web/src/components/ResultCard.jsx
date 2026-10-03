import React, { useState, useEffect } from 'react'
import EmailModal from './EmailModal'

// Anti-spam: allow up to 10 requests per student per faculty per 24h
function getRequestKey(facultyId, rollNo) {
  return `req_${facultyId}_${rollNo || 'guest'}`
}

function getRecentRequests(facultyId, rollNo) {
  try {
    const raw = localStorage.getItem(getRequestKey(facultyId, rollNo))
    if (!raw) return []
    const list = JSON.parse(raw)
    const cutoff = Date.now() - 24 * 60 * 60 * 1000
    return list.filter(ts => ts > cutoff)
  } catch (_) {
    return []
  }
}

function canSendRequest(facultyId, rollNo) {
  const recent = getRecentRequests(facultyId, rollNo)
  if (recent.length >= 10) {
    return { ok: false, reason: 'You have reached the maximum 10 requests to this faculty for today.' }
  }
  return { ok: true, count: recent.length }
}

function markRequestSent(facultyId, rollNo) {
  try {
    const recent = getRecentRequests(facultyId, rollNo)
    recent.push(Date.now())
    localStorage.setItem(getRequestKey(facultyId, rollNo), JSON.stringify(recent))
  } catch (_) {}
}

export default function ResultCard({ result, sessionId, student }) {
  const [open, setOpen]           = useState(false)
  const [showEmail, setShowEmail] = useState(false)
  const [showRequest, setShowRequest] = useState(false)
  const [slots, setSlots]         = useState(null)
  const [requestMsg, setRequestMsg] = useState('')
  const [requestSlot, setRequestSlot] = useState('')
  const [requestTopic, setRequestTopic] = useState('')
  const [requestStatus, setRequestStatus] = useState(null) // null | 'sending' | 'sent' | 'error' | 'blocked'
  const [blockReason, setBlockReason] = useState('')

  // Pre-fill topic and helpful message from result
  useEffect(() => {
    if (result.primary_domain) {
      setRequestTopic(result.primary_domain)
      if (!requestMsg) {
        setRequestMsg(`I have an interest in ${result.primary_domain} and would like to request guidance for potential research or project work.`)
      }
    }
  }, [result.primary_domain])

  const loadSlots = async () => {
    if (slots) return
    try {
      const res = await fetch(`/slots/${result.faculty_id}`)
      setSlots(await res.json())
    } catch (e) { setSlots({ available: false, reason: 'Failed to load' }) }
  }

  const basisClass = result.expertise_basis === 'STATED' ? 'stated'
    : result.expertise_basis === 'INFERRED' ? 'inferred' : 'both'

  const rollNo = student?.rollNo || localStorage.getItem('student_roll') || ''
  const studentName = student?.name || localStorage.getItem('student_name') || 'Student'

  const handleOpenRequest = () => {
    const check = canSendRequest(result.faculty_id, rollNo)
    if (!check.ok) {
      setBlockReason(check.reason)
      setRequestStatus('blocked')
    } else {
      setRequestStatus(null)
      setBlockReason('')
      if (!requestMsg) {
        setRequestMsg(`I have an interest in ${requestTopic || result.primary_domain || 'this topic'} and would like to discuss possible project collaboration.`)
      }
    }
    setShowRequest(true)
  }

  const sendRequest = async () => {
    const activeRoll = rollNo || '245324733083'
    const check = canSendRequest(result.faculty_id, activeRoll)
    if (!check.ok) {
      setRequestStatus('blocked')
      setBlockReason(check.reason)
      return
    }
    if (!requestMsg.trim()) {
      setBlockReason('Please write a brief message describing your interest.')
      setRequestStatus('blocked')
      return
    }

    setRequestStatus('sending')
    try {
      const params = new URLSearchParams({
        session_id:    sessionId || `STU-${activeRoll}`,
        faculty_id:    result.faculty_id,
        student_name:  studentName,
        student_email: `${activeRoll}@kmec.edu.in`,
        topic:         requestTopic || result.primary_domain || 'Research Discussion',
        message:       requestMsg,
        slot:          requestSlot || '',
      })

      const res = await fetch(`/student-request?${params.toString()}`, { method: 'POST' })
      const data = await res.json()

      if (data.ok) {
        markRequestSent(result.faculty_id, activeRoll)
        setRequestStatus('sent')
      } else {
        setRequestStatus('error')
        setBlockReason(data.detail || 'Server error. Please try again.')
      }
    } catch (e) {
      setRequestStatus('error')
      setBlockReason('Connection error. Is the server running?')
    }
  }

  return (
    <div className="result-card">
      <div className="card-header" onClick={() => { setOpen(o => !o); if (!open) loadSlots() }}>
        <div>
          <div className="card-name">
            {result.display_name}
            {result.is_hod && <span className="chip" style={{ marginLeft: 6 }}>HOD</span>}
            {result.is_phd && <span className="chip" style={{ marginLeft: 4 }}>PhD</span>}
          </div>
          <div className="card-meta">
            {result.department_code} · {result.designation} · {result.primary_domain}
          </div>
          <div style={{ marginTop: 4, display: 'flex', gap: 5, flexWrap: 'wrap' }}>
            {result.research_areas?.slice(0, 4).map((a, i) => (
              <span key={i} className="chip">{a}</span>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
          <span className={`badge ${basisClass}`}>{result.label}</span>
          <span className="card-score">⚡ {(result.score * 100).toFixed(0)}%</span>
          <span style={{ fontSize: 12, color: 'var(--text3)' }}>{open ? '▲' : '▼'}</span>
        </div>
      </div>

      {open && (
        <div className="card-body">
          {/* Detailed profile excerpt */}
          {result.detailed_profile && (
            <p style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 12, lineHeight: 1.6 }}>
              {result.detailed_profile}
            </p>
          )}

          {/* Stated evidence */}
          {result.stated_evidence?.length > 0 && (
            <div className="evidence-section">
              <div className="evidence-title">Stated in Profile:</div>
              {result.stated_evidence.map((ev, i) => (
                <div key={i} className="evidence-item">
                  <div style={{ fontSize: 10, color: 'var(--accent)', textTransform: 'uppercase', marginBottom: 2 }}>
                    {ev.source_type}
                  </div>
                  <div>{ev.passage}</div>
                </div>
              ))}
            </div>
          )}

          {/* Inferred evidence */}
          {result.inferred_evidence?.length > 0 && (
            <div className="evidence-section">
              <div className="evidence-title">Research Publications ({result.inferred_evidence.length}):</div>
              {result.inferred_evidence.map((ev, i) => (
                <div key={i} className="evidence-item">
                  <div style={{ fontWeight: 600, color: 'var(--text)' }}>
                    {ev.url ? (
                      <a href={ev.url} target="_blank" rel="noreferrer" style={{ color: 'var(--text)' }}>
                        {ev.source_title} ↗
                      </a>
                    ) : ev.source_title}
                    {ev.year && <span style={{ color: 'var(--text3)', fontWeight: 400, marginLeft: 6 }}>({ev.year})</span>}
                  </div>
                  <div style={{ color: 'var(--text2)', marginTop: 2 }}>{ev.passage}</div>
                  <span className="chip" style={{ marginTop: 4, display: 'inline-block', fontSize: 10 }}>
                    match: {ev.match_mode}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Free Slots */}
          <div style={{ marginBottom: 12 }}>
            <span style={{ fontSize: 11, color: 'var(--text3)', fontWeight: 600, textTransform: 'uppercase' }}>
              Free Meeting Slots:
            </span>
            {slots ? (
              slots.available && slots.slots?.length > 0 ? (
                <div style={{ marginTop: 4, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {slots.slots.map((s, i) => (
                    <span key={i} className="chip" style={{ background: 'var(--bg3)', borderColor: 'var(--accent)' }}>
                      {s.day} {s.start}–{s.end}
                    </span>
                  ))}
                </div>
              ) : (
                <span style={{ fontSize: 12, color: 'var(--text3)', marginLeft: 8 }}>
                  {slots.reason || 'No fixed office hours published'}
                </span>
              )
            ) : (
              <span style={{ fontSize: 12, color: 'var(--text3)', marginLeft: 8 }}>Loading...</span>
            )}
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
            <button className="btn" style={{ fontSize: 12, padding: '7px 14px' }}
              onClick={handleOpenRequest}>
              📅 Send Meeting Request
            </button>
            <button className="btn secondary" style={{ fontSize: 12, padding: '7px 14px' }}
              onClick={() => setShowEmail(true)}>
              ✉ Draft Email
            </button>
            {result.scholar_url && (
              <a href={result.scholar_url} target="_blank" rel="noreferrer" className="btn secondary"
                style={{ fontSize: 12, padding: '7px 14px', textDecoration: 'none' }}>
                Scholar ↗
              </a>
            )}
            {result.linkedin_url && (
              <a href={result.linkedin_url} target="_blank" rel="noreferrer" className="btn secondary"
                style={{ fontSize: 12, padding: '7px 14px', textDecoration: 'none' }}>
                LinkedIn ↗
              </a>
            )}
          </div>

          {/* Inline Send Request Form */}
          {showRequest && (
            <div style={{
              marginTop: 14,
              padding: 16,
              background: 'var(--bg2)',
              borderRadius: 8,
              border: '1px solid var(--accent)',
              animation: 'fadeIn 0.2s ease-out'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text)' }}>
                  Send Research Request to {result.display_name}
                </div>
                <button onClick={() => { setShowRequest(false); setRequestStatus(null); setBlockReason('') }}
                  style={{ background: 'none', border: 'none', color: 'var(--text3)', cursor: 'pointer', fontSize: 16, padding: '0 4px' }}>
                  ✕
                </button>
              </div>

              {requestStatus === 'sent' ? (
                <div style={{
                  padding: '16px 14px',
                  background: 'rgba(52,199,89,0.1)',
                  borderRadius: 8,
                  border: '1px solid var(--success)',
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: 24, marginBottom: 6 }}>✅</div>
                  <div style={{ fontWeight: 700, color: 'var(--success)', fontSize: 14, marginBottom: 4 }}>
                    Meeting Request Sent Successfully!
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text2)', maxWidth: 380, margin: '0 auto 12px', lineHeight: 1.5 }}>
                    Your request was delivered directly to {result.display_name}'s Faculty Portal in real-time.
                    You will be contacted at <code style={{ color: 'var(--accent)' }}>{rollNo || '245324733083'}@kmec.edu.in</code>.
                  </div>
                  <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
                    <a href="#/faculty" target="_blank" rel="noreferrer" className="btn secondary" style={{ fontSize: 11, padding: '5px 12px', textDecoration: 'none' }}>
                      Open Faculty Portal in new tab →
                    </a>
                    <button className="btn secondary" style={{ fontSize: 11, padding: '5px 12px' }}
                      onClick={() => { setRequestStatus(null); setShowRequest(false) }}>
                      Close
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  {(requestStatus === 'blocked' || requestStatus === 'error') && blockReason && (
                    <div style={{ color: 'var(--danger)', fontSize: 12, marginBottom: 12, padding: '8px 10px', background: 'rgba(224,80,80,0.08)', borderRadius: 6, border: '1px solid rgba(224,80,80,0.2)' }}>
                      {blockReason}
                    </div>
                  )}

                  {/* Student sender badge */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 10px', background: 'var(--bg3)', borderRadius: 6, marginBottom: 10, fontSize: 11 }}>
                    <span style={{ color: 'var(--text3)' }}>Sending as:</span>
                    <span style={{ fontWeight: 600, color: 'var(--accent)' }}>
                      {studentName} ({rollNo || '245324733083'})
                    </span>
                  </div>

                  <div className="form-group" style={{ marginBottom: 10 }}>
                    <label className="form-label">Topic / Research Area</label>
                    <input className="form-input" style={{ fontSize: 12 }}
                      value={requestTopic}
                      onChange={e => setRequestTopic(e.target.value)}
                      placeholder={result.primary_domain || 'e.g. Machine Learning, IoT...'} />
                  </div>

                  {slots?.available && slots.slots?.length > 0 && (
                    <div className="form-group" style={{ marginBottom: 10 }}>
                      <label className="form-label">Preferred Slot (optional)</label>
                      <select className="filter-select" style={{ width: '100%' }}
                        value={requestSlot} onChange={e => setRequestSlot(e.target.value)}>
                        <option value="">No preference / Any time</option>
                        {slots.slots.map((s, i) => (
                          <option key={i} value={`${s.day} ${s.start}-${s.end}`}>
                            {s.day} {s.start} – {s.end}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div className="form-group" style={{ marginBottom: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <label className="form-label" style={{ margin: 0 }}>
                        Your Message <span style={{ color: 'var(--danger)' }}>*</span>
                      </label>
                      <button
                        type="button"
                        onClick={() => setRequestMsg(`I have an interest in ${requestTopic || result.primary_domain || 'this topic'} and would like to request guidance for potential research or project work.`)}
                        style={{ background: 'none', border: 'none', color: 'var(--accent)', fontSize: 10, cursor: 'pointer', padding: 0, textDecoration: 'underline' }}>
                        Suggest template
                      </button>
                    </div>
                    <textarea className="form-input" rows={3} style={{ resize: 'vertical', fontSize: 12 }}
                      value={requestMsg}
                      onChange={e => setRequestMsg(e.target.value)}
                      placeholder="e.g. I have an interest in this topic and would like to collaborate..." />
                  </div>

                  {/* Preset quick message chips */}
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
                    {[
                      'I have an interest in this topic',
                      'Interested in B.Tech project guidance',
                      'Seeking research internship under your mentorship'
                    ].map((msg, i) => (
                      <button key={i} type="button"
                        onClick={() => setRequestMsg(`${msg} (${requestTopic || result.primary_domain || ''}).`)}
                        style={{
                          fontSize: 10, padding: '3px 8px', borderRadius: 4,
                          background: 'var(--bg3)', border: '1px solid var(--border)',
                          color: 'var(--text2)', cursor: 'pointer'
                        }}>
                        + "{msg}"
                      </button>
                    ))}
                  </div>

                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn" style={{ flex: 1, fontSize: 12, padding: '8px 16px' }}
                      onClick={sendRequest}
                      disabled={requestStatus === 'sending' || requestStatus === 'blocked'}>
                      {requestStatus === 'sending' ? (
                        <><span className="spinner" /> &nbsp;Sending...</>
                      ) : (
                        '🚀 Send Request to Faculty Portal'
                      )}
                    </button>
                    <button className="btn secondary" style={{ fontSize: 12, padding: '8px 14px' }}
                      onClick={() => { setShowRequest(false); setRequestStatus(null); setBlockReason('') }}>
                      Cancel
                    </button>
                  </div>
                </>
              )}
            </div>
          )}

          {showEmail && (
            <EmailModal
              faculty={result}
              slots={slots?.slots || []}
              student={student}
              onClose={() => setShowEmail(false)}
            />
          )}
        </div>
      )}
    </div>
  )
}
