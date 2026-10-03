# CONTEXT.md — Faculty Research Discovery Assistant

> Read this first. It is written so a new teammate or an AI coding agent can understand the whole project without any other file.

- Hackathon: JIG26 | Problem ID: JIG26_23 | Track C — NLP, LLM & RAG
- Team: ERROR 404 (TEAM-14)
- Domain: Academic discovery and knowledge graphs

---

## 1. What we are building

A web assistant where students type a research interest (or a faculty name) and get a ranked list of faculty who work on it, with proof (publications or passages), a profile card, a contact email draft, and suggested meeting times based on class timetables.

The two hard requirements in the problem statement:

1. **Stated expertise must be distinguished from inferred topic similarity.**
2. **Duplicate names must be handled** (two different people with the same or similar name).

## 2. Inputs we actually have

- A list of faculty **names and qualifications** (from the college database).
- Everything else is **enriched** from consented or public sources: publication APIs (OpenAlex, Semantic Scholar, Crossref, ORCID), the college database (department, email, timetable), and a consented profile URL (LinkedIn is stored as a link only).

## 3. Hard rules (do not break)

| # | Rule |
|---|------|
| R1 | Only use data that is consented or from public APIs. Do NOT scrape LinkedIn or Google Scholar pages. |
| R2 | LinkedIn is shown as a stored link only. Never fetch or parse it. |
| R3 | Every returned faculty result must carry at least one citation (passage plus source link). |
| R4 | Every returned result carries an `expertise_basis` of `STATED`, `INFERRED` or `BOTH`, plus the separate evidence lists behind it (see section 5). |
| R5 | A result is labelled "Stated expertise" only when faculty-authored text (research interests, bio, project description) explicitly names the topic. A match that rests only on publication similarity is labelled "Inferred from publications" and must never be worded as the faculty member's own claim. |
| R9 | Never merge two people on name alone. At least one strong identifier (ORCID, email) or several agreeing signals are required. |
| R10 | The evaluation set must include at least one deliberate duplicate-name query, and the report must show how it was disambiguated (section 13). |
| R6 | If a name query matches more than one `faculty_id` with similar confidence, the system must ask the user to choose. It must never guess. |
| R7 | Meeting slots come only from real timetable data. If none exists, show "Schedule not available". |
| R8 | If data is synthetic (for demo), say so in the UI footer. |

## 4. Key idea: combine and disambiguate BEFORE chunking

Chunking raw text first causes duplicate-name collisions and loses context. The fix is a pre-chunking pipeline:

```
raw sources
  -> 1. Entity resolution   (decide who is who, assign faculty_id)
  -> 2. Normalization       (names, topics, synonyms)
  -> 3. Canonical record    (one record per faculty_id with all evidence)
  -> 4. Source typing       (faculty-authored PROFILE/PROJECT vs PUBLICATION)
  -> 5. Contextual chunking (each chunk gets a metadata header)
  -> 6. Indexing            (BM25 index + vector index, both keyed by faculty_id)
```

### 4.1 Entity resolution (duplicate names)

- Normalize: lowercase, strip titles (Dr., Prof.), remove diacritics, expand or reduce initials ("R. Rao" ~ "Ravi Rao"), collapse spaces.
- Block: group candidates by normalized last name plus first initial.
- Score each pair using these signals: ORCID / Scholar ID (strong), email (strong), department, qualification, institution, co-authors, publication overlap.
- Decision:
  - score >= HIGH -> merge into the same `faculty_id`
  - score <= LOW -> different people, different `faculty_id`
  - in between -> flag `needs_review` and keep separate
- At query time, a name matching several `faculty_id` values with a small confidence gap returns a **disambiguation response** (see API), and the UI shows a picker with department and qualification.

### 4.2 Normalization

- Topic normalization: lowercase, lemmatize, expand abbreviations (NLP = natural language processing, ML = machine learning), map synonyms to a canonical topic via a small taxonomy file (`data/taxonomy.yaml`).
- Name normalization: see 4.1.

### 4.3 Canonical record (one per faculty)

```json
{
  "faculty_id": "F012",
  "display_name": "Dr. Ravi Rao",
  "name_variants": ["R. Rao", "Ravi K. Rao"],
  "department": "CSE",
  "qualification": "PhD, IIT Madras",
  "email": "ravi.rao@college.edu",
  "orcid": "0000-0000-0000-0000",
  "linkedin_url": "https://...",
  "consent": true,
  "stated_topics": ["nlp", "information retrieval"],
  "publications": [{"pub_id": "P1", "title": "...", "year": 2023, "venue": "...", "abstract": "...", "url": "..."}],
  "projects": [{"project_id": "J1", "title": "...", "description": "...", "year": 2024}],
  "timetable": [{"day": "Mon", "start": "10:00", "end": "11:00", "type": "class"}]
}
```

### 4.4 Contextual chunking

Chunk at passage level (abstract, project description, profile bio), about 150-250 tokens with a small overlap. **Prepend a metadata header to every chunk before embedding and BM25 indexing**:

```
[Faculty: Dr. Ravi Rao | ID: F012 | Dept: CSE | Source: PUBLICATION | Year: 2023 | Topics: nlp, retrieval]
<passage text>
```

Each chunk also stores filterable metadata: `faculty_id, department, year, source_type, evidence_type, url, topics`.

Two index levels:
- Passage level: used for ranking and citations.
- Faculty level: passage scores are aggregated per `faculty_id` (use max of the top 3 passage scores) to produce the final faculty ranking.

## 5. Retrieval techniques (how and why)

| Technique | What it does | Strength | Weakness |
|-----------|--------------|----------|----------|
| BM25 (keyword) | Scores by term frequency and rarity of query words in a passage | Exact terms, names, acronyms, rare words | Misses synonyms and paraphrases |
| Vector search | Embeds query and passages, ranks by cosine similarity | Meaning match, synonyms ("LLM" vs "language model") | Can return plausible but unlisted topics; weak on exact names |
| RRF (Reciprocal Rank Fusion) | Merges several ranked lists using ranks only: `score(d) = sum over lists of 1 / (k + rank_in_list(d))`, k = 60 | No score normalization needed; robust | Ignores how confident each retriever was |
| Cross-encoder rerank | Reads query and passage together and outputs a relevance score | Most accurate ordering | Slow, so run only on the top 20-30 |

Pipeline order (fixed): `BM25 top 50 || Vector top 50 -> RRF -> top 30 -> cross-encoder -> top 10 passages -> aggregate per faculty_id -> ranked faculty`.

Why hybrid: BM25 catches exact names and acronyms; vectors catch meaning. RRF combines them without tuning weights. The cross-encoder fixes the final ordering.

### Stated vs inferred (revised for the release addendum)

Every chunk has a `source_type`: `PROFILE_KEYWORDS`, `PROFILE_BIO`, `PROJECT_DESC` (faculty-authored) or `PUBLICATION` (title, abstract, author keywords).

Definitions:

- **STATED**: faculty-authored text explicitly names the topic (after taxonomy normalization). The faculty member declared it. A purely semantic match against faculty text does not count; the topic must actually be named.
- **INFERRED**: the only support is a publication whose text is similar to the query, by keyword overlap (`match_mode = LEXICAL`) or embedding similarity (`match_mode = SEMANTIC`). Publications prove work was done, but the link to the query topic is our inference, not their claim. A `SEMANTIC` match is the weakest kind.
- **BOTH**: a stated item exists and at least one publication supports it.

Decision logic per faculty member (run on that member's top reranked chunks):

```
stated   = [c for c in chunks if c.source_type in FACULTY_AUTHORED and names_topic(c, query_topics)]
inferred = [c for c in chunks if c.source_type == "PUBLICATION" and c.rerank_score >= T]
basis    = "BOTH" if stated and inferred else "STATED" if stated else "INFERRED"
```

Reporting rules:

- The two evidence lists are kept and shown separately: `stated_evidence` and `inferred_evidence`. Never merge them into one list.
- The UI groups results under "Stated expertise" and "Inferred from publications", with the badge on each card. Ranking is by relevance; the system does not silently boost one group.
- Each inferred item shows its `match_mode` and score, and the card says "Based on publication similarity, not stated by the faculty member."
- The email draft for an INFERRED result refers to the paper ("I read your paper on X") and never says "I know you are an expert in X".
- Why this matters to a person relying on the result is written up in `WRITTEN_DISCUSSION.md`.

## 6. Query types

| Type | Example | Handling |
|------|---------|----------|
| Topic | "faculty working on federated learning" | Full hybrid pipeline |
| Name lookup | "Dr. Rao" | Entity match, disambiguation if more than one |
| Publication-based | "who published on graph neural networks in 2023" | Hybrid plus year filter |
| Project-based | "projects on smart agriculture" | Hybrid restricted to `source_type=PROJECT` |
| Filtered | "NLP faculty in CSE department" | Hybrid plus department filter |
| Natural-language need | "I want a guide for a thesis on medical image segmentation" | Hybrid, then rerank |
| Similar faculty | "faculty similar to Dr. Rao" | Vector over faculty-level embedding, always tagged INFERRED unless topics overlap |

## 7. Evaluation

- 10 topic queries, each with human relevance labels (0 = not relevant, 1 = partly, 2 = relevant, 3 = highly relevant) over the candidate faculty pool.
- Metrics: Precision@5, Recall@10, MRR, nDCG@10.
- Compare four configurations (ablation): BM25 only, Vector only, Hybrid (RRF), Hybrid + cross-encoder.
- Output a table to `eval/results.md` and show it in the UI.
- Of the 10 queries, at least one (`Q-DUP`) is a deliberate duplicate-name case. Its extra metrics and report are in section 13.
- For every result returned for every query, `eval/basis_report.md` records the faculty member, rank, `expertise_basis`, and the evidence behind it. Also report per query how many results were STATED, INFERRED and BOTH.
- Additional metric: Precision@5 computed separately for STATED-basis and INFERRED-basis results, to show whether inferred results hold up under human labelling.

## 8. Interface requirements

- Multi-student: each browser session gets a `session_id`; queries are queued; students can leave and return and see results again.
- Input: search box, filters (department, year, source type, evidence type), optional topic matrix (students x topics) for bulk submission.
- Dashboard: a graph of faculty, topics and publications. Results appear **slowly, stage by stage** (BM25 -> Vector -> RRF -> Cross-encoder) driven by a trace stream, so evaluators can watch the retrieval happen.
- Faculty profile card: photo (if consented), qualification, department, evidence list with citation links, Scholar / ORCID / LinkedIn links, email draft button, suggested meeting slots.
- Clusters: faculty working on the same topic are grouped so a student can contact any one.
- Disambiguation picker when names clash.

## 9. API contract

```
POST /search
  body: {session_id, query, filters: {department, year_from, year_to, source_type, evidence_type}}
  200:  {status: "ok", trace_id, results: [Result]}
        or {status: "disambiguation", options: [{faculty_id, display_name, department, qualification}]}

Result = {faculty_id, display_name, department, score,
          expertise_basis: "STATED"|"INFERRED"|"BOTH",
          label: "Stated expertise"|"Inferred from publications"|"Stated + publications",
          stated_evidence:   [{source_type, passage, url}],
          inferred_evidence: [{passage, source_title, year, url, match_mode: "LEXICAL"|"SEMANTIC", score}]}

GET  /trace/{trace_id}          -> Server-Sent Events: {stage, items:[{faculty_id, rank, score}], ms}
GET  /faculty/{faculty_id}      -> full profile
GET  /slots/{faculty_id}        -> [{day, start, end}] free gaps (or {available:false})
POST /draft-email               body: {faculty_id, student_name, topic, evidence_id} -> {subject, body, mailto}
POST /disambiguate              body: {session_id, query, faculty_id} -> same shape as /search results
```

## 10. Suggested stack

- Backend: Python, FastAPI
- Keyword: `rank_bm25` (or Elasticsearch)
- Vector: `sentence-transformers` (e.g. all-MiniLM-L6-v2 or bge-small) with FAISS or Chroma
- Cross-encoder: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Data: SQLite or Postgres for records, files in `data/`
- Frontend: React plus D3 (or vis-network) for the graph
- Email draft: template with optional LLM, delivered via a `mailto:` link

## 11. Repository layout

```
/data         raw/, processed/, taxonomy.yaml
/ingest       sources.py, entity_resolution.py, normalize.py, chunk.py, build_index.py
/retrieval    bm25.py, vector.py, rrf.py, rerank.py, pipeline.py, evidence.py
/api          main.py, sessions.py, slots.py, email_draft.py
/web          React app
/eval         queries.json, judgments.json, run_eval.py, results.md,
              basis_report.md, disambiguation_report.md
CONTEXT.md  PLAN.md  EVALUATOR_QA.md  WRITTEN_DISCUSSION.md
```

## 12. Glossary

- **RAG**: retrieve relevant text, then use it as evidence (and optionally as LLM input).
- **Entity resolution**: deciding which records refer to the same real person.
- **Chunk / passage**: a small piece of text that is indexed and retrieved.
- **RRF**: Reciprocal Rank Fusion, a rank-only way to merge result lists.
- **Cross-encoder**: a model that scores a (query, passage) pair together.
- **nDCG / MRR**: ranking quality metrics.

## 13. Release addendum (announced at release)

Requirement text: include at least one deliberate duplicate-name case among the ten evaluated queries and report how the system disambiguates it; for each result returned, report separately whether it reflects expertise the faculty member explicitly stated or only a topic-similarity inference from their publications; and discuss in writing why this distinction matters to someone relying on the result.

| Requirement | Where it is met |
|-------------|-----------------|
| Duplicate-name case among the ten queries | `Q-DUP` in `eval/queries.json`, built from at least two faculty with the same or near-identical name |
| Report how it is disambiguated | `eval/disambiguation_report.md` |
| Per-result stated vs inferred report | `expertise_basis` field plus `eval/basis_report.md` |
| Written discussion | `WRITTEN_DISCUSSION.md`, also shown on the evaluation page |

### 13.1 The Q-DUP query

Design: the corpus contains at least two real or constructed faculty with the same normalized name (for example two "R. Rao" in different departments), each with distinct research areas. `Q-DUP` is an ambiguous query such as `R. Rao information retrieval`, written so that both people could plausibly match.

Expected system behaviour:

1. Name normalization maps the query name to all matching `faculty_id` values.
2. The confidence gap between candidates is below the threshold, so the API returns `status: "disambiguation"` with options (display name, department, qualification, one-line research summary, ORCID if known).
3. The student (or the test script) selects one option; `/disambiguate` re-runs retrieval restricted to that `faculty_id` and returns evidence only from that person.
4. If the query also contains a department or topic that clearly separates the candidates, the system may resolve automatically, but it must state why ("matched department CSE").

What `eval/disambiguation_report.md` must contain:

- the query, the candidates found, and the signals used (name variants, department, qualification, ORCID, email, publication overlap)
- the system's decision (asked the user, or auto-resolved and why)
- the option chosen and the results returned afterwards
- the metrics below, and any failure cases honestly listed

Disambiguation metrics:

| Metric | Meaning | Target |
|--------|---------|--------|
| Option recall | share of true same-name people offered as options | 100% |
| Merge errors | different people wrongly given one `faculty_id` | 0 |
| Wrong-person leakage | returned evidence items that belong to another same-name person | 0 |
| Post-choice Precision@5 | relevance of results for the chosen person | report |
| Auto-resolve correctness | when auto-resolved, was it right | report |

### 13.2 Per-result basis report

`eval/basis_report.md` has one row per returned result for every evaluated query:

| Query | Rank | Faculty | expertise_basis | Stated evidence (source) | Inferred evidence (publication, match_mode) |
|-------|------|---------|-----------------|--------------------------|---------------------------------------------|

A short summary per query follows: counts of STATED, INFERRED, BOTH.

### 13.3 Written discussion

`WRITTEN_DISCUSSION.md` explains why the stated/inferred distinction matters to someone relying on a result. Fill in the real numbers from the report after the evaluation run. Do not invent results.

## 14. Instructions for AI agents working in this repo

1. Read this file and `PLAN.md`. Pick the first unchecked task in `PLAN.md`.
2. Respect rules R1-R10 above. Never add scraping of LinkedIn or Google Scholar.
3. Keep the pipeline order in section 5. Do not skip entity resolution before chunking.
4. Every function that returns faculty must include `expertise_basis` and the separate `stated_evidence` and `inferred_evidence` lists.
5. Add or update a test for each module. Check off the task in `PLAN.md` when done.
6. If a requirement is unclear, ask the team instead of guessing.
