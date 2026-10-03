import React, { useState, useEffect, useRef } from 'react'
import PipelineDash from './PipelineDash'
import ResultCard from './ResultCard'
import DisambigPicker from './DisambigPicker'

const PREDEFINED = {
  topic: [
    'Who works on machine learning and deep learning?',
    'I want to research cybersecurity',
    'Show faculty working on cloud computing',
    'Find professors researching IoT and embedded systems',
    'Who can guide me on big data and analytics?',
    'Find faculty in NLP or natural language processing',
  ],
  name: [
    'Tell me about Dr. Balakrishna',
    'Find Dr. Srinivas',
    'Show CSE department professors',
    'Who are the HODs?',
  ]
}

export default function ChatView({ sessionId, indexReady, student }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hello! I'm your Faculty Research Discovery Assistant. Search by research topic (e.g. 'machine learning', 'cybersecurity') or faculty name (e.g. 'Dr. Balakrishna'). I'll find the best matching faculty with cited evidence.",
      type: 'welcome'
    }
  ])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [trace, setTrace] = useState([])
  const [traceId, setTraceId] = useState(null)
  const [filters, setFilters] = useState({})
  const [departments, setDepartments] = useState([])
  const [showFilters, setShowFilters] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    fetch('/departments').then(r => r.json()).then(setDepartments).catch(() => {})
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // SSE trace consumer
  useEffect(() => {
    if (!traceId) return
    const es = new EventSource(`/trace/${traceId}`)
    es.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.stage === 'done') { es.close(); return }
      setTrace(prev => {
        const existing = prev.findIndex(t => t.stage === data.stage)
        if (existing >= 0) {
          const next = [...prev]; next[existing] = data; return next
        }
        return [...prev, data]
      })
    }
    es.onerror = () => es.close()
    return () => es.close()
  }, [traceId])

  const handleSearch = async (q = query) => {
    if (!q.trim() || loading) return
    setLoading(true)
    setTrace([])
    setTraceId(null)

    setMessages(prev => [...prev, { role: 'user', content: q }])
    setQuery('')

    try {
      const res = await fetch('/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, query: q, filters })
      })
      const data = await res.json()

      if (data.status === 'disambiguation') {
        setMessages(prev => [...prev, {
          role: 'assistant',
          type: 'disambiguation',
          content: `I found multiple faculty members matching that name. Please select who you mean:`,
          options: data.options,
          query: q,
        }])
      } else if (data.status === 'ok') {
        if (data.trace_id) setTraceId(data.trace_id)
        const count = data.results?.length || 0
        setMessages(prev => [...prev, {
          role: 'assistant',
          type: 'results',
          content: count > 0
            ? `Found ${count} faculty member${count > 1 ? 's' : ''} matching "${q}". Topics detected: ${(data.query_topics || []).join(', ') || 'general'}`
            : `No faculty found for "${q}". Try a broader term like 'machine learning' or 'cloud computing'.`,
          results: data.results || [],
          traceId: data.trace_id,
          queryTopics: data.query_topics || [],
        }])
      } else {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.message || 'Something went wrong. Please try again.',
        }])
      }
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Connection error. Is the backend server running?',
      }])
    }
    setLoading(false)
  }

  const handleDisambiguate = async (option, query) => {
    setLoading(true)
    setTrace([])
    setMessages(prev => [...prev, {
      role: 'user',
      content: `Selected: ${option.display_name} (${option.department_code})`
    }])
    try {
      const res = await fetch('/disambiguate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, query, faculty_id: option.faculty_id })
      })
      const data = await res.json()
      if (data.trace_id) setTraceId(data.trace_id)
      setMessages(prev => [...prev, {
        role: 'assistant',
        type: 'results',
        content: `Showing results for ${option.display_name} (${option.department_code})`,
        results: data.results || [],
        traceId: data.trace_id,
        queryTopics: data.query_topics || [],
      }])
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error loading results.' }])
    }
    setLoading(false)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Pipeline dash (shows during/after search) */}
      {trace.length > 0 && (
        <div style={{ padding: '12px 24px 0', flexShrink: 0 }}>
          <PipelineDash stages={trace} loading={loading} />
        </div>
      )}

      {/* Chat messages */}
      <div className="chat-area">
        {messages.map((msg, i) => (
          <div key={i} className={`msg ${msg.role}`}>
            <div className="msg-avatar">{msg.role === 'user' ? 'YOU' : 'AI'}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="msg-bubble">
                <p>{msg.content}</p>
              </div>

              {/* Disambiguation picker */}
              {msg.type === 'disambiguation' && (
                <DisambigPicker
                  options={msg.options}
                  query={msg.query}
                  onSelect={(opt) => handleDisambiguate(opt, msg.query)}
                />
              )}

              {/* Results */}
              {msg.type === 'results' && msg.results?.length > 0 && (
                <div className="results-section">
                  {/* Group by basis */}
                  {['STATED', 'BOTH', 'INFERRED'].map(basis => {
                    const group = msg.results.filter(r => r.expertise_basis === basis)
                    if (!group.length) return null
                    const labels = { STATED: 'Stated Expertise', BOTH: 'Stated + Publications', INFERRED: 'Inferred from Publications' }
                    return (
                      <div key={basis} style={{ marginBottom: 16 }}>
                        <div className="results-header">
                          <span className={`badge ${basis.toLowerCase()}`}>{labels[basis]}</span>
                          <span style={{ marginLeft: 8 }}>{group.length} result{group.length > 1 ? 's' : ''}</span>
                        </div>
                        {group.map(r => (
                          <ResultCard key={r.faculty_id} result={r} sessionId={sessionId} student={student} />
                        ))}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="msg">
            <div className="msg-avatar">AI</div>
            <div className="msg-bubble">
              <span className="spinner" /> &nbsp; Searching through {' '}
              {trace.length > 0 ? `${trace[trace.length-1]?.stage?.toUpperCase()} stage` : 'BM25'} ...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Search bar */}
      <div className="search-area">
        {/* Suggestions */}
        <div className="suggestions">
          {PREDEFINED.topic.slice(0, 4).map((s, i) => (
            <button key={i} className="suggestion-chip" onClick={() => handleSearch(s)}>{s}</button>
          ))}
        </div>

        {/* Filters */}
        {showFilters && (
          <div className="filter-row" style={{ marginBottom: 8 }}>
            <select className="filter-select" onChange={e => setFilters(f => ({ ...f, department: e.target.value || undefined }))}>
              <option value="">All Departments</option>
              {departments.map(d => <option key={d.code} value={d.code}>{d.code} — {d.name}</option>)}
            </select>
            <select className="filter-select" onChange={e => setFilters(f => ({ ...f, source_type: e.target.value || undefined }))}>
              <option value="">All Sources</option>
              <option value="PROFILE_KEYWORDS">Stated Topics</option>
              <option value="PROFILE_BIO">Profile Bio</option>
              <option value="PROJECT_DESC">Projects</option>
              <option value="PUBLICATION">Publications</option>
            </select>
            <select className="filter-select" onChange={e => setFilters(f => ({ ...f, evidence_type: e.target.value || undefined }))}>
              <option value="">All Evidence</option>
              <option value="STATED">Stated Only</option>
              <option value="INFERRED">Inferred Only</option>
            </select>
          </div>
        )}

        <div className="search-row">
          <button className="btn secondary" style={{ padding: '10px 12px', fontSize: 12 }}
            onClick={() => setShowFilters(f => !f)}>
            {showFilters ? 'Hide' : 'Filters'}
          </button>
          <input
            className="search-input"
            placeholder="Search research topics or faculty names..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            disabled={loading || !indexReady}
          />
          <button className="btn" onClick={() => handleSearch()} disabled={loading || !query.trim() || !indexReady}>
            {loading ? <span className="spinner" /> : 'Search'}
          </button>
        </div>

        {!indexReady && (
          <div style={{ fontSize: 11, color: '#ff4444', marginTop: 6 }}>
            Search index not ready. Run: <code>python scripts/run_ingest.py</code>
          </div>
        )}
      </div>
    </div>
  )
}
