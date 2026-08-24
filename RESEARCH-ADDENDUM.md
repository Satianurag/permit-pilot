# Permit Pilot — Research Addendum (Aug 21, 2026)

Follow-up research after `PERMIT-PILOT-PLAN.md`. Live-verified where noted.

---

## Verdict: kya aur research chahiye?

**Nahi — data/domain research close hai.** 209/229 NYC Socrata APIs tested, country locked, architecture locked, demo cases seeded.

**Ab build phase:** ADK + GCP scaffold, Socrata adapter, Temporal durable workflow, 4-min demo video. Neeche sirf woh gaps hain jo research se close kiye gaye.

---

## 1. Mandatory hackathon stack (rules verified)

Source: [allthingsagentichackathon.devpost.com/rules](https://allthingsagentichackathon.devpost.com/rules)

| Requirement | Detail |
|-------------|--------|
| Deadline | **Aug 31, 2026 @ 5:00 PM PT** |
| Credits form | [forms.gle/riGhgDSHkHeMx8Ca6](https://forms.gle/riGhgDSHkHeMx8Ca6) — **Aug 28, 12:00 PM PT** (ya jab tak supply hai) |
| Model | **Gemini 3.5+** via Gemini API or Vertex AI |
| Agent framework | ADK **or** GenAI SDK **or** Antigravity **or** GenKit |
| GCP service | Cloud Run, Firestore, Pub/Sub, GKE, Cloud SQL, etc. |
| Video | ≤4 min, unedited live execution, **visible GCP proof** (Console / Cloud Run / Vertex / `.run` URL) |
| Repo access | `testing@devpost.com`, `cloudhackathons@google.com` if private |
| Bonus | Blog +0.2, social `#AllThingsAgenticHackathon` +0.2, Gemma/Veo/Lyria +0.2 each (max +0.6) |

**Recommended build wiring (research, not yet implemented):**

```
Clerk UI (Cloud Run)
  → agentgateway (CEL policy)
  → ADK root orchestrator (Gemini 3.5 on Vertex)
  → Temporal workflow (temporalio + GoogleAdkPlugin)
  → dept agents as ADK sub_agents / RemoteA2aAgent on separate Cloud Run services
  → Socrata tools (BBL/BIN join)
  → Langfuse via GoogleADKInstrumentor (OTel)
```

References:
- ADK on Cloud Run: [docs.cloud.google.com/run/docs/ai/build-and-deploy-ai-agents/deploy-adk-agent](https://docs.cloud.google.com/run/docs/ai/build-and-deploy-ai-agents/deploy-adk-agent)
- ADK + Temporal durable execution: [docs.temporal.io/develop/python/integrations/google-adk](https://docs.temporal.io/develop/python/integrations/google-adk)
- ADK multi-agent A2A on Cloud Run: [cloud.google.com/blog/topics/developers-practitioners/building-distributed-ai-agents](https://cloud.google.com/blog/topics/developers-practitioners/building-distributed-ai-agents)
- Langfuse + ADK: [langfuse.com/integrations/frameworks/google-adk](https://langfuse.com/integrations/frameworks/google-adk)

**Langfuse caveats (build time):**
- Use `runner.run_async()` not sync — OTel context breaks on background threads
- ADK spans may not populate Langfuse `usage_details`; use standard OTel token attrs if cost tracking needed

---

## 2. Critic agent — ordinance citation source (NEW, live verified)

Demo beat #4 requires **cite-or-reject**. Socrata gives facts (zoning district, violations) but not ordinance text.

**Best free source: [BetaNYC/nyc-charter-laws-rules](https://github.com/BetaNYC/nyc-charter-laws-rules)**

| Tool | Use |
|------|-----|
| `search` | Keyword across Charter, Admin Code, Rules |
| `get_section` | Retrieve by citation (e.g. `§ 259`, `11-602.1`) |
| `get_title` | Full chapter/title |

- Source: American Legal Publishing bulk XML — **no API key**
- Admin Code XML zip live: `http://files.amlegal.com/pdffiles/NewYorkCity/Admin/XML.zip` (HTTP 200, ~65 MB)
- MCP server included — Critic agent tool banane ke liye direct fit

**Secondary (optional, paid after trial):** [ZoningVerdict](https://zoningverdict.com/developers) — address→district + cited rules. 100 free calls/month.

**Skip for MVP:**
- `maps.nyc.gov/geoclient/v1` → **HTTP 410 Gone** (deprecated)
- `api.nyc.gov/geoclient/v2` → **HTTP 401** (NYC.gov API key required)
- PLUTO `64uk-42ks` already gives `zonedist1`, `landuse`, `histdist` — sufficient for Zoning Agent facts

---

## 3. Demo case seeds (NEW — live Socrata)

Har demo beat ke liye real property — build mein seed karo.

### Case A — Primary (demolition + violation history)
| Field | Value |
|-------|-------|
| Address | 43-30 PARSONS BOULEVARD, QUEENS |
| BIN | `4117367` |
| BBL | `4051980021` |
| Work | Construction Fence — Demolition of 3 story building |
| Zoning | R4, LandUse=11, no historic district |
| Owner | FLUSHING HOSPITAL MEDICAL CENTER |
| Data richness | 7 permits, 5 filings, 56 DOB violations, 6 ECB, 5 complaints, 2 elevators, 3×311 |

### Case B — Landmark district conflict
| Field | Value |
|-------|-------|
| Address | 112-08 178 STREET, QUEENS |
| BBL | `4103000034` |
| Historic district | **Addisleigh Park Historic District** |
| Landmarks API | `gpmc-yuvp` → 2 rows on this BBL |

Landmarks agent blocks → Critic cites LPC / Zoning Resolution via BetaNYC `get_section`.

### Case C — Incomplete filing (multi-week Temporal workflow)
| Field | Value |
|-------|-------|
| Address | 761 MACON STREET, BROOKLYN |
| BIN | `3040031` |
| BBL | `3014930048` |
| Filing status | **Incomplete** (`w9ak-ipjd`) |
| Work | Plumbing modifications to existing kitchen |

Clerk intake → durable workflow with signals for document upload.

---

## 4. APIs — kya skip karna hai

| Source | Status | Action |
|--------|--------|--------|
| `avgm-ztsb` FDNY live | Timeout | Use `bi53-yph3` |
| `pkdm-hqsa` Stop Work | 404 retired | `eabe-havv` + `6bgk-3dad` |
| `jz4z-kudi` OATH hearings | Timeout | `y3hw-z6bm` |
| `k55i-dnjd` Dev Pipeline | 404 | `8586-3zfm` + `br6q-ssj3` |
| Geoclient v1 | 410 Gone | PLUTO BBL/BIN joins |
| Geoclient v2 | 401 without key | Optional later; not blocking |
| NYC Zoning API (`zoning.planningdigital.com`) | No JSON response in live test | PLUTO `64uk-42ks` covers zoning facts |

---

## 5. eBau-shaped mock — minimum surface

Agents orchestrate around this; eBau fork nahi karna.

| eBau concept | Permit Pilot mock endpoint |
|--------------|---------------------------|
| Dossier / Case | `POST /cases` — BBL, BIN, packet refs |
| Distribution | `POST /cases/{id}/distribution` — dept routing |
| Tasks | `GET/POST /cases/{id}/tasks` |
| Claims | `POST /cases/{id}/claims` — ask applicant |
| Audit | `GET /cases/{id}/audit` — append-only log |
| Templates | `GET /templates/{work_type}` |

Backend stores in Firestore; agents read/write via gateway-allowlisted tools.

---

## 6. Research NOT needed anymore

- Country comparison (UK/Finland/Switzerland/Australia) — NYC wins
- Socrata catalog expansion beyond 209 OK — diminishing returns
- Hackathon track crowding re-analysis — Fleet locked Aug 15
- OSS fork evaluation (eBau, permit_os, etc.) — reference only, no fork

---

## 7. Next build steps (priority order)

1. `$150 GCP credits` form submit (Aug 28 se pehle)
2. ADK multi-agent skeleton + `adk deploy cloud_run`
3. Python Socrata adapter (`BBL`/`BIN` join layer from plan Part 5)
4. Temporal + `GoogleAdkPlugin` — demo beat #3 (`kubectl delete` resume)
5. BetaNYC MCP tool on Critic agent — demo beat #4
6. Langfuse OTel — demo beat #5 trace walkthrough
7. Seed Cases A/B/C on startup
8. 4-min unedited demo script with GCP Console visible
