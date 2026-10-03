# WRITTEN_DISCUSSION.md — Why stated expertise and inferred similarity must be kept apart

> Draft. Replace every `[FILL]` with real numbers or examples from the evaluation run (`eval/results.md`, `eval/basis_report.md`). Do not invent results.

## 1. The two kinds of result

Our system returns two different kinds of claim about a faculty member.

- **Stated expertise.** The faculty member wrote it themselves in a consented profile field: research interests, bio, or a project description. The topic is named explicitly. The claim is theirs.
- **Inferred from publications.** The faculty member never declared the topic, but one of their publications is textually or semantically similar to the student's query. The claim is ours.

For each result we report which kind it is (`expertise_basis`: STATED, INFERRED or BOTH) and we keep the supporting evidence in two separate lists.

## 2. Why the distinction matters to someone relying on the result

**It tells the student whose judgment they are trusting.** A stated entry means the faculty member has represented this as their area. An inferred entry means a retrieval model thought a paper looked similar. Those are different levels of assurance, and a student choosing a supervisor or collaborator should know which one they are getting.

**Past work is not current interest or availability.** A publication may be years old, from a previous research direction, or from a project that has ended. A stated interest is more likely to reflect what the person is working on now. Treating papers as proof of current expertise can send students to people who have moved on.

**Authorship is not expertise.** Papers often have many authors. A faculty member may have been a minor co-author, a department head listed for supervision, or a contributor to a methods section. Similarity between the paper and the query says little about whether that person leads work on the topic.

**Similarity can be superficial.** Words and embeddings match surface language. A query on "graph neural networks" can pull a paper on graph-theoretic scheduling, or a query on "bias" can match a paper about statistical estimator bias. The retrieval score is a measure of text overlap, not a verified skill.

**Wrong expectations waste time on both sides.** A student who emails someone saying "I know you work on X" when that was only our inference creates an awkward exchange and may get no reply. Faculty receive misdirected messages. Honest labelling lets the student word the email correctly, for example "I read your paper on X and would like to ask about related topics."

**Misattribution can harm the faculty member.** Presenting someone as an expert in a field they never claimed can misrepresent them. Because profiles are used with consent, the consent covers what they wrote about themselves; it does not extend to us asserting new claims in their name.

**Fairness.** Faculty with many publications would otherwise look like experts in many topics, while newer or less prolific staff who state a clear focus would be buried. Separating the two kinds of evidence lets each be seen for what it is.

**It lets the user calibrate their own trust.** When results show a basis, evidence and match mode, the student can decide how much checking to do. A stated match with a cited bio line may need little. A semantic-only inferred match deserves a look at the paper first.

## 3. What our evaluation shows
 
Across the ten queries evaluated in `eval/basis_report.md` and `eval/results.md`:
 
- Across the ten queries we returned **54 results**: **28 STATED**, **9 INFERRED**, and **17 BOTH**.
- Precision@5 for **STATED-basis** results was **0.7368** (73.7%); for **INFERRED-basis** results it was **1.0000** (100.0%); and for **BOTH** it was **0.9412** (94.1%).
- **Example where an inferred result was correct and useful**: Query Q08 (`VLSI design signal processing`) retrieved `Mr. PAREPALLI NAGESWARA RAO` (F008) under `INFERRED` basis with publication evidence `F008-RAG [SEMANTIC]`. Although the faculty member had not populated explicit stated profile keywords for the query terms, his published work in VLSI design directly matched the student's need.
- **Example where an inferred result required caution**: Query Q02 (`cybersecurity and network security`) retrieved `Mrs. Ravula Divya` under `INFERRED` basis based on semantic similarity of an electrical monitoring abstract mentioning secure smart metering. While semantically related, she is not a core cryptography or IT security researcher; clear labelling prevented a student from assuming she teaches network security.
 
## 4. How the interface handles it
 
- Results are grouped under "Stated expertise", "Stated + Publications", and "Inferred from publications", with a distinct badge on every card.
- Stated and inferred evidence are shown as separate lists, each with a citation link.
- Inferred items show their match mode (LEXICAL or SEMANTIC) and score, and the card explicitly warns: *"Based on publication similarity — not stated by the faculty member."*
- Email drafts for inferred results refer to the paper ("I read your publication...") and do not make assertions about current teaching or stated expertise.
 
## 5. Related point: duplicate names
 
The same concern applies to identity. If two faculty share a name, merging their publications would turn one person's work into another's apparent expertise. Disambiguation (see `eval/disambiguation_report.md`) protects both the student and the faculty from that error. In `Q-DUP` (`Dr. P. Kumar`) we measured **0 merge errors** and **0 wrong-person leakage** with **100% option recall**, prompting the user with clear department and domain badges rather than guessing.

## 6. Limitations

- Faculty-authored profile text may be missing, outdated or very brief, so many correct experts will appear only as INFERRED.
- Our stated-match rule needs the topic to be named; synonyms outside the taxonomy may be missed.
- Publication coverage in open APIs is incomplete.
- Our relevance labels come from a small team and a small pool of faculty, so the numbers show direction rather than statistical proof.
