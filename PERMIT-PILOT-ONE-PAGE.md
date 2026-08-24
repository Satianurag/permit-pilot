# Permit Pilot — One Page (living doc)

> **Last updated:** 24 Aug 2026  
> **Purpose:** Single source of truth — product, UI, research, demo, build. Iterate here; detail archives stay in `PERMIT-PILOT-PLAN.md` + `RESEARCH-ADDENDUM.md`.

---

## 0. One-liner

**Permit Pilot** = NYC city clerk ke liye AI orchestration layer — task queue + ek case file jahan department agents (zoning, fire, utilities, landmarks) **real NYC open data** se review likhte hain. Clerk approve karta hai. **DOB NOW replace nahi karta.**

**Pitch (demo):** *"Jab Queens demolition permit pe DEP violation aur landmark check lagti hai, agents minutes mein review queue re-plan karte hain — weeks nahi."*

---

## 1. Status

| Item | Status |
|------|--------|
| Hackathon track (Fortified Enterprise Fleet) | ✅ Locked |
| Product concept | ✅ Locked |
| Country / domain (NYC) | ✅ Locked |
| NYC APIs (209/229 tested) | ✅ Done |
| Production UI research | ✅ Done (24 Aug 2026) |
| UI spec (this doc §5–6) | ✅ Locked |
| Code / UI / API | ✅ Production deploy |
| Vertex Gemini orchestrator | ✅ Live on Cloud Run |
| Trace replay (Audit tab) | ✅ Firestore spans |
| Intake modal + PII redaction | ✅ Done |
| Agent Catalog + gateway | ✅ Done |
| Durable workflow (crash-resume) | ✅ Firestore-backed |
| Critic cite-or-reject | ✅ Done |
| Firestore (GCP) | ✅ `gen-lang-client-0233250350` |
| Live NYC Open Data | ✅ Socrata in distribution engine |
| GCP Cloud Workflows | ✅ Live (`permit-pilot-distribution`) |
| 4-min demo video | ⏳ Remaining deliverable |

---

## 2. Kya bana rahe hain (non-tech)

### Problem
- Ek building permit **4–8 weeks** review mein rehta hai.
- **5+ departments** alag cheezein check karte hain (zoning, fire, water, landmarks…).
- Paperwork messy aata hai; systems alag-alag hain.

### Solution
Maria (NYC plan examiner) ek app use karti hai:
1. Permit packet upload karti hai
2. AI specialists **parallel** mein NYC public records check karte hain
3. Har department ka result **ek jagah** dikhta hai — pass/fail + reason + citation
4. Maria **final decision** leti hai (approve ya applicant se aur docs)

### Ye chatbot nahi hai
Production clerk software = **task inbox + case file with tabs**. Hum wahi pattern follow karenge.

### Hero user
- **Maria** — municipal clerk / DOB plan examiner (hackathon “Unlikely Hero”)
- **Applicant/builder** — zyada tar **DOB NOW** use karta hai; sirf tab aata hai jab Maria missing doc maange

---

## 3. Hackathon

| Field | Value |
|-------|-------|
| Event | [All Things Agentic](https://allthingsagentichackathon.devpost.com/) |
| Track | **Fortified Enterprise Fleet** (~15–20% submissions vs ~45–55% Taskmaster) |
| Judging | Innovation 40% / Architecture 30% / Demo 30% |
| Must have | Gemini 3.5+, ADK/GenAI SDK/Genkit, 1× GCP service, ≤4 min unedited video + GCP proof visible |
| Bonus | Blog +0.2, `#AllThingsAgenticHackathon` +0.2, Gemma/Veo/Lyria +0.2 each (max +0.6) |

### 5 demo beats (video script backbone)

| # | Beat | UI moment |
|---|------|-----------|
| 1 | Clerk finds signed A2A agent card | Agent Catalog **side panel** (demo only) |
| 2 | Messy packet → PII redacted | New case **intake modal** |
| 3 | Kill zoning worker mid-run → resumes | Case **Distribution tab** status recovers |
| 4 | Critic rejects uncited claim → re-route | **Distribution drawer** + citation |
| 5 | Unsigned rogue agent blocked | Agent Catalog reject + **Audit tab** trace |

---

## 4. Architecture (high level)

```
Applicant → DOB NOW (existing, out of scope)
Clerk UI (Cloud Run)
  → agent gateway (fingerprint allowlist)
  → ADK orchestrator (Gemini / Vertex) + dept agents + Socrata tools (BBL/BIN)
  → Firestore checkpoints + GCP Cloud Workflows (durable distribution)
  → eBau-shaped case API: cases, distribution, tasks, claims, audit
  → Cloud Trace / Langfuse (OTel → Audit tab)
```

### GEAP capability map (Fleet rubric)

| Capability | Implementation |
|------------|----------------|
| Registry | A2A Agent Cards |
| Runtime | Temporal + ADK on Cloud Run |
| Memory | Letta (dept partitions) |
| Identity | SPIFFE/Keycloak pattern |
| Gateway | agentgateway CEL |
| Guardrails | NeMo + Presidio (PII) |
| Observability | Langfuse |

### eBau reference (domain only — no fork)

Agents sit **above** dossier-shaped API:

| Concept | API endpoint |
|---------|-------------------|
| Dossier / Case | `POST /cases` |
| Distribution | `POST /cases/{id}/distribution` |
| Tasks | `GET/POST /cases/{id}/tasks` |
| Claims | `POST /cases/{id}/claims` |
| Audit | `GET /cases/{id}/audit` |

---

## 5. Production UI research (24 Aug 2026)

**Sources:** eBau (inosca, Swiss cantons), Accela Civic 8.0, Idox Uniform, OpenGov Permitting, NYC DOB NOW, PermitFlow, PermitOS.

### Universal pattern

```
My Tasks (homepage)
    ↓ click task
One Case / Record / Dossier
    ├── Summary
    ├── Distribution   ← departments / AI agents report HERE
    ├── Documents
    ├── Claims         ← ask applicant
    └── Audit/History  ← trace lives HERE
```

| System | Clerk homepage | Core object |
|--------|----------------|-------------|
| eBau | Task list | Dossier + modules (Distribution, Claims, Alexandria…) |
| Accela | My Tasks portlet | Record + Documents/Workflow tabs |
| Idox Uniform | Traffic-light tasks | Case |
| OpenGov | Staff queue | Application record |
| NYC DOB NOW | (examiner backend) | Job filing / BIN |
| PermitFlow | *(builder-side, not clerk)* | Project pipeline |

### eBau internal modules (clerk-facing)

| Module | Use |
|--------|-----|
| Task list | Daily inbox — click opens right step |
| Dossier list | Search all permits |
| Distribution | Cross-dept routing + feedback |
| Claims | Ask applicant for more info |
| Alexandria | Documents |
| Journal / History | Timeline + audit |

### Key insight

- **Two apps in production:** applicant portal (DOB NOW) + staff internal area. **Never the same UI.**
- Clerks live in **tasks**, not chat.
- Multi-dept review = **Distribution tab / workflow sub-tasks**, not separate pages per agent.
- Trace/audit = **tab inside case**, not standalone product.

---

## 6. UI spec — what to BUILD vs SKIP

### BUILD (minimum honest MVP)

| # | Route / surface | What it does |
|---|-----------------|--------------|
| 1 | **`/tasks`** (homepage) | My Tasks queue — “Review distribution for BIN …” |
| 2 | **`/cases/:id`** | Single case hub with tabs below |
| 3 | Tab: **Summary** | Address, BBL/BIN, owner, work type, overall status |
| 4 | Tab: **Distribution** | Rows: Zoning, Fire, DEP, Landmarks — Pass/Fail/Checking |
| 5 | **Drawer** on Distribution row | Findings, citations, NYC evidence |
| 6 | Tab: **Claims** | Request missing docs; show applicant responses |
| 7 | Tab: **Audit** | Timeline + “Open trace replay” (Langfuse embed) |
| 8 | **Sticky bar** on case | `[ Approve dossier ]` `[ Request changes ]` |
| 9 | **New case modal** | Intake upload + BBL/BIN — not a separate app |

**Total routes: 2** (`/tasks`, `/cases/:id`) + modal + drawer.

### SKIP (not helpful for this project)

| Screen | Why skip |
|--------|----------|
| Applicant portal | NYC has DOB NOW |
| Fees / payments | Out of scope |
| Permit print / issuance | Mock decision only |
| Inspection scheduling | Post-permit |
| Admin / org / templates | Not demo story |
| Chat-first home | Not how clerks work |
| Separate page per AI agent | Use Distribution rows |
| Agent Catalog in main nav | Demo panel only |
| Standalone Trace app | Use Audit tab |

### DEMO ONLY (hackathon beats, not daily UI)

- **Agent Catalog** — slide-over panel from case or tasks header
- **Full trace walkthrough** — opens from Audit tab

---

## 7. Clerk user flow (step by step)

```
1. Maria opens app → lands on MY TASKS
2. Clicks "Review distribution — BIN 4117367"
3. Case opens → Summary tab (context)
4. Clicks Distribution tab → sees dept rows updating
5. Clicks Fire row → drawer: violations found, citations
6. If missing doc → Claims tab → request sent (workflow pauses)
7. Applicant responds (email/DOB NOW — out of UI) → task reappears in queue
8. All green → Approve on sticky bar
9. (Demo) Audit tab → replay agent steps for judges
```

### Weeks-long workflow
- **Same case screen** — only status chips + timeline update
- Temporal handles timers/signals behind the scenes
- Maria never “loses” a case

---

## 8. AI team → NYC data

| Agent | Source | Dataset ID |
|-------|--------|------------|
| Zoning | DCP PLUTO | `64uk-42ks` |
| Building/DOB | DOB NOW permits | `rbx6-tga4` |
| Filings | DOB NOW filings | `w9ak-ipjd` |
| Fire | FDNY violations (fallback) | `bi53-yph3` *(not `avgm-ztsb` — timeout)* |
| Utilities | DEP ECB | `skr7-cxt3` |
| Landmarks | LPC | `gpmc-yuvp`, `buis-pvji`, `dpm2-m9mq` |
| Housing | HPD | `wvxf-dwi5` |
| Critic | Cross-check + ordinance text | Socrata joins + [BetaNYC/nyc-charter-laws-rules](https://github.com/BetaNYC/nyc-charter-laws-rules) |
| Sentinel | Weather | Open-Meteo |

**Join keys:** `bbl`, `bin` (primary)

**Base URL:**
```
https://data.cityofnewyork.us/resource/{dataset-id}.json?$where=bbl='4051980021'&$limit=50
```

---

## 9. Demo case seeds

### Case A — Primary (demolition + violation history)
| Field | Value |
|-------|-------|
| Address | 43-30 PARSONS BOULEVARD, QUEENS |
| BIN / BBL | `4117367` / `4051980021` |
| Work | Demolition fence — demolition of 3-story building |
| Zoning | R4, no historic district |
| Richness | 7 permits, 56 DOB violations, 5 filings, 3×311 |

### Case B — Landmark conflict
| Field | Value |
|-------|-------|
| Address | 112-08 178 STREET, QUEENS |
| BBL | `4103000034` |
| Historic | Addisleigh Park Historic District |

### Case C — Incomplete filing (multi-week Temporal)
| Field | Value |
|-------|-------|
| Address | 761 MACON STREET, BROOKLYN |
| BIN / BBL | `3040031` / `3014930048` |
| Status | Incomplete filing (`w9ak-ipjd`) |

---

## 10. Safeguards (why not “just ChatGPT”)

| Safeguard | Demo beat |
|-----------|-----------|
| PII redacted before memory | #2 |
| Workflow survives worker kill | #3 |
| Critic cite-or-reject | #4 |
| Unsigned agent blocked at gateway | #5 |
| Full trace in audit | #5 |

---

## 11. Tech stack (build order)

1. GCP credits form (before 28 Aug)
2. ADK skeleton + `adk deploy cloud_run`
3. Python Socrata adapter (BBL/BIN joins)
4. eBau-shaped case API (Firestore + live Socrata)
5. Clerk UI: `/tasks` + `/cases/:id` (tabs per §6)
6. Temporal + GoogleAdkPlugin
7. BetaNYC MCP on Critic agent
8. Langfuse OTel → Audit tab
9. Seed cases A/B/C
10. 4-min unedited demo video

### Recommended wiring
```
Clerk UI (Cloud Run)
  → agentgateway
  → ADK orchestrator (Vertex Gemini 3.5+)
  → Temporal + dept agents (A2A / sub_agents)
  → Socrata tools
  → Langfuse (OTel)
```

---

## 12. Explicitly NOT building

- Taskmaster-style inbox→Jira clones
- Full DOB NOW replacement
- eBau fork
- Generic chat assistant as product
- Pages production permit software doesn’t have (see §6 SKIP)

---

## 13. Related files

| File | Contents |
|------|----------|
| `PERMIT-PILOT-PLAN.md` | Full architecture, mermaid diagrams, NYC API tables |
| `RESEARCH-ADDENDUM.md` | Hackathon rules, critic source, build steps |
| `canvases/permit-pilot-explainer.canvas.tsx` | Non-tech visual overview |
| `canvases/permit-pilot-ui-flow.canvas.tsx` | Early 6-screen sketch (superseded by §6) |
| `canvases/permit-pilot-production-ui-research.canvas.tsx` | Production UI research visual |

**When iterating UI:** edit **§5–7** in this file first. Canvases are optional visuals.

---

## 14. Repo layout (scaffold)

```
permit-pilot/
  services/api/          # Case API (FastAPI, Firestore, live Socrata)
  services/orchestrator/ # ADK root_agent + live Socrata tools
  web/                   # Clerk UI — /tasks, /cases/:id
  scripts/deploy.sh      # Cloud Run (single container)
  scripts/audit.sh       # Sequential production verification
  scripts/seed-once.sh   # One-time NYC case bootstrap (local)
```

**No mock data in code.** Reference cases use real NYC Open Data BBL/BIN; distribution reviews are live Socrata pulls.

Run locally:
```bash
# One-time: gcloud config set project gen-lang-client-0233250350
# API (Firestore via gcloud ADC locally)
./scripts/dev.sh api

# Web (separate terminal; proxies /api → :8000)
./scripts/dev.sh web

# Optional one-time Firestore bootstrap (real NYC cases)
./scripts/seed-once.sh
```

Cloud Run (production — **one public URL**, API not exposed):
```bash
./scripts/deploy.sh
./scripts/deploy-orchestrator.sh   # ADK + Vertex (scale-to-zero)
```

| Service | URL |
|---------|-----|
| Clerk app | https://permit-pilot-538666547847.us-central1.run.app |
| ADK orchestrator | https://permit-pilot-orchestrator-538666547847.us-central1.run.app |

Cost & security defaults on deploy:
- **One** Cloud Run service (`permit-pilot`) — scale to zero, max 1 instance
- CPU throttling, no startup boost (minimal spend)
- API at `/api/*` only; no separate public API URL
- `SEED_ON_STARTUP=false` — no Socrata/Firestore churn on cold starts; run `./scripts/seed-once.sh` locally when needed

Note: GCP **account** billing ≠ **project** billing link. Link with:
`gcloud billing projects link gen-lang-client-0233250350 --billing-account=YOUR_ACCOUNT_ID`

## 15. Open questions / next decisions

- [x] Frontend framework for clerk UI → **React + Vite** (scaffold only)
- [x] Case API → **FastAPI + Firestore + live Socrata** (no mocks)
- [x] Agent Catalog: real A2A cards vs demo stub → **Real registry + gateway signatures**
- [x] Trace replay in Audit tab → **Firestore OTel-shaped spans**
- [x] Vertex Gemini orchestrator briefing → **POST /api/cases/{id}/orchestrate**
- [x] ADK Cloud Run → https://permit-pilot-orchestrator-538666547847.us-central1.run.app
- [ ] 4-min demo video (script below)

## 16. Demo video script (≤4 min)

1. **GCP proof** (15s) — Cloud Run `permit-pilot` + Firestore console, project `gen-lang-client-0233250350`
2. **Agent Catalog** (30s) — signed agent passes gateway; rogue agent blocked
3. **Intake + PII** (45s) — paste packet with email/SSN → redacted in audit
4. **Distribution + crash** (60s) — workflow steps; simulate kill → resume
5. **Critic** (30s) — open distribution drawer with citations on landmark fail
6. **Orchestrator** (30s) — Run Vertex Gemini briefing on Summary tab
7. **Audit trace** (30s) — trace replay timeline; approve dossier

---

## 17. Sequential audit (services vs custom)

Run: `./scripts/audit.sh`

| # | Requirement | Implementation | Service |
|---|-------------|----------------|---------|
| 1 | Persistence | Firestore cases/tasks/audit | **GCP Firestore** |
| 2 | NYC data | Socrata HTTP client | **NYC Open Data** |
| 3 | PII redaction | `security/pii.py` | **Cloud DLP** (prod) / regex (local) |
| 4 | LLM orchestration | `orchestration/vertex.py` | **Vertex Gemini** via `google-genai` |
| 5 | Agent runtime | `services/orchestrator` | **Google ADK** on Cloud Run |
| 6 | Traces | OTel → Cloud Trace + Firestore UI mirror | **Cloud Trace** + Firestore |
| 7 | Optional traces | Langfuse ingestion when env set | **Langfuse** |
| 8 | Durable workflow | GCP Cloud Workflows + Firestore checkpoints | **GCP Cloud Workflows** |
| 9 | Gateway identity | `security/agent_gateway.py` | Fingerprint allowlist (agentgateway pattern) |
| 10 | Deploy | `Dockerfile.combined` | **Cloud Run** + Artifact Registry |

**Removed dead code (24 Aug):** split `Dockerfile.api`, `cloudbuild.api/web.yaml`, unused nginx `services/combined/`, `services/web/`.

**Context7 verified:** `google-genai` `Client(vertexai=True)` + `gemini-2.5-flash`; ADK `adk deploy cloud_run` for orchestrator.

---

