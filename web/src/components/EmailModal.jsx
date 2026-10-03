import React, { useState } from 'react'

export default function EmailModal({ faculty, slots, student, onClose }) {
  const [studentName, setStudentName] = useState(student?.name || '')
  const [studentEmail, setStudentEmail] = useState(student?.rollNo ? `${student.rollNo}@student.kmec.edu.in` : '')
  const [topic, setTopic] = useState(faculty.primary_domain || '')
  const [draft, setDraft] = useState(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  const generate = async () => {
    setLoading(true)
    try {
      const res = await fetch('/draft-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          faculty_id: faculty.faculty_id,
          student_name: studentName,
          student_email: studentEmail,
          topic,
          expertise_basis: faculty.expertise_basis,
          slot_ids: slots.map(s => `${s.day} ${s.start}`)
        })
      })
      const data = await res.json()
      setDraft(data)
    } catch (e) { alert('Failed to generate draft') }
    setLoading(false)
  }

  const copy = () => {
    navigator.clipboard.writeText(`Subject: ${draft.subject}\n\n${draft.body}`)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        background: 'var(--bg2)', border: '1px solid var(--border)',
        borderRadius: 10, width: 560, maxHeight: '80vh',
        overflow: 'auto', padding: 24
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <div style={{ fontWeight: 600, fontSize: 14 }}>Draft Email — {faculty.display_name}</div>
          <button className="btn secondary" style={{ padding: '4px 12px', fontSize: 12 }} onClick={onClose}>✕</button>
        </div>

        {faculty.expertise_basis === 'INFERRED' && (
          <div className="notice-banner" style={{ marginBottom: 12 }}>
            This faculty was matched by publication similarity, not stated expertise.
            The email draft will reference their paper, not claim expertise.
          </div>
        )}

        {!draft ? (
          <>
            <div className="form-group">
              <label className="form-label">Your Name</label>
              <input className="form-input" value={studentName} onChange={e => setStudentName(e.target.value)} placeholder="e.g. Rahul Sharma" />
            </div>
            <div className="form-group">
              <label className="form-label">Your Email</label>
              <input className="form-input" value={studentEmail} onChange={e => setStudentEmail(e.target.value)} placeholder="student@kmec.edu.in" />
            </div>
            <div className="form-group">
              <label className="form-label">Research Topic</label>
              <input className="form-input" value={topic} onChange={e => setTopic(e.target.value)} />
            </div>
            <div style={{ fontSize: 12, color: 'var(--text3)', marginBottom: 12 }}>
              Available slots: {slots.length > 0
                ? slots.map(s => `${s.day} ${s.start}–${s.end}`).join(', ')
                : 'Not available — will omit slots'}
            </div>
            <div className="card-actions">
              <button className="btn" onClick={generate} disabled={!studentName || loading}>
                {loading ? <span className="spinner" /> : 'Generate Draft'}
              </button>
              <button className="btn secondary" onClick={onClose}>Cancel</button>
            </div>
          </>
        ) : (
          <>
            <div style={{ fontSize: 12, color: 'var(--text3)', marginBottom: 4 }}>Subject</div>
            <div style={{
              background: 'var(--bg3)', border: '1px solid var(--border)',
              borderRadius: 4, padding: '8px 12px', fontSize: 13,
              marginBottom: 12, fontWeight: 500
            }}>
              {draft.subject}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text3)', marginBottom: 4 }}>Body</div>
            <pre style={{
              background: 'var(--bg3)', border: '1px solid var(--border)',
              borderRadius: 4, padding: '12px', fontSize: 12,
              whiteSpace: 'pre-wrap', fontFamily: 'var(--mono)',
              color: 'var(--text2)', marginBottom: 16, maxHeight: 300, overflow: 'auto'
            }}>
              {draft.body}
            </pre>
            <div className="card-actions">
              <button className="btn" onClick={copy}>{copied ? 'Copied!' : 'Copy'}</button>
              <a className="btn secondary" href={draft.mailto} style={{ textDecoration: 'none' }}>
                Open in Mail
              </a>
              <button className="btn secondary" onClick={() => setDraft(null)}>Re-generate</button>
              <button className="btn secondary" onClick={onClose}>Close</button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
