CLAUDE.md — Beyond Portal Agent POC

This file is read automatically by Claude Code. Follow it exactly. Ask before
deviating from the schema, tech stack, or agent list defined here.

Update (2026-08-19): Secrets strategy changed — Azure Key Vault
(beyondportal) is now live and is the required source for all secrets.
This replaces the original .env-only plan in Section 3. See Section 3
for details.

Update (2026-08-19, later same day): Reversed again per Varun — for this
POC, secrets go back to .env (gitignored) instead of Key Vault. Key Vault
RBAC access was blocking local development, and the team decided the
POC doesn't need it. This supersedes the update above. See Section 3
for details.

1. Project Summary

A minimal POC demonstrating an agentic content portal for Lucy (Client
Executive persona). Lucy sees articles/videos, gets AI-assisted reading tools,
gets recommendations, and her engagement score updates live as she interacts
with content. Everything outside Lucy's flow is out of scope — do not build
communities, events, moderation, RM workspace, or CRM sync.

2. Tech Stack (do not substitute or add libraries beyond this list)
Layer	Choice
Frontend	React
Backend	FastAPI (Python 3.11+)
Database	Azure SQL Database (via SQLAlchemy + pyodbc)
File storage	Azure Blob Storage (2 containers: article-files, videos-files — corrected 2026-08-20, neither container is named "articles"/"videos")
AI	Azure AI Foundry — deployment gpt-5.4-mini, chat.completions API
Auth	SQL users table, hardcoded/plaintext credentials (POC only, flag as insecure)
Hosting	Azure App Service (backend), Azure Static Web App (frontend)
Secrets	.env (gitignored), loaded via python-dotenv. Key Vault reversed — see Section 3.

New approved dependency (2026-08-20): pypdf, for extracting body_text
from the real article PDFs during the content swap. Confirmed with the
user before adding, per this section's own rule.
3. Environment Variables & Secrets

Secrets live in .env (gitignored, never committed). This reverses the
Key Vault plan above — Key Vault access (RBAC) was blocking local dev, and
Varun confirmed the POC doesn't need it. Still never put secret values in
source files, config committed to git, or logs.

.env holds both the non-secret config and the secret values:

KEY_VAULT_URL — no longer used; safe to leave unset or remove
FOUNDRY_DEPLOYMENT_NAME
STORAGE_ARTICLES_CONTAINER — value is "article-files", not "articles" (corrected 2026-08-20)
STORAGE_VIDEOS_CONTAINER — value is "videos-files", not "videos" (corrected 2026-08-20)
SQL_CONNECTION_STRING — TEMPORARY (2026-08-20): Driver 18 was never
  actually installed on the dev machine (blocked on admin elevation all
  session); using Driver={SQL Server} (the legacy driver that is
  installed) instead, WITHOUT the Encrypt/TrustServerCertificate
  attributes — the legacy driver rejects those as invalid connection
  string attributes, and apparently negotiates TLS with Azure SQL fine
  without them. Verified working end-to-end through the real db.py/
  pyodbc path (not a substitute) and through a live uvicorn server.
  Revert to Driver 18 once it's properly installed for production —
  this stopgap is a real, if unintentional, deviation from Section 2's
  "SQLAlchemy + pyodbc" stack description (still pyodbc, just an older
  driver than intended).
SQL_ADMIN_USERNAME
SQL_ADMIN_PASSWORD
STORAGE_CONNECTION_STRING
FOUNDRY_ENDPOINT
FOUNDRY_API_KEY
FOUNDRY_TRANSCRIBE_DEPLOYMENT_NAME — optional, only for Section 6 #9 (Video
  Transcript & Summary); unset until Varun confirms a transcription model
  is actually deployed. config.py does not require this at startup.
FOUNDRY_LEGACY_API_VERSION — optional, same reason as above; the legacy
  Azure OpenAI api-version needed for the transcription call only.

backend/config.py loads all of the above from .env via python-dotenv and
exposes a single settings object — the rest of the codebase imports from
config.py and never reads os.environ or .env directly. No Key Vault or
DefaultAzureCredential code remains in config.py.

Resolved: there is no FOUNDRY_API_VERSION. The beyondportal-foundry
resource uses Azure OpenAI's v1 GA API surface
(https://beyondportal-foundry.services.ai.azure.com/openai/v1/), which
uses implicit versioning — no api-version parameter, and no
azure_endpoint/AzureOpenAI class either. foundry_client.py uses the plain
openai.OpenAI client with base_url=FOUNDRY_ENDPOINT and api_key=
FOUNDRY_API_KEY. Verified live against the gpt-5.4-mini deployment via
chat.completions.create() on 2026-08-19. The registry-path value Varun
originally sent was never a real api-version — that question doesn't
apply to this endpoint type.

4. Database Schema (already created — match exactly, do not alter)
users(user_id PK, name, username, password, persona, declared_interests, created_at)
content_items(content_id PK, type, title, body_text, blob_url, thumbnail_url, duration, topic_tags, published_at)
engagement_signal(signal_id PK, user_id FK, content_id FK, signal_type, depth_pct, occurred_at)
engagement_scores(user_id PK/FK, score, level, delta, last_updated)
recommendations(rec_id PK, user_id FK, content_id FK, rank, score, reason_code, status, generated_at)
signal_weight_config(signal_type PK, weight)

declared_interests and topic_tags are JSON-encoded string arrays. Keep a
single INTEREST_TO_TAG mapping dict in one place (e.g. constants.py); do
not duplicate it.

Real vocabulary (from Neha's tags.docx, 2026-08-20 — replaces the earlier
placeholder market/leadership domain):

declared_interests: Tax Transformation, International Tax, Transfer
Pricing, Cyber Security, Tax Technology, Compliance Advisory, ESG Tax &
Incentives, Mergers & Acquisitions, Digital Transformation, Regulatory
Reporting.

topic_tags: PILLAR_TWO, INTL_TAX, TAX_TRANSFORMATION, TRANSFER_PRICING,
CYBER_SECURITY, AI_TAX_OPS, COMPLIANCE_ADVISORY, ESG_TAX,
MERGERS_ACQUISITIONS, DIGITAL_TRANSFORMATION, REGULATORY_REPORTING.

Two mapping decisions in constants.INTEREST_TO_TAG worth recording:
PILLAR_TWO has no interest of its own, so it's folded into "International
Tax" (a full match, not just a partial one, for Pillar Two content);
"Tax Technology" maps to AI_TAX_OPS, the only tax-tech-shaped tag
tags.docx lists. Separately: the already-seeded c003 row carries a
literal "TAX_TECHNOLOGY" tag that isn't in tags.docx's 11-tag list at
all — harmless (it just never matches anything), worth dropping when
c003's real content is swapped in.

5. Coding Standards — Ponytail Ladder (mandatory for every change)

Before writing any code, work down this ladder and stop at the first rung
that resolves the need. Do not skip ahead to "write something custom" if an
earlier rung already solves it.

1. Does this need to exist at all?     -> no: skip it (YAGNI)
2. Already in this codebase?           -> reuse it, don't rewrite
3. Python stdlib does it?              -> use it
4. FastAPI/SQLAlchemy/React built-in?  -> use it
5. Already an installed dependency?    -> use it
6. Solvable in one line?               -> one line
7. Only then: write the minimum that actually works

This is about laziness in building, not in understanding the problem —
read the surrounding code and trace the real data flow before picking a rung.

Never cut, regardless of the ladder above:

Input validation at any trust boundary (user input, LLM output before DB
writes, request bodies)
Error handling for external calls (SQL, Blob, Foundry) — these must not
crash the API; return a clean error response
No secrets, connection strings, or API keys committed to source or logs

Also required:

Type hints on all function signatures
No premature abstraction — don't build a generic "agent base class" or
plugin framework for 8 functions; a plain function per agent is correct
at this scale
No new dependencies beyond what's in Section 2 without asking first
Prefer the rule-based dispatcher described in Section 7 over any
LLM-based routing — this was a deliberate architecture decision, not an
oversight

If Claude Code has the ponytail plugin installed, it will enforce this
automatically — this section exists so the same standard holds even without
the plugin active.

6. Agent Specifications

Each agent is a plain Python function + one FastAPI route. No agent
framework, no orchestrator class hierarchy — a POC with 8 known, fixed
triggers does not need one.

#	Agent	Endpoint	Trigger	Input	Output	Notes
1	Signal Ingestion	POST /signals	article read / video watched / AI tool used (background)	user_id, content_id, signal_type, depth_pct (optional)	{signal_id, score_updated, new_score?, delta?}	Writes to engagement_signal. No dedup — log every signal, even repeats. Validate user_id/content_id exist and signal_type is one of the six below; reject with a clean error otherwise. If the Scoring Agent call fails, the signal write still stands — return score_updated: false, not an error.
2	Engagement Scoring	(called internally by #1, not its own public route)	after signal logged	user_id, signal_type, depth_pct (passed in, not re-queried)	new score, delta	delta = weight * (depth_pct/100) if depth_pct is not None else weight; weight from signal_weight_config, 0 if no config row for that signal_type (log a warning, do not raise); new_score = round(min(100, current + delta)); level bucket: <40 "Getting Started", 40-74 "Active", 75+ "Very Active"

Signal types (six values, kept in constants.SIGNAL_TYPES, single source
of truth): ARTICLE_READ, VIDEO_WATCHED, AI_TOOL_USED, ASK_AI_QUERY,
ARTICLE_SHARED, CONTENT_DOWNLOAD. Corrected 2026-08-20 after verifying
signal_weight_config directly against the real beyondportal-db — this is
the real, already-seeded set (Summarize/Simplify/Translate all collapse
into the generic AI_TOOL_USED; Ask AI's real type is ASK_AI_QUERY, not
ASK_AI_USED). The earlier "six granular AI-tool types" note in this
section was wrong; it came from an unverified source and was corrected
once the live database could actually be checked. ARTICLE_SHARED and
CONTENT_DOWNLOAD have no agent/trigger in this POC yet — valid signal
types, no feature built around them (confirmed with Varun 2026-08-20).
3	Content Recommendation	GET /recommendations/{user_id}	dashboard load	user_id	ranked list of content_id + reason_code	Simple tag-overlap between declared_interests and topic_tags, no ML needed
4	Summarize	POST /summarize	"Summarize" click	content_id	short summary text	Single LLM call on body_text
5	Simplify	POST /simplify	"Simplify" click	content_id	plain-language rewrite	Single LLM call, different prompt than Summarize — do not merge into the same function with a flag, keep them as two small functions sharing one LLM-call helper
6	Translate	POST /translate	language selector	content_id, target_language	translated text	Single LLM call; POC scope = translate on demand, no pre-translation caching needed
7	Insight	GET /insights/{user_id}	dashboard widget	user_id, recent engagement_signal rows	1-2 sentence narrative about the user's activity pattern	Single LLM call summarizing recent signals — do not build a separate analytics pipeline for this
8	Ask AI	POST /ask-ai	chat input	user_id, question	grounded answer + which content_id it drew from	Retrieval = keyword match over content_items.body_text (no vector DB for POC) + LLM call with retrieved context in the prompt
9	Video Transcript & Summary	POST /video-summary	video content item opened	content_id	{content_id, summary}	See detailed spec below

All LLM-calling agents (4, 5, 6, 7, 8, 9) should share one thin wrapper
function for calling Azure OpenAI (endpoint, key, deployment from config) —
do not write six separate client-construction blocks.

9.1 Video Transcript & Summary Agent — Detailed Spec (added 2026-08-20)

Idempotent: transcript is stored in content_items.body_text (reused, not
a new column — Section 4 says the schema is already created and match
exactly; adding a column is the same kind of decision Key Vault/.env
needed sign-off for, and reuse means Summarize/Simplify/Translate work on
video transcripts for free with zero changes to those agents).

Logic:
1. Reject if content_id doesn't exist or its type isn't "video".
2. If body_text is already populated, skip transcription entirely — go
   straight to step 4. This is what makes the agent idempotent.
3. Otherwise: download the video from blob_url (Blob container "videos"),
   transcribe it, and store the transcript in body_text before
   proceeding. No audio-extraction step — the transcription model
   accepts common video containers (mp4 etc.) directly.
4. Generate a ~150-word summary from body_text via the shared call_llm
   helper and return {content_id, summary}. The summary itself is NOT
   persisted — regenerated on every call, same pattern as the Summarize
   agent.

   Prompt history: briefly unified with Summarize's prompt via a shared
   summarize_text() helper (2026-08-21), then reversed the same day —
   video transcripts have different artifacts than articles (filler
   words, speaker labels, timestamps) and this agent's own target length
   (~150 words) always differed from Summarize's (60-word cap). Back to
   its own _SUMMARY_SYSTEM_PROMPT in video_transcript_summary.py; still
   shares the call_llm wrapper, just not the prompt text.

Speech-to-text approach (confirmed with Varun 2026-08-20): use the
Whisper/gpt-4o-transcribe model on the same beyondportal-foundry
resource, not a new Azure resource. Because the v1 GA API surface this
app otherwise uses does not yet support audio transcription (confirmed
404 as of 2026-08), this one call goes through a second, legacy-style
AzureOpenAI client (with an explicit api_version) — foundry_client.py's
transcribe_audio() isolates this, so call_llm() and every other agent
stay on the v1 client unchanged.

Resolved 2026-08-20: transcription is fully working end-to-end, verified
live on v004 (real transcript persisted to body_text, real ~150-word
summary generated, idempotency confirmed — a second call took ~10s
instead of ~54s, meaning it correctly skipped re-transcription). Two
things worth remembering about this specific resource:
- It is NOT beyondportal-foundry — it's a separate Azure resource
  (varunbollam-3525-resource), with its own FOUNDRY_TRANSCRIBE_ENDPOINT/
  FOUNDRY_TRANSCRIBE_API_KEY (Section 3), because gpt-4o-transcribe-diarize
  isn't deployed on the main resource.
- gpt-4o-transcribe-diarize is a diarization model and requires an
  explicit chunking_strategy parameter ("auto") that plain transcription
  models don't — foundry_client.py's transcribe_audio() passes this.
Working config: FOUNDRY_LEGACY_API_VERSION=2025-03-01-preview via the
legacy AzureOpenAI client (this resource's v1-surface auth did not work
in testing, unlike beyondportal-foundry's).

Real trap found while running v001 (2026-08-20): the idempotency check
(if not item.body_text: transcribe) can't tell a real transcript apart
from leftover placeholder text — v001 still had the original seed's
"Transcript placeholder for..." string in body_text, which is non-empty,
so the agent skipped real transcription and summarized the placeholder
junk instead. Not a code bug (the check is doing exactly what it says),
but a data trap: any content_items row seeded before this agent existed
needs its placeholder body_text cleared before the agent will actually
transcribe it. v001 was cleared and re-run (real transcript now stored);
v002/v003 had their placeholder body_text cleared pre-emptively too,
even though they can't be transcribed yet (still blocked on the 25MB
limit below) — so a future run won't get fooled the same way.

Update 2026-08-20: the 25MB file-size limit noted above is no longer
hypothetical. Real durations (parsed from the actual video files —
see below) put v002 at 32.6MB and v003 at 74MB, both over the limit;
only v001 (7.5MB) and v004 (5.2MB) are under it. Chunking (or switching
those two to Azure AI Speech batch transcription, Section 6 #9's
originally-considered Option 2) will be needed for v002/v003 — revisit
once the deployment name is confirmed and a real transcription attempt
on one of these two actually fails.

Bug fixed 2026-08-20: clients/blob_client.py's download_blob_from_url()
was passing the still-percent-encoded path segments (e.g. "%20", "%2C")
straight to the Azure SDK as the blob name, instead of decoding them
first. This never surfaced on the article PDFs (their filenames have no
characters needing URL-encoding) but broke every video download, since
those filenames have spaces/commas. Fixed by unquote()-ing the path
before splitting it into container/blob_name.

Video durations were wrong (placeholder values from the original seed,
not the real files) until corrected 2026-08-20 via a zero-dependency
MP4 duration parser (backend/update_content.py's get_mp4_duration() —
reads the 'moov'/'mvhd' atom directly with stdlib binary parsing, no
ffprobe/FFmpeg needed locally or in deployment). v001's parsed value
(20:43) matched the already-known-correct real duration exactly,
confirming the parser; v002 corrected 8:15 -> 8:43, v003 corrected
10:04 -> 29:40 (v003 was nearly 3x longer than its placeholder).

published_at for all 12 content_items rows is now real, sourced from
file metadata (PDF /CreationDate for c001-c008; the same mvhd atom's
creation_time field, via get_mp4_creation_date(), for v001-v004) rather
than the placeholder seed dates. No placeholder was needed in the end —
every file had usable metadata.

Known POC-scope limitation, not a bug: no chunking for files over the
transcription API's 25MB limit. Add only if a real video actually hits
that size (Section 5 ladder — don't build for a hypothetical).

9.2 Ask AI Agent — Grounding Fix (2026-08-21)

Verified with a real unrelated question ("what is the recipe for
chocolate cake") that the agent already refused correctly rather than
hallucinating — that part of the grounding guardrail (Section 11.1) was
already working. Testing surfaced a real, narrower gap: a question that
coincidentally shares a generic word with real content (e.g. "strategy",
which appeared in 9 of our 12 articles) could retrieve irrelevant context;
the LLM still correctly declined to answer from it, but source_content_ids
kept claiming those items as sources anyway — a real UI inconsistency
("based on: X" shown next to "I don't have relevant content").

Two fixes in agents/ask_ai.py:
- _retrieve() now drops any keyword appearing in more than half the
  corpus before scoring — adapts to whatever words are actually
  over-common in the real content, instead of a hardcoded stopword list
  needing constant tuning.
- source_content_ids is now derived from the model's own answer: if it
  contains the refusal phrasing the system prompt asks for ("...have
  relevant content..."), source_content_ids is forced to [] regardless of
  what got retrieved. This is the more robust fix — no keyword heuristic
  over a 12-document corpus can eliminate every coincidental overlap
  (that would need real semantic search, out of scope per Section 6 #8),
  but the model's own grounding judgment is a reliable enough signal for
  whether to attribute sources.

Unrelated but found while testing this: 7 leftover fictional content_items
rows (c009-c012, v005-v007) were sitting in the real database, matching
an early pre-real-domain content draft, dated the same day they were
found. Source unclear (not from a seed.py run that could be reconstructed
this session — that run was verified rolled back). Deleted after
confirming no engagement_signal/recommendations rows referenced them.

Known POC-scope limitation, accepted 2026-08-21: beyondportal-db runs on
Azure SQL's General Purpose Serverless tier (GP_S_Gen5, min capacity 0.5
vCore), which scales compute up/down dynamically and causes inconsistent
query latency (the same query on the same open connection measured 6.7s,
then 0.88s, then 9s) — this is also the cause of the earlier "database
not currently available, retry" (40613) errors. Ask AI (#8) feels this
most since its retrieval scans the whole content_items table rather than
a single-row lookup by primary key. Confirmed with the user this is an
acceptable tradeoff for the POC rather than raising minCapacity (a real
Azure cost change) — revisit if latency becomes a real problem.

7. Routing — Rule-Based, Not LLM Supervisor

This was a deliberate decision (see project history): the frontend action
already tells you which agent to call, so route by trigger type, not by LLM
reasoning.

POST /signals          -> Signal Ingestion Agent -> Scoring Agent
GET  /recommendations  -> Recommendation Agent
POST /summarize         -> Summarize Agent
POST /simplify           -> Simplify Agent
POST /translate          -> Translate Agent
GET  /insights           -> Insight Agent
POST /ask-ai             -> Ask AI Agent
POST /video-summary      -> Video Transcript & Summary Agent

Implement this as normal FastAPI route functions — do not build a
"supervisor agent" or intent classifier on top of it.

8. Task Execution Plan

Work through these in order. Mark each done before starting the next unless
they're explicitly parallel-safe.

 0.1 Scaffold repo: /backend, /frontend, /db folders
 0.2 backend/requirements.txt (fastapi, uvicorn, sqlalchemy, pyodbc, openai, azure-storage-blob, python-dotenv)
 0.3 backend/config.py — loads all values (non-secret and secret) from .env via python-dotenv, exposes one combined settings object
 0.4 .env.example committed (keys only, no values), .env gitignored; confirm no secret value ever appears in .env.example, source, or logs
 0.5 backend/venv/ — local virtualenv (added 2026-08-20), created from the
     Python 3.12 install already on the dev machine, not the global
     interpreter. venv/ is gitignored. Activate before running anything:
     backend/venv/Scripts/activate (Windows) or
     source backend/venv/bin/activate (macOS/Linux), then
     pip install -r requirements.txt if packages are ever added/changed.
     Re-verified after creation: config.py imports cleanly, both unit
     test files pass, and `python -m uvicorn main:app` serves real
     requests — all inside the venv, not the global Python.
 1.1 backend/models.py — SQLAlchemy models for all 6 tables (Section 4)
 1.2 backend/db.py — engine + session dependency for FastAPI
 1.3 backend/seed.py — inserts Lucy, 3-4 articles, 2-3 videos, signal_weight_config rows; idempotent (safe to re-run)
 2.1 backend/clients/foundry_client.py — one function: call_llm(system_prompt, user_prompt) -> str
 2.2 backend/clients/blob_client.py — upload_file, get_blob_url helpers
 3.1 backend/agents/signal_ingestion.py + scoring logic inline or in same module
 3.2 backend/agents/recommendation.py
 3.3 backend/agents/summarize.py
 3.4 backend/agents/simplify.py
 3.5 backend/agents/translate.py
 3.6 backend/agents/insight.py
 3.7 backend/agents/ask_ai.py
 3.8 backend/agents/video_transcript_summary.py (added 2026-08-20, see Section 6 #9)
 4.1 backend/main.py — wires all routes per Section 7 table
 5.1 Manual test each endpoint with a real request (curl/Postman), confirm DB rows and LLM responses look correct
 5.2 Run the full Lucy demo sequence: load dashboard -> read article -> score updates -> click Summarize -> click Ask AI
 6.1 Push to GitHub, confirm App Service deployment succeeds
 6.2 Hit deployed /recommendations/{user_id} and /summarize to smoke-test production
9. Definition of Done (per task)

A task is done when:

It runs without error against the real Azure resources (not mocked)
It has type hints and handles the "external call fails" case
No secret values appear in the diff
It does not introduce a class/framework/abstraction that only this POC's
8 fixed agents would ever use — if in doubt, re-check Section 5's ladder
10. Explicitly Out of Scope

Do not build, even if it seems related: Communities, Events, Moderation,
RM Workspace, Intent Detection (the CRM kind), NBA Agent, CRM sync,
Power BI/EDP export, multi-language UI chrome (only content translation
per Section 6 #6 is in scope), vector database, LLM-based routing/supervisor.

Update: Key Vault integration was tried and then reversed back to .env
for secrets (see Section 3, updated 2026-08-19). Do not build Key Vault
integration for this POC.

11. Additional Engineering Standards (merged from team rule set)

A broader team rule set (.mdc files: architect, backend, frontend, database,
cache, RAG, agents, security, testing, devops, response-style, coding-standards)
was provided for reference. Most of it describes a different stack than
this project — PostgreSQL, Next.js, Redis, AWS/Docker/ECS, vector-DB RAG, and
a full multi-agent framework (planner/executor/memory/supervisor) — and
directly conflicts with decisions already made in this file (Azure SQL, plain
React, no agent framework, rule-based routing, no premature abstraction for
8 functions). Those conflicting parts are intentionally NOT applied here.
Sections 4–7 above remain the source of truth for schema, stack, and
architecture.

The parts that are genuinely stack-agnostic and consistent with this
project's decisions are folded in below.

11.1 Security (always applies)
Never hardcode secrets, API keys, tokens, credentials, or private URLs —
see Section 3; everything comes from .env (gitignored), never from source.
Never log passwords, tokens, raw secrets, or sensitive user content
(including LLM prompts/responses that might echo secrets).
Validate and sanitize all user input at every trust boundary (request
bodies, LLM output before it's written to the DB) — already required by
Section 5.
Treat uploads, URLs, and content pulled into prompts as untrusted; guard
against prompt injection in the Ask AI agent (#8) — don't let retrieved
body_text override system instructions.
Do not return raw stack traces or database errors to the client — catch
exceptions in each route and return a clean, generic error response.
Use least-privilege access scoped to what each component needs (Blob,
SQL) — Managed Identity where the hosting platform supports it.
11.2 Testing & code quality

For this POC's scale, keep testing pragmatic rather than exhaustive:

Add basic unit tests for the scoring formula (#2) and the recommendation
tag-overlap logic (#3) — these are the two pieces of real business logic
and are cheap to get wrong silently.
Add a smoke test per endpoint (already covered by Task 5.1/5.2) rather than
a full test suite — full test coverage is not required for an 8-endpoint
POC, but the two logic-bearing agents above should not go untested.
Mock the Foundry LLM call in any automated test — do not depend on a live
model call for tests to pass.
Use type hints and run a formatter/linter (e.g. ruff/black) before
considering a task done.
11.3 General coding standards
Prefer simple, readable code over clever code; this reinforces Section 5's
ponytail ladder, it doesn't add a new requirement.
Keep changes minimal and localized — don't touch unrelated files.
Reuse existing patterns/utilities before introducing new ones (e.g. the
shared LLM-call wrapper in Section 6, the shared INTEREST_TO_TAG map in
Section 4) rather than re-deriving them per agent.
No new dependencies beyond Section 2 without asking first (already stated
in Section 5 — repeated here because the external rule set flagged it too).
Explain tradeoffs briefly when more than one reasonable approach exists,
rather than silently picking one.
11.4 Response style when Claude Code implements a task
Produce complete, working code for the task at hand — not a stub or a
toy version — but stay inside this POC's scope (Section 1, Section 10).
Explain architecture briefly only when it isn't obvious from Sections 4-7.
When a change implies a follow-up (e.g. a new env key, a new seed row, a
new test), say so explicitly rather than leaving it implicit.
Do not introduce new abstractions, layers, or frameworks not already
described in this file — if the external rule set's guidance would require
one (e.g. a repository layer, a planner/executor agent split), skip it and
flag the conflict instead of applying it silently.