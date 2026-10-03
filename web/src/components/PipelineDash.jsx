import React from 'react'

const STAGES = ['bm25', 'vector', 'rrf', 'rerank', 'final']
const LABELS = { bm25: 'BM25', vector: 'Vector', rrf: 'RRF', rerank: 'Rerank', final: 'Result' }

export default function PipelineDash({ stages, loading }) {
  const stageMap = Object.fromEntries(stages.map(s => [s.stage, s]))

  return (
    <div>
      <div style={{ fontSize: 10, color: 'var(--text3)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        Retrieval Pipeline
      </div>
      <div className="pipeline-dash">
        {STAGES.map((s, i) => {
          const data = stageMap[s]
          const isDone = !!data
          const isActive = !isDone && loading && stages.length === i
          return (
            <div key={s} className={`pipeline-stage ${isDone ? 'done' : isActive ? 'active' : ''}`}>
              <div className="stage-name">
                <span className={`stage-dot ${isDone ? 'done' : isActive ? 'active' : ''}`} />
                {LABELS[s]}
              </div>
              {isDone && (
                <>
                  <div className="stage-count">{data.count ?? data.items?.length ?? '—'}</div>
                  <div className="stage-ms">{data.ms}ms</div>
                </>
              )}
              {!isDone && isActive && <div className="stage-ms">running...</div>}
              {!isDone && !isActive && <div className="stage-ms">–</div>}
            </div>
          )
        })}
      </div>
    </div>
  )
}
