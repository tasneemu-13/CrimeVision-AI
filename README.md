# CrimeVision AI — Intelligent Multimodal Forensic Analysis Platform

> **v2.0 Production Forensic OS**  
> An auditable, court-ready digital forensics intelligence platform integrating deep vision object detection, speech-to-text transcript timelines, CCTV trajectory tracking, cross-modal evidence fusion, and cryptographic chain of custody.

---

## 🏛️ Platform Architecture

CrimeVision AI is architected with strict separation of concerns, multi-tenant case isolation, and persistent storage:

```
crimevision/
├── app.py                      # Application router & session state coordinator
├── requirements.txt            # Python dependencies (SQLAlchemy, bcrypt, OpenCV, etc.)
├── .env.example                # Template for environment configuration
├── database/
│   ├── connection.py           # SQLite connection, WAL mode & session manager
│   ├── models.py               # SQLAlchemy ORM models (Users, Cases, Evidence, etc.)
│   └── db_service.py           # User-isolated transactional CRUD operations
├── auth/
│   ├── security.py             # Salted bcrypt/PBKDF2 hashing, strength meter & validators
│   └── session.py              # Persistent token management & query_param synchronization
├── ai_services/
│   ├── providers.py            # Transparent Groq & Gemini client with explicit status
│   ├── vision.py               # Scene entity detection, threat scoring & leads
│   ├── audio.py                # Whisper ASR transcription & penal event tagging
│   ├── video.py                # OpenCV frame sampling, motion diff & trajectory tracker
│   └── fusion.py               # Multimodal cross-corroboration & grounded Q&A engine
├── reporting/
│   └── pdf_generator.py        # ReportLab court-ready forensic PDF export with custody table
├── ui/
│   ├── styles.py               # Forensic dark design system (Graphite, Deep Navy, Teal/Cyan)
│   ├── components.py           # Reusable metric cards, threat badges & status pills
│   ├── landing.py              # Modern public platform landing page
│   ├── auth_pages.py           # Sign In, Sign Up, Strength Meter & Password Recovery
│   ├── dashboard.py            # Case overview, live metrics, search/filter & create case
│   └── case_workspace.py       # Scoped workspace hosting the 6 forensic modules
├── data/                       # Persistent data vault (auto-created)
│   ├── crimevision.db          # SQLite relational database
│   ├── uploads/                # Ingested evidence files (permanent storage)
│   └── reports/                # Generated court-ready PDF documents
└── tests/
    ├── conftest.py             # Test database fixture
    ├── test_auth.py            # Password hashing, validation, session token tests
    ├── test_db_isolation.py    # Multi-user isolation & authorization boundary tests
    ├── test_forensics.py       # Evidence ingestion, hashing, ledger fusion tests
    └── test_pdf_export.py      # PDF report generation & checksum verification tests
```

---

## 🔑 Core Features & Enhancements

### 1. Robust Authentication & Session Persistence
- **Secure Password Hashing:** Salted passwords using `bcrypt` (with fallback to `PBKDF2-HMAC-SHA256`). Plaintext passwords are never stored.
- **Dynamic Password Strength Meter:** Real-time feedback checking length (>=8), uppercase, lowercase, numbers, and special symbols.
- **Persistent Sessions Across Browser Refresh:** Cryptographic 256-bit session tokens stored in the database and synchronized with URL parameters. Refreshing the browser (`F5`), switching tabs, or restarting the backend keeps the investigator logged in without data loss.
- **Password Recovery:** Built-in password reset workflow verified by investigator credentials.

### 2. Multi-User Case Isolation & Authorization
- **Strict Query-Level Isolation:** Every database operation verifies that the requested case, evidence file, or audit record belongs to the authenticated investigator.
- **Zero Cross-User Leakage:** One investigator cannot view, edit, or delete another investigator's cases, even if they guess the Case ID.
- **Tamper-Evident SHA-256 Vault:** Uploaded evidence files are permanently saved to `data/uploads/{case_id}/` and indexed with their cryptographic SHA-256 digests.

### 3. Forensic Operations Dashboard
- **Calculated Real-Time Metrics:**
  - Total Cases stored in persistent vault.
  - Active Investigations (Open / In Progress).
  - Total Evidence Ingested.
  - Total Court Reports Generated.
- **Investigation Case Management:**
  - Search by Title, Case ID, Location, or Category.
  - Filter by Status (Open, In Progress, Under Review, Closed).
  - Sort by Newest, Oldest, or Title.
  - Prominent **Create New Case** action.
  - Optional **Initialize Forensic Benchmark Case** button for one-click demonstration.
- **Live Forensic Audit Trail:** Chronological log of recent custody transactions across all user cases.

### 4. Six Integrated Forensic Modules
1. **📷 Scene Tagger:** Detects 5 forensic classes (`person`, `firearm`, `edged_weapon`, `blood_spatter`, `forced_entry`), assigns threat levels (Low → Critical), classifies scenes, draws bounding boxes, and generates prioritized investigative leads.
2. **🎙 Witness Audio:** Transcribes emergency dispatches and witness audio, tags speakers, and extracts penal-code keywords onto a chronological timeline.
3. **🎥 CCTV Analysis:** Extracts video frames via OpenCV, computes frame-differencing motion intensity profiles, maps suspect trajectory, and categorizes chronological progression events.
4. **🧠 Multimodal Fusion & Chat:** Unifies visual, auditory, and surveillance data into a master cross-modal ledger. Answers investigator questions by citing exact evidence IDs (e.g. `[IMG-001.D1]`) and refuses speculation when facts are missing. Chat history is saved per case in the database.
5. **📄 PDF Report Export:** Compiles official ReportLab court-ready forensic reports with case metadata, annotated scene plates, verbatim transcripts, CCTV trajectory summaries, master ledgers, and investigator certification blocks.
6. **🧾 Chain of Custody:** Full chronological audit ledger recording evidence intake, transfers, timestamps (UTC), and SHA-256 checksums with CSV export and manual custodial transfer logging.

### 5. Transparent & Honest AI Processing
- Unlike prototypes that fake AI analysis, CrimeVision AI explicitly indicates whether it is operating with a live cloud model (`Groq Llama-Scout Vision` / `Gemini 2.0 Flash` / `Whisper ASR`) or running deterministic local forensic baselines (`RT-DETR Local Baseline`, `OpenCV Frame Diff Tracker`).
- If an API key is missing or fails, clear actionable guidance is provided rather than fabricated claims.

### 6. Premium Forensic Intelligence UI
- Styled in deep graphite (`#0b0f14`), obsidian navy (`#101723`), and dark slate card surfaces (`#141f2d`).
- Restrained forensic teal (`#00e5a8`) and precision cyan (`#0ea5e9`) accents.
- Structured tables, clean data density, crisp monospace badges, and high-contrast typography without distracting neon glows.

---

## 🚀 Quickstart & Installation

### Prerequisites
- Python 3.9+ (Python 3.11 recommended)
- `pip` package manager

### 1. Clone & Install Dependencies
```bash
cd crimevision
pip install -r requirements.txt
```

### 2. Environment Configuration (Optional)
Copy the example environment configuration:
```bash
cp .env.example .env
```
To enable live multimodal vision and Whisper transcription, add your API key:
```env
GROQ_API_KEY=your_groq_api_key_here
# or
GEMINI_API_KEY=your_gemini_api_key_here
```
*(If left empty, CrimeVision AI seamlessly runs high-fidelity local deterministic forensic baselines).*

### 3. Launch the Application
```bash
streamlit run app.py
```
Open your browser to `http://localhost:8501`.

---

## 🧪 Automated Testing

CrimeVision AI includes a comprehensive test suite covering authentication, multi-user isolation, evidence integrity, multimodal fusion, and PDF report generation:

```bash
pytest tests/ -v
```

### Test Coverage Highlights:
- `test_auth.py`: Password hashing & verification, email regex validation, password strength scoring, session token issuance & invalidation.
- `test_db_isolation.py`: Verifies that User A's cases and evidence are strictly invisible and inaccessible to User B.
- `test_forensics.py`: Tests scene object detection, audio event tagging, CCTV frame tracking, ledger extraction, and grounded evidence Q&A.
- `test_pdf_export.py`: Validates ReportLab PDF generation, binary integrity (`%PDF`), and SHA-256 checksum calculation.

---

## 📜 Statutory Notice
All automated forensic detections, audio transcriptions, and suspect tracking outputs generated by CrimeVision AI are intended for investigative triage. Formal judicial presentation requires corroboration by a certified digital forensics examiner.
