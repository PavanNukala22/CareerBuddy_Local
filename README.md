# Career Buddy LMS

A Django-based **Learning Management System for Business / Professional English**, combined with an **AI-powered career and hiring platform**. It serves two kinds of users through separate portals:

- **Students** — learn business English through interactive activities, live AI-driven speaking workshops (Group Discussion, JAM, Roleplay), a grammar module, Skill-Up assessments with certificates, and an AI resume builder with proctored mock interviews.
- **Employers** — post jobs, search candidate resumes, and track applicants.

The platform uses **Sarvam AI** for conversational agents, speech-to-text and resume analysis, **Django Channels** (WebSockets) for real-time workshops, and **Razorpay** for paid subscription plans.

---

## Features

| Module | Description |
|--------|-------------|
| **Activities / LMS** | Structured learning path `Activity → SubActivity → Exercise → Question` with progress tracking and multiple exercise types (MCQ, fill-in-the-blank, matching, ...). |
| **Group Discussion (GD)** | Real-time group discussion practice with AI participants over WebSockets. |
| **JAM (Just A Minute)** | Timed solo speaking practice with AI feedback. |
| **Roleplay** | Scenario-based conversational practice (mobile responsive). |
| **Grammar Module** | Grammar lessons with slides, video and illustrations served under `/subject/`. |
| **Skill-Up Assessments** | Assessments under `/skill-up/` that issue certificates on completion. |
| **Resume Builder** | Upload a PDF/DOCX resume, get an ATS score, skills analysis and job matching. |
| **AI Mock Interview** | Proctored, camera-mandatory interview with a 30-second answer timer, live speech-to-text answers, per-question AI scoring and a final analytics report (see [Interview module](#interview-module)). |
| **Career / Job Matching** | Recommends jobs from the database ranked by skill overlap and experience level. |
| **Employer Portal** | Post and manage jobs, view applicants, search candidate resumes ranked by relevance. |
| **Riya Chatbot** | Voice-enabled AI assistant (Sarvam STT/TTS) that guides students across the platform. |
| **Subscription Plans** | Free / Normal / Pro plans via Razorpay, with email OTP, server-side payment webhook and GST tax invoices. |

---

## Tech Stack

- **Backend:** Django 5.2, Django Channels 4 + Daphne (ASGI / WebSockets)
- **Database:** MySQL 8 via `mysqlclient` (MySQL only — SQLite is deliberately rejected by `settings.py`)
- **AI:** Sarvam AI API (agents, STT/TTS, resume analysis); LanguageTool API for grammar checks
- **Payments:** Razorpay (orders, signature verification, webhook, invoices via `reportlab`)
- **Resume parsing:** `pypdf`, `PyPDF2`, `pdfplumber`, `python-docx`
- **Frontend:** Django templates, Bootstrap 5, Tailwind CSS 3 (built with `npm run build:css`), Font Awesome, vanilla JS
- **In-browser ML:** `face-api.js` (tiny face detector) for interview proctoring
- **Testing:** Playwright (`testing/automation`), custom latency/load scripts (`performance-testing/`)
- **Config:** `python-decouple` (`.env`)

---

## Project Structure

```
business_english_lms/   # Project config (settings, urls, asgi, wsgi)
core/                   # Shared models (Resume, JobDescription), protected media serving, resume utils
activities/             # LMS activities, exercises, progress, Roleplay module
users/                  # Student auth, profiles, subscription plans
GD_app/                 # Group Discussion workshop (WebSockets + AI agents)
jam_app/                # JAM speaking workshop
career_app/             # Resume builder, ATS analysis, mock interview, payments (Razorpay)
skillup_assessment/     # Skill-Up assessments and certificates
jobs_app/               # Employer job postings, applications, candidate search
accounts_app/           # Employer authentication
employer_portal/        # Employer portal URL routing
riya_bot/               # Riya AI chatbot assistant
ResumeBuilder_module/   # Standalone resume-builder core logic (see its integration_guide.md)
subject_views.py        # Grammar lessons module
templates/              # HTML templates
static/                 # Source CSS / JS / images (Tailwind source in static/css/)
data/                   # Interview question bank (CSV)
testing/                # QA: Playwright automation, defects, reports, screenshots
performance-testing/    # Latency / load measurement scripts
media/                  # User uploads — resumes, selfies, interview videos (not in git)
logs/                   # Application logs (errors.log, payments.log — not in git)
```

---

## Getting Started

### Prerequisites
- Python 3.12 (3.11+ should work)
- MySQL 8 running locally
- Node.js (only needed to rebuild Tailwind CSS or run Playwright tests)
- A Sarvam AI API key (for all AI features)
- Razorpay test keys (for the subscription flow)

### 1. Clone & create a virtual environment
```bash
git clone https://github.com/srinivas1543/Career_Buddy_LMS.git
cd Career_Buddy_LMS

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
npm install            # optional: Tailwind build + Playwright
```

### 3. Configure environment variables
```bash
copy .env.example .env      # Windows
cp .env.example .env        # macOS / Linux
```

`.env.example` documents every setting. The essentials:

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY`, `DEBUG` | Django basics |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | MySQL connection |
| `SARVAM_API_KEY`, `SARVAM_MODEL` | Sarvam AI |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` | Payments |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL` | SMTP for OTP / notifications (ZeptoMail walkthrough in `.env.example`) |
| `GST_RATE`, `COMPANY_*` | Seller details printed on GST invoices |
| `CACHE_URL` | Shared cache (e.g. Redis) — required for multi-process deployments |
| `LANGUAGETOOL_API_URL` | Grammar-check endpoint |

> Never commit `.env` — it is git-ignored. Keep `.env.example` as the shared template.
>
> If you run more than one checkout of this project on the same machine, give each its own `DB_NAME`. Two checkouts sharing one database will apply each other's migrations and break each other's inserts.

### 4. Create the database
```sql
CREATE DATABASE business_english_lms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. Migrate, seed and create an admin
```bash
python manage.py migrate
python manage.py populate_activities      # LMS activities & exercises
python manage.py seed_jobs                # sample job postings for matching
python manage.py seed_resumes             # sample candidate resumes for search
python manage.py import_question_bank     # interview question bank from data/
python manage.py createsuperuser
```

### 6. Run the server
```bash
python manage.py runserver
```
Visit **http://127.0.0.1:8000/** (admin at `/admin/`).

> On Windows, `setup.bat` automates database creation, `.env` generation, migrations, activity seeding and superuser creation.

### Rebuilding CSS
```bash
npm run build:css     # static/css/tailwind.src.css → static/css/tailwind.build.css
```

---

## Key URLs

| Path | Description |
|------|-------------|
| `/` | Home / landing page |
| `/dashboard/` | Student dashboard |
| `/activities/` | Learning activities |
| `/roleplay/` | Roleplay workshop |
| `/skill-up/` | Skill-Up hub and assessments |
| `/subject/` | Grammar module |
| `/gd/` | Group Discussion workshop |
| `/jam/` | JAM speaking workshop |
| `/resume-builder/` | Resume builder, job match & AI interview |
| `/pro/` | Subscription plans & Razorpay checkout |
| `/employer-home/`, `/employer/` | Employer portal |
| `/admin/` | Django admin (includes read-only interview session / malpractice review) |

---

## Interview Module

The AI mock interview (`/resume-builder/start-interview/`) is proctored. Behaviour worth knowing when developing or testing it:

- **Camera is mandatory.** The interview cannot start until the browser grants camera access and a live preview is verified. This is enforced server-side (`camera_verified_at` on the session) — the question and answer endpoints reject requests without it. Camera loss mid-interview pauses the interview until it is reconnected.
- **30-second answer timer.** Each question's deadline is anchored server-side (`ResumeQuestion.presented_at`); when it expires the current answer (spoken or typed) is auto-submitted and the next question loads. Refreshing the page does not reset the clock.
- **Scoring.** Each question is scored 0–5 by Sarvam AI; the final score is scaled to 0–100 and the interview passes at **≥ 70**.
- **Recording.** The whole interview (video + audio, capped at ~400 kbps / 15 fps) is recorded in the browser and uploaded on completion. It is **kept only if the final score is ≥ 70**; below that it is discarded and never written to disk. Kept recordings are stored under `interview_videos/session_<hash>.webm` in the MinIO bucket when `MINIO_ENDPOINT_URL` is set (local `media/` otherwise) and are served via `core/media_views.py` only to the owning candidate and to employers that candidate has applied to (shown on the employer's application-detail page).
- **Anti-malpractice.** Face-not-detected, multiple faces, tab switch, window blur and camera interruption are logged per session (`InterviewViolation`) with a server-side counter that survives refreshes. Escalation: warnings for the first two violations, **flagged for review** at 3, **terminated** (auto-scored on answers so far) at 5. Thresholds are constants in `career_app/views.py`.

---

## Management Commands

| Command | Purpose |
|---------|---------|
| `populate_activities` | Populate LMS activities and exercises |
| `setup_professional_modules` | Set up professional learning modules |
| `seed_jobs` / `seed_it_jobs` | Create sample job postings used by career matching |
| `seed_resumes` | Generate sample candidate resume PDFs (`--clear` to reset) |
| `seed_candidates` | Create sample candidate accounts |
| `import_question_bank` / `import_interview_questions` | Load the interview question bank from `data/` |
| `seed_process_questions` | Seed process-oriented interview questions |
| `backfill_resume_text` / `cleanup_resumes` | Maintenance for stored resumes |
| `index_skillup` | Index Skill-Up content for the Riya chatbot |
| `send_test_email` | Verify SMTP configuration |

---

## Testing

- **Automation (Playwright):** scripts in `testing/automation` and `testing/automation_scripts`; defects, reports and screenshots are kept alongside them. See `testing/README.md`.
- **Performance:** latency/load scripts in `performance-testing/` (`node performance-testing/measure.js`, `python performance-testing/query_profile.py`).
- **Django checks:** `python manage.py check` and `python manage.py makemigrations --check`.

---

## Deployment Notes

- Set `DEBUG=False` and configure `ALLOWED_HOSTS`.
- Run `python manage.py collectstatic`; serve `staticfiles/` via your web server. Serve `/media/` **through Django** for `resumes/`, `selfies/` and `interview_videos/` — those paths are access-controlled in `core/media_views.py` and must not be exposed as plain static files.
- Interview recordings go to MinIO: run it on the same host, bound to loopback only, and set `MINIO_ENDPOINT_URL=http://127.0.0.1:9000` plus `MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY`/`MINIO_BUCKET` in `.env` (see `.env.example`). Keep the bucket private — Django streams the file after its own access check. To move recordings that already exist on disk into the bucket, run `python manage.py migrate_interview_videos` (add `--delete-local` once verified).
- `media/` must live on a persistent disk (candidate search reads resume PDFs from it; interview recordings are stored there).
- Use an ASGI server (Daphne) so the WebSocket workshops work.
- Set `CACHE_URL` to a shared backend (Redis) when running multiple workers — OTP codes and rate limits live in the cache.
- Register the Razorpay webhook at `https://<domain>/pro/webhook/razorpay/` (event `payment.captured`) and set `RAZORPAY_WEBHOOK_SECRET`.
- Rotate all secrets (`SECRET_KEY`, API keys, email token) before going live.

---

## License

This project is provided as-is for educational and demonstration purposes.
