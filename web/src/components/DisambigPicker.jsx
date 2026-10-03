import React from 'react'

export default function DisambigPicker({ options, query, onSelect }) {
  return (
    <div className="disambig" style={{ marginTop: 8, maxWidth: 520 }}>
      <div className="disambig-header">
        Multiple faculty found — who are you looking for?
      </div>
      {options.map(opt => (
        <div key={opt.faculty_id} className="disambig-option" onClick={() => onSelect(opt)}>
          <div>
            <div className="disambig-name">{opt.display_name}</div>
            <div className="disambig-dept">
              {opt.department_code} · {opt.qualification} · {opt.primary_domain}
            </div>
            {opt.research_areas?.length > 0 && (
              <div style={{ marginTop: 4, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {opt.research_areas.slice(0, 3).map((a, i) => (
                  <span key={i} className="chip">{a}</span>
                ))}
              </div>
            )}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
            <div className="disambig-conf">conf: {opt.confidence}</div>
            <button className="btn secondary" style={{ fontSize: 11, padding: '4px 12px' }}>
              Select
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
