# PLAN.md — What to do, in order

Read `CONTEXT.md` first. Check off items as you finish them.

## Phase 0 — Setup (30 min)
- [ ] Create repo with the layout from CONTEXT.md section 11
- [ ] Python env, install: fastapi, uvicorn, rank_bm25, sentence-transformers, faiss-cpu (or chromadb), pyyaml, pytest
- [ ] Agree on the 10 demo topics and 3 demo duplicate-name cases

## Phase 1 — Corpus and entities (Day 1)
- [ ] Load names and qualifications from the college list into `data/raw/faculty.csv`
- [ ] Add department, email, consent flag, and timetable (CSV from college DB, or synthetic and labelled as synthetic)
- [ ] `sources.py`: fetch publications from OpenAlex / Semantic Scholar / Crossref by name plus affiliation; store `orcid` and `url`
- [ ] `normalize.py`: name normalization and topic normalization with `data/taxonomy.yaml`
- [ ] `entity_resolution.py`: blocking, pair scoring, HIGH/LOW thresholds, `needs_review` list
- [ ] Insert at least 3 deliberate duplicate-name cases (same or near-identical normalized name, different departments or qualifications). One of them is reserved for the evaluated query `Q-DUP`
- [ ] For each duplicate pair, record the ground truth (which publications and topics belong to whom) in `eval/duplicates_truth.json`
- [ ] Output `data/processed/faculty.json` (canonical records)
- Done when: every record has a unique `faculty_id` and no two real people share one

## Phase 2 — Chunking and indexes (Day 1-2)
- [ ] `chunk.py`: passage chunks (150-250 tokens), prepend the metadata header, attach filter metadata
- [ ] Tag each chunk `evidence_type` (STATED / PUBLISHED / PROJECT)
- [ ] `build_index.py`: BM25 index and vector index, both over the headed chunks
- Done when: searching "federated learning" returns chunks that carry `faculty_id`, `url`, `evidence_type`

## Phase 3 — Hybrid retrieval (Day 2)
- [ ] `bm25.py`: top 50 chunks
- [ ] `vector.py`: top 50 chunks
- [ ] `rrf.py`: `score = sum(1/(60+rank))`, return top 30
- [ ] `rerank.py`: cross-encoder over the top 30, return top 10
- [ ] `evidence.py`: aggregate per `faculty_id`; split chunks into faculty-authored and publication; compute `expertise_basis` (STATED / INFERRED / BOTH), keep `stated_evidence` and `inferred_evidence` as separate lists, set `match_mode` on inferred items (rules R4, R5)
- [ ] `names_topic()`: a stated match requires the topic to be explicitly named in faculty-authored text after taxonomy normalization; semantic-only matches count as INFERRED
- [ ] `pipeline.py`: run the stages and emit a trace event after each stage (stage name, ranked ids, ms)
- [ ] Filters: department, year range, source type, evidence type
- Done when: `pipeline.search(query, filters)` returns ranked faculty with citations and a full trace

## Phase 4 — API and sessions (Day 2-3)
- [ ] FastAPI endpoints from CONTEXT.md section 9
- [ ] Name-query path: return `status: "disambiguation"` when the confidence gap is small (rule R6)
- [ ] `sessions.py`: per-session history and a job queue so many students can submit at once
- [ ] `/trace/{id}` as Server-Sent Events with a deliberate delay between stages (about 600-900 ms) for the slow reveal
- [ ] `slots.py`: free gaps from timetable (working hours minus classes, minimum 30 min)
- [ ] `email_draft.py`: template with student name, topic, one cited paper, and 2-3 proposed slots; return a `mailto:` link
- Done when: curl calls to every endpoint work

## Phase 5 — Evaluation (Day 3)
- [ ] Write `eval/queries.json` with 10 queries: 9 topic queries plus `Q-DUP`, the deliberate duplicate-name query (or more than one duplicate-name query if you prefer)
- [ ] Label relevance 0-3 for candidate faculty per query (two people label, resolve disagreements)
- [ ] `run_eval.py`: compute Precision@5, Recall@10, MRR, nDCG@10 for BM25, Vector, Hybrid, Hybrid + cross-encoder
- [ ] Write the table to `eval/results.md`
- [ ] Run `Q-DUP`; write `eval/disambiguation_report.md` (candidates, signals, decision, chosen option, results after choice, option recall, merge errors, wrong-person leakage, post-choice P@5)
- [ ] Write `eval/basis_report.md`: one row per returned result for all ten queries with `expertise_basis`, stated evidence, inferred evidence and `match_mode`; add per-query counts of STATED / INFERRED / BOTH
- [ ] Compute Precision@5 separately for STATED-basis and INFERRED-basis results
- [ ] Fill the real numbers into `WRITTEN_DISCUSSION.md` and add 2-3 concrete examples from the run (one where inference was right, one where it was misleading)
- Done when: the table exists and the cross-encoder row is explained in 2 sentences

## Phase 6 — Interface (Day 3-4)
- [ ] Search page: query box, filters, optional topic matrix input, session id in local storage
- [ ] Disambiguation picker
- [ ] Dashboard: staged pipeline view (BM25 -> Vector -> RRF -> Cross-encoder) with rank-change animation
- [ ] Graph: faculty, topics, publications; cluster faculty on the same topic; click a node to open the profile
- [ ] Results list grouped under "Stated expertise" and "Inferred from publications", badge on each card, stated and inferred evidence in two separate lists with citation links, `match_mode` shown on inferred items
- [ ] Evaluation page showing the disambiguation report, the basis report and the written discussion
- [ ] Profile card: photo, qualification, evidence list, Scholar / ORCID / LinkedIn links, slots, email draft with Copy and Open-in-mail buttons
- [ ] Evaluation page showing the results table
- Done when: a full demo run works end to end with no manual steps

## Phase 7 — Polish and rehearsal (Day 4)
- [ ] Footer notice if any data is synthetic (rule R8)
- [ ] Test with 3 students at once in different browser windows
- [ ] Prepare the demo script below
- [ ] Rehearse `EVALUATOR_QA.md`

## Demo script (5 minutes)
1. (30 s) Problem and the two hard rules: stated vs inferred, duplicate names.
2. (60 s) Search "natural language processing for legal text": watch BM25 -> Vector -> RRF -> Cross-encoder light up in sequence.
3. (60 s) Open a result with a Stated expertise badge: show the faculty-authored passage and its source. Then open one "Inferred from publications" result: show the paper, the match mode, and the warning "not stated by the faculty member". Explain why the two are kept apart.
4. (45 s) Search a duplicate name: the picker appears; choose one; the right profile loads.
5. (45 s) Profile: links, free slots, generated email draft with a cited paper.
6. (45 s) Evaluation table: four configurations, hybrid + cross-encoder wins.
7. (30 s) Two students searching in parallel; mention privacy and consent.

## Risks and fallbacks
| Risk | Fallback |
|------|----------|
| API returns no publications for a faculty member | Use college bio and projects; label evidence STATED only |
| No timetable available | Show "Schedule not available"; email draft without slots |
| Cross-encoder too slow on a laptop | Reduce rerank pool to 15; precompute for demo queries |
| Wi-Fi fails | Cache API results in `data/processed`; run everything offline |
| Name merge errors | Keep `needs_review` list and show picker rather than merging |
