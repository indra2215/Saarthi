# IMPLEMENTATION_PLAN.md — Agent prompt and build plan

Use this file as the working brief for a coding agent (Antigravity or any other). It is self-contained. If `CONTEXT.md`, `PLAN.md`, `EVALUATOR_QA.md` and `WRITTEN_DISCUSSION.md` exist in the repo, read them too; where they disagree with this file, ask the user.

---

## 0. Kickoff prompt (paste this into the agent)

```
You are the lead engineer for "Faculty Research Discovery Assistant"
(hackathon JIG26_23, Track C: NLP, LLM and RAG, team ERROR 404).

Read IMPLEMENTATION_PLAN.md fully, then CONTEXT.md if present.
Work milestone by milestone (M0 to M9). For each milestone:
  1. State the plan in 5 lines or fewer.
  2. Implement it.
  3. Run the tests and the acceptance check listed for that milestone.
  4. Commit with message "M<n>: <summary>".
  5. Stop and report: what works, what failed, what you assumed.
Do not start the next milestone until the acceptance check passes or I say continue.

Hard rules:
- Use only consented data or public APIs (OpenAlex, Semantic Scholar, Crossref, ORCID).
  Never scrape LinkedIn or Google Scholar. LinkedIn is stored as a link only.
- Resolve entities and assign faculty_id BEFORE chunking. Never merge people on name alone.
- Every result must return expertise_basis (STATED | INFERRED | BOTH) with separate
  stated_evidence and inferred_evidence lists.
- If a name query matches several faculty_ids with similar confidence, return a
  disambiguation response. Never guess.
- Never invent data, results or metrics. Synthetic demo data must be labelled synthetic.
- Ask me when a requirement is unclear.
```

---

## 1. Goal

A web app where students search faculty by research topic or name and get ranked faculty with cited evidence, a profile card, a drafted contact email, and suggested meeting slots from the class timetable. Many students can use it at once. A dashboard shows retrieval happening stage by stage, slowly enough for evaluators to follow.

Must-have behaviours from the problem statement and the release addendum:

1. Metadata-rich corpus with normalized names and topics.
2. Hybrid retrieval: BM25 plus vector, fused with RRF, then cross-encoder reranking.
3. Ranked faculty with supporting publications or passages.
4. Evaluation of ten queries with relevance measures, including at least one deliberate duplicate-name query and a report of how it is disambiguated.
5. For every returned result, report separately whether it reflects stated expertise or only an inference from publication similarity. Written discussion of why that matters.
6. Interface with filters and citation links.

## 2. Stack (default; change only if the user agrees)

| Layer | Choice |
|-------|--------|
| Language | Python 3.11 |
| API | FastAPI plus Uvicorn, Server-Sent Events for the trace |
| Keyword | `rank_bm25` |
| Vectors | `sentence-transformers` (`all-MiniLM-L6-v2` or `bge-small-en-v1.5`) plus FAISS (or Chroma) |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Storage | SQLite for sessions and records, JSON files in `data/processed` |
| Name matching | `rapidfuzz` |
| Tests | `pytest` |
| Frontend | React (Vite) plus D3 force graph |

Everything must run on a laptop without a GPU and, once data is cached, without internet.

## 3. Repository layout

```
/data         raw/, processed/, taxonomy.yaml
/ingest       sources.py, normalize.py, entity_resolution.py, canonical.py, chunk.py, build_index.py
/retrieval    bm25.py, vector.py, rrf.py, rerank.py, evidence.py, pipeline.py
/api          main.py, schemas.py, sessions.py, slots.py, email_draft.py
/web          React app
/eval         queries.json, judgments.json, duplicates_truth.json, run_eval.py,
              results.md, basis_report.md, disambiguation_report.md
/tests        one test file per module
CONTEXT.md  PLAN.md  EVALUATOR_QA.md  WRITTEN_DISCUSSION.md  IMPLEMENTATION_PLAN.md
```

## 4. Data schemas

Canonical faculty record (`data/processed/faculty.json`):

```json
{
  "faculty_id": "F012",
  "display_name": "Dr. Ravi Rao",
  "name_variants": ["R. Rao", "Ravi K. Rao"],
  "department": "CSE",
  "qualification": "PhD, IIT Madras",
  "email": "ravi.rao@college.edu",
  "orcid": null,
  "linkedin_url": null,
  "scholar_url": null,
  "photo_url": null,
  "consent": true,
  "synthetic": false,
  "stated_topics": ["natural language processing"],
  "bio": "...",
  "publications": [{"pub_id": "P1", "title": "", "year": 2023, "venue": "", "abstract": "", "keywords": [], "url": ""}],
  "projects": [{"project_id": "J1", "title": "", "description": "", "year": 2024}],
  "timetable": [{"day": "Mon", "start": "10:00", "end": "11:00", "type": "class"}]
}
```

Chunk record (indexed):

```json
{
  "chunk_id": "F012-P1-0",
  "faculty_id": "F012",
  "source_type": "PROFILE_KEYWORDS | PROFILE_BIO | PROJECT_DESC | PUBLICATION",
  "text": "[Faculty: Dr. Ravi Rao | ID: F012 | Dept: CSE | Source: PUBLICATION | Year: 2023 | Topics: nlp]\n<passage>",
  "department": "CSE",
  "year": 2023,
  "topics": ["natural language processing"],
  "url": "https://..."
}
```

Search result:

```json
{
  "faculty_id": "F012", "display_name": "", "department": "", "score": 0.0,
  "expertise_basis": "STATED | INFERRED | BOTH",
  "label": "Stated expertise | Inferred from publications | Stated + publications",
  "stated_evidence":   [{"source_type": "", "passage": "", "url": ""}],
  "inferred_evidence": [{"passage": "", "source_title": "", "year": 0, "url": "", "match_mode": "LEXICAL | SEMANTIC", "score": 0.0}]
}
```

## 5. Milestones

### M0 — Scaffold (acceptance: `pytest` runs, `uvicorn api.main:app` starts)
- Create the layout above, `requirements.txt`, `.gitignore`, a `Makefile` or `scripts/` with `ingest`, `index`, `serve`, `eval`, `test`.
- `/health` endpoint returns `{"ok": true}`.
- Config file `config.yaml`: model names, thresholds, delays, top-k sizes. No magic numbers in code.

### M1 — Data intake (acceptance: `data/processed/faculty.json` validates against the schema)
- Load names and qualifications from `data/raw/faculty.csv`. Required columns: `name, qualification`; optional: `department, email, orcid, linkedin_url, consent`.
- `sources.py`: fetch publications by author name plus affiliation from OpenAlex (primary), Semantic Scholar and Crossref (fallback); store ORCID when present. Cache every API response under `data/raw/cache/` so the app runs offline afterwards. Respect rate limits and set a polite `User-Agent` with a contact email from config.
- Records without `consent: true` are excluded from all later steps.
- If a field is missing, leave it null. Never fabricate.
- If demo data must be synthetic, set `synthetic: true` on those records. The UI footer must show a notice when any synthetic record is in use.
- Create at least 3 deliberate duplicate-name pairs (same or near-identical normalized name, different department or qualification, different publications). Record who owns what in `eval/duplicates_truth.json`.

### M2 — Normalization and entity resolution (acceptance: tests for duplicates pass)
- `normalize.py`:
  - `normalize_name(s)`: lowercase, strip titles (dr, prof, mr, mrs, ms), remove diacritics and punctuation, collapse spaces, reduce given names to initials for blocking.
  - `normalize_topic(s)`: lowercase, lemmatize, expand abbreviations using `data/taxonomy.yaml` (NLP, ML, LLM, CV, IR), map synonyms to a canonical topic.
- `entity_resolution.py`:
  - Blocking key: normalized last name plus first initial.
  - Pair score (weights in config): ORCID equal (decisive), email equal (decisive), department equal, qualification similar (rapidfuzz), publication overlap (shared titles or DOIs), co-author overlap.
  - Thresholds: `score >= HIGH` merge, `score <= LOW` separate, between: separate and add to `needs_review`.
  - Rule: never merge on name similarity alone.
- `canonical.py`: assemble one record per `faculty_id`.
- Tests: two same-name people with different departments stay separate; the same person from two sources with a matching ORCID merges; an ambiguous pair lands in `needs_review`.

### M3 — Contextual chunking and indexes (acceptance: a test query returns chunks with correct `faculty_id`)
- `chunk.py`: passage chunks of about 150 to 250 tokens with a small overlap. Prepend the metadata header shown in section 4. Set `source_type`:
  - `PROFILE_KEYWORDS` from `stated_topics`, `PROFILE_BIO` from `bio`, `PROJECT_DESC` from project descriptions, `PUBLICATION` from title plus abstract plus keywords.
- `build_index.py`: build BM25 over the chunk text and a FAISS index over embeddings of the same text. Persist to `data/processed/index/`. Index building must be deterministic and runnable from one command.
- Both indexes support filtering on `department`, `year`, `source_type` (apply filters before ranking, or over-fetch then filter).

### M4 — Hybrid retrieval (acceptance: `pipeline.search()` returns ranked faculty with a full trace)
- `bm25.py`: top 50 chunks. `vector.py`: top 50 chunks. Run both on the same normalized query.
- `rrf.py`:

```python
def rrf(ranked_lists, k=60, top_n=30):
    scores = {}
    for lst in ranked_lists:              # each list is [chunk_id, ...] best first
        for rank, cid in enumerate(lst, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=scores.get, reverse=True)[:top_n]
```

- `rerank.py`: cross-encoder over the top 30 (query, chunk text) pairs, return the top 10 chunks with scores. Batch the call.
- `evidence.py`: group the reranked chunks per `faculty_id` and compute `expertise_basis` exactly as follows:

```python
FACULTY_AUTHORED = {"PROFILE_KEYWORDS", "PROFILE_BIO", "PROJECT_DESC"}

def build_basis(chunks, query_topics, rerank_threshold):
    stated = [c for c in chunks
              if c.source_type in FACULTY_AUTHORED and names_topic(c.text, query_topics)]
    inferred = [c for c in chunks
                if c.source_type == "PUBLICATION" and c.rerank_score >= rerank_threshold]
    if stated and inferred: basis = "BOTH"
    elif stated:            basis = "STATED"
    else:                   basis = "INFERRED"
    return basis, stated, inferred
```

  - `names_topic` returns true only if the topic (after normalization and taxonomy expansion) appears explicitly in the faculty-authored text. A semantic-only match against faculty text does not count as stated.
  - For each inferred item set `match_mode = "LEXICAL"` if any normalized query topic appears in the passage, else `"SEMANTIC"`.
  - Faculty score is the max of the top 3 chunk scores for that person.
  - If a faculty member has no stated item and no inferred item above the threshold, drop them from results.
- `pipeline.py`:
  - Emit a trace event after each stage: `{stage: "bm25|vector|rrf|rerank|final", items: [{faculty_id, chunk_id, rank, score}], ms}`.
  - Return `{results, trace}`.
  - Name queries: before retrieval, run `resolve_name_query()`. If more than one `faculty_id` matches and the confidence gap is below `disambiguation_gap` in config, return `{status: "disambiguation", options: [...]}` and run no retrieval.
- Tests: ranking order is stable; a publication-only match is `INFERRED`; a profile-keyword match is `STATED`; a mixed case is `BOTH`.

### M5 — API and sessions (acceptance: curl calls to every endpoint work; two sessions do not mix)
Endpoints:

```
POST /search        {session_id, query, filters}         -> results | disambiguation
POST /disambiguate  {session_id, query, faculty_id}      -> results restricted to that faculty_id
GET  /trace/{id}    Server-Sent Events, delay between stages from config (default 700 ms)
GET  /faculty/{id}  full profile with evidence and links
GET  /slots/{id}    free gaps from timetable, or {"available": false}
POST /draft-email   {faculty_id, student_name, topic, evidence_id} -> {subject, body, mailto}
GET  /session/{id}  history of that session's queries and results
```

- `sessions.py`: SQLite table of sessions and queries; an in-process job queue so many students can submit at once; results are saved so a student can leave and return.
- `slots.py`: working hours (config, default 09:00 to 17:00) minus timetable entries, keep gaps of at least 30 minutes, return the next 5 slots. No timetable: `{"available": false, "reason": "Schedule not available"}`.
- `email_draft.py`: template with student name, topic, one cited paper, and 2 to 3 slots. For `INFERRED` results the text must refer to the paper ("I read your paper ...") and must not claim the faculty member is an expert. Return a `mailto:` URL with encoded subject and body. An LLM may polish the text only if configured; the template works without one.
- Responses use Pydantic schemas in `schemas.py`.

### M6 — Evaluation (acceptance: `make eval` writes all three reports)
- `eval/queries.json`: ten queries, nine topic queries plus `Q-DUP`, the deliberate duplicate-name query (for example `R. Rao information retrieval`, built on a duplicate pair from M1). Include a spread of query types: topic, name lookup, publication plus year, project, filtered by department.
- `eval/judgments.json`: relevance labels 0 to 3 per query per candidate faculty, labelled by two people (store both labels and the agreed value). The agent must not make up labels; if they are missing, generate a labelling sheet (CSV) for the humans and stop.
- `run_eval.py`: compute Precision@5, Recall@10, MRR and nDCG@10 for four configurations: BM25 only, vector only, hybrid with RRF, hybrid with cross-encoder. Write `eval/results.md` with a per-query table and averages.
- `eval/basis_report.md`: one row per returned result for all ten queries:
  `| Query | Rank | Faculty | expertise_basis | Stated evidence (source) | Inferred evidence (publication, match_mode) |`
  followed by per-query counts of STATED, INFERRED and BOTH. Also report Precision@5 separately for STATED-basis and INFERRED-basis results.
- `eval/disambiguation_report.md` for `Q-DUP`: candidates found, signals used, decision (asked the user or auto-resolved and why), option chosen, results afterwards, and these metrics: option recall, merge errors, wrong-person leakage (using `duplicates_truth.json`), post-choice Precision@5, auto-resolve correctness. List failures honestly.
- Fill the real numbers into `WRITTEN_DISCUSSION.md` where it says `[FILL]`. Do not invent results.

### M7 — Frontend (acceptance: full demo path works with no manual steps)
- Search page: query box, filters (department, year range, source type, expertise basis), session id kept in local storage, optional topic matrix input (rows are students, columns are topics) for bulk submission.
- Disambiguation picker: cards with display name, department, qualification, one-line research summary; selecting one calls `/disambiguate`.
- Pipeline dashboard: four stage panels (BM25, Vector, RRF, Cross-encoder) that fill in as the SSE events arrive, with rank-change arrows between stages and the stage time in ms.
- Graph (D3 force layout): nodes for faculty, topics and publications. Faculty who match the same topic are clustered, with a caption "any of these can be contacted". Click a node to open the profile card. Reveal nodes gradually following the trace.
- Results list: grouped under "Stated expertise" and "Inferred from publications"; badge on each card; stated and inferred evidence in separate lists with citation links; inferred items show `match_mode`, score and the text "Based on publication similarity, not stated by the faculty member."
- Profile card: photo (placeholder if none), qualification, department, Scholar / ORCID / LinkedIn links (only if stored), free slots, email draft with Copy and Open-in-mail buttons.
- Evaluation page: results table, basis report, disambiguation report and the written discussion.
- Footer notice if any synthetic data is in use.
- Accessibility: keyboard navigation, labels on controls, colour is never the only signal.

### M8 — Hardening (acceptance: checklist below passes)
- Three browser windows search at once without interference.
- Offline mode: with the network off, search, profile, slots and email draft still work from cache.
- Records without consent never appear in results, the graph or the evaluation outputs.
- Empty query, unknown name, very long query and filter combinations with zero hits give clear messages, not errors.
- Cross-encoder fallback: if it fails to load, fall back to RRF order and show a visible notice.
- Latency: the real pipeline answers in under 3 s on a laptop for the demo queries; only the dashboard replay adds the display delay.

### M9 — Demo preparation (acceptance: a 5-minute dry run)
- `make demo` seeds data, builds indexes, starts the API and the web app.
- Script: problem and two hard rules (30 s) -> topic search with the slow dashboard (60 s) -> one stated and one inferred result side by side (60 s) -> `Q-DUP` disambiguation (45 s) -> profile, slots and email draft (45 s) -> evaluation table and the stated-versus-inferred discussion (45 s) -> two students in parallel (15 s).
- Print the top ten evaluator questions from `EVALUATOR_QA.md` and check that each has a matching screen or number in the app.

## 6. Definition of done

- [ ] Duplicates are separated before chunking; zero merge errors on `duplicates_truth.json`.
- [ ] Hybrid pipeline runs in the fixed order BM25 and vector, then RRF, then cross-encoder.
- [ ] Every result has `expertise_basis` and two separate evidence lists, and the UI shows them separately.
- [ ] `Q-DUP` is among the ten evaluated queries and `eval/disambiguation_report.md` exists with real numbers.
- [ ] `eval/results.md`, `eval/basis_report.md` and `WRITTEN_DISCUSSION.md` are filled from a real run.
- [ ] Only consented or public-API data is used; no scraping; synthetic data is labelled.
- [ ] Dashboard shows the stages slowly; graph, filters, citation links, profile, slots and email draft all work.
- [ ] Tests pass and `make demo` works from a clean checkout.

## 7. How the agent should work

- Keep each milestone small and runnable. Commit after each one.
- Write the test first for the logic with rules attached (entity resolution, `build_basis`, slots).
- Put thresholds and delays in `config.yaml`. Explain any value you pick, and say it is a starting point, not a tuned result.
- When data is missing (labels, timetable, consent), stop and ask. Do not fill gaps with invented values.
- At the end of every milestone report: done, not done, assumptions, and what you need from the user.
