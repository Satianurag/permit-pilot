# Permit Pilot

**NYC building-permit clerk orchestration layer** — task inbox + case file where department agents pull **live NYC Open Data** (Socrata), write distribution reviews, and a human clerk approves. This does **not** replace [DOB NOW](https://www.nyc.gov/site/buildings/industry/dob-now.page); it sits above the examiner workflow.

Built for the [All Things Agentic Hackathon](https://allthingsagentichackathon.devpost.com/) — **Fortified Enterprise Fleet** track.

| Live service | URL |
|--------------|-----|
| Clerk app (UI + `/api`) | https://permit-pilot-538666547847.us-central1.run.app |
| ADK orchestrator | https://permit-pilot-orchestrator-538666547847.us-central1.run.app |

**GCP project:** `gen-lang-client-0233250350` · **Region:** `us-central1`

---

## What it does

Maria (NYC plan examiner) uses a production-style clerk UI:

1. **My Tasks** (`/tasks`) — daily inbox
2. **Case file** (`/cases/:id`) — Summary, Distribution, Claims, Audit tabs
3. **Department agents** — Zoning, Building/DOB, Fire, Utilities, Landmarks, plus a **Critic** (cite-or-reject)
4. **Clerk decides** — Approve dossier or request changes (sticky bar)

All distribution data comes from **real Socrata queries** keyed by BBL/BIN. Reference cases use verified NYC addresses (see `packages/permit_pilot_core/permit_pilot_core/seeds.py`). **No mock data in application code.**

---

## Architecture (as deployed)

```
Clerk UI (React/Vite)
  └─ FastAPI on Cloud Run (single container: static + /api)
       ├─ Firestore — cases, tasks, distribution, claims, audit, workflow steps, traces
       ├─ DistributionEngine — live NYC Open Data (Socrata)
       ├─ WorkflowRunner — Firestore checkpoints (crash / resume demo)
       ├─ GCP Cloud Workflows — managed durable distribution orchestration
       ├─ Vertex Gemini (google-genai) — case briefing via POST /api/cases/{id}/orchestrate
       ├─ Cloud DLP — PII redaction on intake (prod); regex fallback locally
       ├─ OpenTelemetry → Cloud Trace + Firestore trace mirror (Audit tab)
       └─ Agent gateway — fingerprint allowlist for signed A2A agents

ADK orchestrator (separate Cloud Run) — zoning, building, distribution, critic agents
```

| Capability | Implementation |
|------------|----------------|
| Persistence | GCP Firestore |
| NYC data | NYC Open Data (Socrata) |
| PII | Cloud DLP (prod) / regex (local) |
| LLM briefing | Vertex Gemini `gemini-2.5-flash` via `google-genai` |
| Agent runtime | Google ADK on Cloud Run |
| Traces | Cloud Trace + Firestore UI mirror |
| Durable workflow | GCP Cloud Workflows + Firestore checkpoints |
| Gateway | Fingerprint allowlist (`AGENT_TRUSTED_FINGERPRINTS`) |
| Deploy | Cloud Run + Artifact Registry (`Dockerfile.combined`) |

**Honest scope notes** (planned in research docs, not fully built): full Temporal cluster, Letta memory partitions, SPIFFE/Keycloak, NeMo guardrails, and production agentgateway CEL policies. The demo uses Firestore checkpoints + Cloud Workflows and a fingerprint gateway pattern instead.

---

## Repo layout

```
permit-pilot/
  packages/permit_pilot_core/   # models, Socrata, Firestore, distribution, workflow, traces
  services/api/                 # FastAPI (/api prefix)
  services/orchestrator/        # ADK agents
  web/                          # React 19 + Vite + Tailwind 4
  infra/workflows/              # GCP Cloud Workflows definition
  scripts/
    deploy.sh                   # Main app (combined UI + API)
    deploy-orchestrator.sh      # ADK service
    deploy-workflow.sh          # Cloud Workflows + IAM
    audit.sh                    # Production smoke tests (9 checks)
    seed-once.sh                # One-time Firestore bootstrap (local)
    dev.sh                      # Local API / web
  PERMIT-PILOT-ONE-PAGE.md      # Living product + demo spec (source of truth)
```

---

## Quick start (local)

**Prerequisites:** Node 22+, Python 3.12+, [gcloud CLI](https://cloud.google.com/sdk/docs/install) with Application Default Credentials.

```bash
gcloud config set project gen-lang-client-0233250350
gcloud auth application-default login

# API (port 8000)
./scripts/dev.sh api

# Web (port 5173, proxies /api → :8000) — separate terminal
./scripts/dev.sh web

# Optional: seed real NYC cases into Firestore (run once)
./scripts/seed-once.sh
```

Copy `.env.example` to `.env` for optional Langfuse export. Firestore traces are always persisted.

---

## Deploy (production)

```bash
./scripts/deploy.sh              # Clerk app — scale-to-zero, max 1 instance
./scripts/deploy-orchestrator.sh # ADK orchestrator
./scripts/deploy-workflow.sh     # Cloud Workflows (then redeploy main if env changed)
./scripts/audit.sh               # Verify all endpoints
```

**Cost-conscious defaults:** single public Cloud Run service, `min-instances=0`, `max-instances=1`, CPU throttling, no startup boost, `SEED_ON_STARTUP=false` (no Socrata churn on cold start).

---

## API highlights

All routes are under `/api`:

| Route | Purpose |
|-------|---------|
| `GET /tasks` | Clerk task inbox |
| `GET /cases/{id}` | Case summary |
| `GET /cases/{id}/distribution` | Department reviews (live Socrata) |
| `POST /cases/intake` | New case + PII redaction |
| `POST /cases/{id}/workflow/resume` | Resume distribution workflow |
| `POST /cases/{id}/workflow/gcp-run` | Start Cloud Workflows execution |
| `POST /cases/{id}/orchestrate` | Vertex Gemini briefing |
| `GET /cases/{id}/trace` | Trace spans for Audit tab |
| `GET /agents` | Agent catalog (A2A cards) |
| `POST /agents/{name}/invoke` | Gateway-signed agent invoke |
| `GET /config/observability` | Cloud Trace / Workflows console links |

---

## Demo video (remaining deliverable)

Record a **≤4 minute unedited** video per `PERMIT-PILOT-ONE-PAGE.md` §16:

1. GCP proof (Cloud Run + Firestore console)
2. Agent Catalog — signed pass, rogue blocked
3. Intake + PII redaction
4. Distribution workflow — simulate kill → resume (or Run GCP Workflows)
5. Critic citations in distribution drawer
6. Vertex orchestrator briefing
7. Audit trace replay + approve

---

## Documentation

| File | Contents |
|------|----------|
| [PERMIT-PILOT-ONE-PAGE.md](./PERMIT-PILOT-ONE-PAGE.md) | Product spec, UI, demo script, audit matrix |
| [PERMIT-PILOT-PLAN.md](./PERMIT-PILOT-PLAN.md) | Full architecture research |
| [RESEARCH-ADDENDUM.md](./RESEARCH-ADDENDUM.md) | Hackathon rules, build notes |

---

## License

Hackathon submission — see repository owner for terms.
