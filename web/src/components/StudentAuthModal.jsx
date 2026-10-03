import React, { useState } from 'react'

export default function StudentAuthModal({ onLogin, currentStudent, onCancel }) {
  const [rollNo, setRollNo] = useState(currentStudent?.rollNo || '')
  const [name, setName] = useState(currentStudent?.name || '')
  const [error, setError] = useState('')

  const validateRollNo = (val) => {
    const cleaned = val.replace(/[\s-]/g, '')
    // Must be 12 digits like 245324733083
    return /^[0-9]{12}$/.test(cleaned)
  }

  const handleSubmit = (e) => {
    e?.preventDefault()
    setError('')
    const cleanedRoll = rollNo.replace(/[\s-]/g, '')

    if (!cleanedRoll) {
      setError('Please enter your roll number.')
      return
    }

    if (!validateRollNo(cleanedRoll)) {
      setError('Invalid format! Roll number must be exactly 12 digits (e.g. 245324733083).')
      return
    }

    const studentName = name.trim() || `Student ${cleanedRoll.slice(-3)}`
    onLogin({
      rollNo: cleanedRoll,
      name: studentName,
      department: getDeptFromRoll(cleanedRoll)
    })
  }

  const getDeptFromRoll = (r) => {
    // 2453-YY-BRANCH-NUM (e.g. 733 -> CSE, 735 -> ECE, 737 -> IT, 748 -> AIML)
    const branchCode = r.slice(6, 9)
    const map = {
      '733': 'CSE',
      '735': 'ECE',
      '737': 'IT',
      '748': 'CSE-AIML',
    }
    return map[branchCode] || 'Engineering'
  }

  const handleUseDemo = () => {
    setRollNo('245324733083')
    setName('K. Ananya')
    setError('')
  }

  return (
    <div className="modal-backdrop">
      <div className="modal-card" style={{ maxWidth: 440, padding: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
          <img
            src="/logo.png"
            alt="KMEC Logo"
            style={{ width: 44, height: 44, borderRadius: 10, objectFit: 'cover', border: '1px solid var(--border)' }}
          />
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: 'var(--text)' }}>Student Authentication</h3>
            <p style={{ fontSize: 12, color: 'var(--text3)', margin: '2px 0 0' }}>Enter your 12-digit university roll number</p>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group" style={{ marginBottom: 14 }}>
            <label className="form-label" style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 6 }}>
              Student Full Name
            </label>
            <input
              className="form-input"
              type="text"
              placeholder="e.g. Rahul Sharma"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="form-group" style={{ marginBottom: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <label className="form-label" style={{ fontSize: 12, color: 'var(--text2)', margin: 0 }}>
                Roll Number (12 Digits) <span style={{ color: 'var(--danger)' }}>*</span>
              </label>
              <button
                type="button"
                onClick={handleUseDemo}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--accent)',
                  fontSize: 11,
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  padding: 0
                }}
              >
                Sample: 245324733083
              </button>
            </div>
            <input
              className="form-input"
              type="text"
              placeholder="e.g. 245324733083"
              value={rollNo}
              maxLength={14}
              onChange={(e) => {
                setRollNo(e.target.value)
                setError('')
              }}
              style={{
                fontFamily: 'var(--mono)',
                fontSize: 14,
                borderColor: error ? 'var(--danger)' : undefined
              }}
              autoFocus
            />
            <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 4 }}>
              Format: <code>245324733083</code> (College 2453 · Year 24 · Branch 733 · Roll 083)
            </div>
          </div>

          {error && (
            <div style={{
              background: 'rgba(255, 68, 68, 0.1)',
              border: '1px solid var(--danger)',
              borderRadius: 6,
              padding: '8px 12px',
              color: 'var(--danger)',
              fontSize: 12,
              marginBottom: 14
            }}>
              {error}
            </div>
          )}

          <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
            {onCancel && (
              <button type="button" className="btn secondary" style={{ flex: 1 }} onClick={onCancel}>
                Cancel
              </button>
            )}
            <button type="submit" className="btn" style={{ flex: 2 }}>
              Continue to Research Discovery →
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
