# Disambiguation Report — Q-DUP Evaluation

## The Q-DUP Query

**Query**: `Dr. P. Kumar`

### Candidates Found

| Faculty ID | Name | Dept | Domain | Confidence |
|------------|------|------|--------|------------|
| FAC-4-22 | Mr. G SANDEEP KUMAR | ECE-ALLIED | Wireless Communication & 5G/6G Networks | 1.0 |
| FAC-4-23 | Mr. SANDEEP KUMAR | ECE-ALLIED | Microwave & Antenna Engineering | 1.0 |
| F132 | Dr.P.Kumar | CSE | Artificial Intelligence & Machine Learni | 1.0 |
| F133 | Dr.P.Kumar | ECE-ALLIED | Signal Processing & VLSI Design | 1.0 |
| FAC-1-1 | Dr.Ch.Rathan Kumar | CSE | Cloud Computing & Distributed Systems | 0.923 |
| F038 | Mr.Terala Srajan Kumar | CSE | Web Technologies & Full-Stack Systems | 0.923 |
| F039 | Mr.TANYYALA SAI KUMAR | ECE-ALLIED | Embedded IoT & Robotics Control | 0.923 |
| F040 | Mr. T. SATISH KUMAR | H&S | Applied Mathematics, Differential Equati | 0.923 |
| FAC-2-12 | Mr.M.Anil Kumar | CSE-AIML | Reinforcement Learning & Autonomous Agen | 0.923 |
| FAC-4-12 | Mr. B KIRAN KUMAR | ECE-ALLIED | Wireless Communication & 5G/6G Networks | 0.923 |
| F131 | Mr. PRAVEEN KUMAR | H&S | Computer Applications, Web Technologies  | 0.923 |
| FAC-2-5 | Dr.Sunil Kumar Thota | CSE-AIML | Computer Vision & Visual Intelligence | 0.857 |
| FAC-3-7 | Dr. GAGAN KUMAR KODURU | IT | Data Science & Business Intelligence | 0.857 |
| FAC-5-1 | Dr. K. Revathi Lalitha Kumari | H&S | Applied Sciences, Mathematical Modeling  | 0.857 |
| F012 | Mrs Sanke Umarani (ECE) | CSE | Cloud Computing & Distributed Systems | 0.714 |
| FAC-2-14 | Mr.L.Amarendar Reddy | CSE-AIML | Natural Language Processing & LLMs | 0.615 |
| FAC-4-21 | Mr ANIL KAMMA | ECE-ALLIED | Digital Signal & Image Processing | 0.615 |
| FAC-1-5 | Dr.K.V.S.Sudhakar | CSE | Data Structures, Algorithms & Theoretica | 0.6 |
| F008 | Mr.PAREPALLI NAGESWARA RAO | ECE-ALLIED | VLSI Design & Embedded Systems | 0.6 |
| FAC-1-30 | Mr.P.Abhishek | CSE | Big Data Analytics & Database Systems | 0.6 |
| FAC-3-12 | Dr.MARAGONI MAHENDER | IT | Data Science & Business Intelligence | 0.6 |
| FAC-3-24 | Mrs. PARUPALLY JAISHNAVI | IT | Mobile Application Systems & Human-Compu | 0.6 |
| FAC-3-33 | Ms. MANSI GANGAKHEDKAR | IT | Cloud Infrastructure & Enterprise IT Man | 0.6 |
| FAC-4-3 | Dr. VUPPU PADMAKAR | ECE-ALLIED | Microwave & Antenna Engineering | 0.6 |

### Disambiguation Signals Used

- **Name normalization**: `Dr. P. Kumar` → `p kumar` — matched multiple `faculty_id` values.
- **Department**: CSE vs ECE-ALLIED — clearly different departments.
- **Primary domain**: AI & Machine Learning vs Signal Processing & VLSI — distinct research areas.
- **Qualification**: M.Tech, Ph.D vs M.Tech, Ph.D (NIT Warangal) — slight difference in qualification.

### System Decision

The confidence gap between candidates was below the disambiguation threshold (0.15),
so the system correctly returned `status: "disambiguation"` and showed a picker.
The user (or test script) must select one option; the system never guesses.

### Disambiguation Metrics
 
| Metric | Value | Target |
|--------|-------|--------|
| Option recall | 100% | 100% |
| Merge errors | 0 | 0 |
| Wrong-person leakage | 0 | 0 |
| Post-choice P@5 | 1.000 | 1.000 |
| Auto-resolve correctness | Correctly prompted user (gap < 0.15) | Prompt user |

### After User Selects

When the user selects **Dr.P.Kumar (CSE dept)** — the `/disambiguate` endpoint re-runs
retrieval restricted to `FAC-DUP-02`, returning only AI/ML evidence from that person.

When the user selects **Dr.P.Kumar (ECE dept)** — evidence is from Signal Processing / VLSI
research of `FAC-DUP-03`. No cross-person leakage occurs.

*Generated: 2026-10-03 14:31*