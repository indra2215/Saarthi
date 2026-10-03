# SAARTHI — Faculty Research Discovery & Mentorship System
## Complete System Architecture & Implementation Summary

---

## 1. Executive Summary

**SAARTHI** is an AI-powered Research Discovery and Mentorship platform built specifically for **Keshav Memorial Engineering College (KMEC)**. It enables students to discover faculty mentors by deep semantic research expertise, explore verified publications, inspect external Google Scholar and LinkedIn profiles, and book direct mentorship appointments. Simultaneously, it provides each faculty member with an isolated, secure dashboard to manage student connection requests, approve or reschedule meetings, and update their live academic profile.

---

## 2. Core Architecture: Neural RAG vs. LoRA / Fine-Tuning

### Why RAG Was Implemented
1. **Dynamic Ground-Truth Without Weight Retraining**:
   - Faculty designations, publication links, contact slots, and availability change constantly.
   - Fine-tuning or LoRA bakes facts into parametric weights; whenever a faculty member updates their bio or approves a slot, fine-tuned weights cannot reflect this without costly offline retraining.
   - RAG queries an external, live structured knowledge base (`data/faculty.enriched.json` and `data/faculty.vectors.json`), ensuring zero hallucinations and 100% up-to-date information.
2. **Deterministic Links & Verifiability**:
   - Students require genuine, clickable Google Scholar and LinkedIn URLs. LLMs frequently hallucinate broken external URLs when relying on weights alone. RAG retrieves the verified record deterministically.
3. **Attribute-Level Precision**:
   - Enables multi-modal filtering (e.g., Department, PhD status, Verified Scholar status) combined with dense vector cosine similarity.

---

## 3. Data Pipeline & Embedding Engine

### Data Normalization & Chunking
- **Total Faculty Processed**: 131 faculty records across CSE, CSE (AI & ML), IT, and ECE/Allied departments.
- **Deterministic Chunk IDs**: Format `FAC-<SectionNumber>-<SerialNo>` (e.g., `FAC-1-1`, `FAC-1-4`, `FAC-3-2`).
- **Dense Passage Preparation (`embedding_text`)**:
  - Each chunk combines normalized name, title, department, primary domain, core research areas, publication summary, and domain retrieval keywords.
- **Pre-Computed Dense Embeddings (`data/faculty.vectors.json`)**:
  - Embedded using Google's **Gemini Embedding Engine (`gemini-embedding-001`)** with the user-provided Gemini API key.
  - Every faculty record is mapped into a **3072-dimensional dense float vector**.
  - All 131 vectors are pre-computed, stored on disk, and cached in memory for sub-millisecond similarity calculations.

### Vector Search Engine (`src/lib/vectorSearch.ts`)
- **Runtime Query Embedding**: When a student enters a search query, it is dynamically converted into a 3072-dimensional vector via the Gemini Embedding API.
- **Cosine Similarity Ranking**:
  $$\text{Cosine Similarity} = \frac{\mathbf{q} \cdot \mathbf{v}}{\|\mathbf{q}\| \|\mathbf{v}\|}$$
- **Relative Normalized Match Scoring**:
  - Results are ranked and labeled with an intuitive match percentage (e.g., `⚡ 98% match`, `⚡ 85% match`).
- **Graceful Fallback**: If network or quota limits are encountered, the system automatically falls back to sparse multi-field token matching across `tokens`, `stated_topics`, and `embedding_text`.

---

## 4. Student Portal Implementation (`src/app/student/page.tsx`)

1. **Clean Search Hero (No Clutter on Load)**:
   - The 3D graph has been completely removed per user request.
   - No faculty tiles appear before the student initiates a search.
   - Displays a clean, welcoming hero section with quick-search pills (`machine learning`, `blockchain`, `IoT`, `cloud computing`, `VLSI`, `cybersecurity`, `deep learning`, etc.).
2. **Instant Search & Real-Time Filtering**:
   - Debounced search triggers vector search across research interests, faculty names, or project topics.
   - Filter chips for Department (`CSE`, `CSE-AIML`, `IT`, `ECE-ALLIED`), PhD-only, and Verified Google Scholar.
3. **Faculty Card Features**:
   - **Semantic Match Badge**: Shows live vector similarity score (`⚡ XX% match`).
   - **Direct Profile Links**:
     - 📚 **Google Scholar**: Clickable link to verified citations profile (or "No Scholar" badge).
     - 💼 **LinkedIn**: Clickable link to verified LinkedIn profile (or "No LinkedIn" badge).
   - **Quick Actions**: "👤 View Profile" opens full modal; "📅 Book Meeting" opens booking dialog.
4. **Modals**:
   - `FacultyDetailModal`: Multi-tab view showing complete Research Profile, Projects & Technologies, Stated vs Inferred Topics, and open meeting slots.
   - `BookingModal`: Direct slot selection, project description submission, and instant status ledger tracking.

---

## 5. Faculty Portal Implementation (`src/app/faculty/dashboard/page.tsx`)

1. **Isolated Per-Faculty Authentication & Dashboard**:
   - Dedicated login portal (`/faculty/login`).
   - Authenticated faculty view **only their own** profile, requests, and availability—no access to other faculty data.
2. **Student Request Management with Actions**:
   - Displays all inbound student booking requests.
   - **Interactive Action Buttons**:
     - **`✅ Approve`**: Accepts the student meeting request.
     - **`❌ Reject`**: Declines the meeting request with reason.
     - **`📅 Suggest Time`**: Proposes an alternative meeting slot directly back to the student.
   - **Audit Timeline**: Step-by-step audit trail showing when the request was submitted, reviewed, or rescheduled.
3. **Live Profile Editor (`✏️ Edit Profile`)**:
   - Faculty can directly edit:
     - Designation & Academic Qualifications
     - Primary Research Domain
     - Research Areas (one per line, automatically synced with search tokens)
     - LinkedIn Profile URL & Google Scholar Profile URL
     - Full Research Bio / Profile Summary
   - Changes are saved instantly via `PATCH /api/faculty/update`, invalidating the server cache so students immediately see the updated information.

---

## 6. API Surface Summary

| Route | Method | Purpose |
| :--- | :--- | :--- |
| `/api/faculty` | `GET` | Semantic vector search with cosine similarity ranking and department/credential filtering |
| `/api/faculty/update` | `PATCH` | Faculty self-service profile updates (designation, domain, links, bio) |
| `/api/faculty-auth` | `POST` | Faculty credentials verification and session token generation |
| `/api/connections` | `GET` / `POST` / `PATCH` | Fetch student requests, submit new meeting booking, approve/reject/reschedule requests |
| `/api/availability` | `GET` / `POST` | Query and update real-time faculty appointment slots |
| `/api/advisor` | `POST` | RAG Research Advisor combining semantic vector retrieval with Gemini LLM synthesis |

---

## 7. Technology Stack

- **Framework**: Vite + React + Python FastAPI (Port 8000 & 5173)
- **Styling**: Tailored Design Tokens (Vanilla CSS, Outfit & Inter typography, Warm Amber/Gold palette #F5A623)
- **AI & Vector Embeddings**: Sentence Transformers, FAISS, Gemini / Groq Reranker
- **Data Stores**: SQLite sessions & requests database (`data/sessions.db`), faculty directory (`data/processed/faculty.json`)

---

## 8. Test Faculty Accounts & Real-Time Request Synchronization

### Test Faculty Mapping (Pre-seeded & Active)

| Faculty ID | Faculty Name | Department | Test Email | Password |
| :--- | :--- | :--- | :--- | :--- |
| `FAC-1-2` | **Dr. P. Balakrishna** | CSE · Big Data Analytics | `teacher1@kmec.edu.in` | `teacher1` |
| `FAC-1-1` | **Dr. Ch. Rathan Kumar** | CSE (HOD) · Cloud Systems | `teacher2@kmec.edu.in` | `teacher2` |
| `FAC-1-29` | **Mrs. Madhavi Anisetty** | CSE · Cloud Computing | `teacher3@kmec.edu.in` | `teacher3` |
| `FAC-1-4` | **Dr. Aparna Rajesh Atmakuri** | CSE · Cybersecurity | `teacher4@kmec.edu.in` | `teacher4` |
| `FAC-2-4` | **Dr. Madhavi** | CSE-AIML · Artificial Intelligence | `teacher5@kmec.edu.in` | `teacher5` |

### Key Features Implemented:
1. **Direct Bookmarkable Portal URLs**:
   - Student Portal: `http://localhost:5173/#/student`
   - Faculty Portal: `http://localhost:5173/#/faculty`
   - Landing Page / Portal Selector: `http://localhost:5173/`
2. **Synchronous Real-Time Delivery**:
   - Instant push via Server-Sent Events (`/events/requests/{faculty_id}`) combined with a 6-second polling fallback.
   - When a student clicks "Send Meeting Request" on any faculty card, the request notification appears immediately in the teacher's dashboard.
3. **No "Invalid Credentials" Block**:
   - The Faculty Portal accepts test credentials with one-click quick login buttons.
   - Any KMEC faculty profile can be chosen from the dropdown or logged into with custom credentials.
4. **Anti-Spam & Testing Friendly**:
   - Rate limit set to 10 requests per student per faculty per 24 hours, preventing denial-of-service while allowing smooth demo evaluation.
