# EVALUATOR_QA.md — Likely questions and short answers

## Retrieval and RAG

**Why hybrid and not just vector search?**
Vector search finds meaning but can miss exact names and acronyms. BM25 finds exact terms but misses synonyms. Hybrid covers both. We measured it: the table in `eval/results.md` shows the gain.

**What is BM25?**
A keyword scoring method. It rewards passages that contain the query words often, favours rare words over common ones, and corrects for passage length.

**What is RRF and why use it?**
Reciprocal Rank Fusion merges ranked lists using only ranks: each list gives a document `1 / (60 + rank)`, and we sum them. It needs no score normalization, so BM25 and cosine scores (different scales) can be combined safely.

**Why add a cross-encoder?**
BM25 and vector search compare the query and passage separately. A cross-encoder reads them together, so it orders the top results more accurately. It is slow, so we only run it on the top 30.

**Why not run the cross-encoder on everything?**
Cost and latency. Cheap retrievers narrow the pool first; the expensive model refines it.

**Why chunk by passage, and how big?**
Passages give precise citations. We use about 150-250 tokens with a small overlap, with a metadata header on each chunk so it keeps its context.

**What does the metadata header do?**
It puts faculty name, ID, department, source and year in the text that is embedded and indexed, so both BM25 and vectors know whose passage it is.

**What is RAG in your system?**
Retrieval of evidence passages, ranked and cited. Generation is limited to the email draft, which is built from retrieved evidence.

## The two hard requirements

**How do you tell stated expertise from inferred similarity?**
Each chunk has a source type. Faculty-authored text (research interests, bio, project description) that explicitly names the topic gives STATED. A match resting only on publication text similarity, by keywords or embeddings, gives INFERRED. Both together give BOTH. Each result reports the two evidence lists separately, and the card says whether the faculty member claimed the topic or we inferred it from their papers.

**Why are publications treated as inference and not as stated expertise?**
A publication shows work was done, but the link between that work and the student's topic is our judgment. The faculty member never said "I am an expert in this." Treating papers as claims would present our inference as their statement.

**How do you handle duplicate names?**
Before chunking, entity resolution assigns a unique `faculty_id` using ORCID, email, department, qualification and publication overlap. Every chunk carries that ID, so people never mix. If a name query matches several IDs, the app shows a picker instead of guessing.

**What if two different people match with similar scores?**
We return a disambiguation response with each person's department and qualification and let the student choose.

**What if the resolution is wrong?**
Uncertain pairs go to a `needs_review` list and stay separate. We prefer showing a picker to wrongly merging two people.

**Why is disambiguation not done in the vector database?**
Embeddings place similar names close together and cannot separate people. Identity must be resolved with structured fields and IDs.

## Data, privacy and ethics

**Where does the data come from?**
The college database (names, qualifications, department, timetable), public publication APIs (OpenAlex, Semantic Scholar, Crossref, ORCID), and consented profile links.

**Do you scrape LinkedIn or Google Scholar?**
No. They prohibit it and the problem requires consented data. LinkedIn is stored as a link only; publications come from open APIs.

**How is consent handled?**
Each record has a consent flag. Records without consent are excluded from search and from display.

**Is any data synthetic?**
If so, the UI footer says so.

**How do you avoid bias toward people with many publications?**
Ranking is by passage relevance, aggregated by max of the top passages, not by publication count.

## Evaluation

**How did you evaluate?**
Ten topic queries, relevance labels from 0 to 3 by two people, and four configurations compared with Precision@5, Recall@10, MRR and nDCG@10.

**What does nDCG mean?**
It scores a ranked list by relevance, giving more credit to relevant items near the top, and normalizes against the ideal order.

**What does MRR mean?**
The average of 1 divided by the rank of the first relevant result.

**Why is your test set small?**
Labelling is manual and the faculty pool is limited. We report it honestly and show the ablation to show direction, not claim statistical proof.

**What are the limits of your system?**
Sparse profiles for faculty with few publications, publication API coverage, and a small labelled set.

## Product and interface

**Why is the dashboard slow on purpose?**
So evaluators can watch each stage (BM25, vector, RRF, cross-encoder) and see how rankings change. The real pipeline is fast; the trace stream adds a short delay for display.

**How do you support many students at once?**
Each session has an ID, queries go through a queue, and results are stored per session so students can leave and return.

**How are meeting times chosen?**
From the faculty timetable: working hours minus class periods, with a minimum gap length. If there is no timetable, we say so.

**How is the email drafted?**
A template using the student's name, topic, one cited paper and 2-3 free slots, delivered through a `mailto:` link. The student reviews and sends it.

**Can several faculty be contacted for the same topic?**
Yes. The graph groups faculty with the same topic, and every profile has its own contact options.

## Scale and future work

**How would this scale to thousands of faculty?**
Use an approximate-nearest-neighbour index, an Elasticsearch or OpenSearch keyword index, precomputed embeddings, and batch reranking.

**What would you add next?**
Feedback learning from student clicks, co-author graphs, multilingual queries, and automatic refresh of publications.

## Release addendum: critical topics in detail

**Which of your ten queries is the duplicate-name case, and what did the system do?**
`Q-DUP` is built on two faculty whose normalized names collide (for example two "R. Rao" in different departments). The query is deliberately ambiguous. Entity matching finds both IDs, the confidence gap is small, so the API returns a disambiguation response instead of ranking either person. The options show department, qualification and a one-line research summary. After the choice, retrieval is restricted to that `faculty_id`. We report option recall, merge errors and wrong-person leakage; the targets are 100%, 0 and 0, and `eval/disambiguation_report.md` shows the actual values.

**What signals separate the two same-name people?**
ORCID and email when available, department, qualification, publication overlap and co-authors, and the topic words in the query. Name similarity alone is never enough to merge (rule R9).

**What if the user does not choose, or the query already contains a department?**
With no choice, nothing is ranked. With a clearly separating department or topic, the system may auto-resolve, but it must say why, and we report auto-resolve correctness separately.

**What if the two people have no distinguishing data at all?**
They stay as separate IDs and both are offered. We would flag the pair `needs_review` for a human. We never guess.

**How do you report stated versus inferred for each result?**
Every result has `expertise_basis` (STATED, INFERRED or BOTH) and two separate evidence lists. `eval/basis_report.md` has one row per returned result for all ten queries, with per-query counts. We also compute Precision@5 separately for stated and inferred results.

**Why does the distinction matter to someone relying on the result?**
Short version: a stated claim is the faculty member's own representation of their expertise and interests; an inference is our guess from past papers. A student who treats a guess as a claim may contact the wrong person, build expectations the faculty member never created, or credit a person with expertise they only touched as a minor co-author. The full discussion is in `WRITTEN_DISCUSSION.md`.

**Could an inferred result still be useful?**
Yes. Papers are real, checkable evidence, and many inferred results are relevant. The point is honest labelling: the student sees the paper, sees that it is our inference, and can judge for themselves.

**Did inferred results perform worse than stated ones?**
Report the measured Precision@5 for each group. Do not claim a direction before you have the numbers.

## Tough questions (practise these)

- "Your cross-encoder only helps a little. Why keep it?" — Show the per-query numbers; it fixes the top-3 order, which matters most to students.
- "Isn't 'Stated expertise' just keyword matching?" — It requires faculty-authored text that names the topic, shown as a citation. Keyword or semantic overlap with a paper alone never earns that label; it is shown as inferred.
- "What if a faculty member objects to being listed?" — Consent flag; removal takes effect on the next index build.
- "Why not use an LLM to answer directly?" — It could invent expertise. We only show retrieved, cited evidence.
