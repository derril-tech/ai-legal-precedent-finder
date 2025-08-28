# AI Legal Precedent Finder — Architecture (V1)

## 1) System Overview
**Frontend/BFF:** Next.js 14 (Vercel).  
**API Gateway:** NestJS (Node 20) REST /v1 with OpenAPI 3.1, Zod validation, Problem+JSON, Casbin RBAC, RLS.  
**Workers (Python 3.11 + FastAPI):**
- case-ingest (parse XML/HTML/PDF, OCR fallback)
- normalize-worker (citations, parties, courts, outcomes)
- embed-worker (paragraphs, holdings, citations)
- rag-worker (retrieval + planning + generation with citations-first decoding)
- graph-worker (precedent graph construction + metrics)
- summary-worker (holdings/reasoning/dicta)
- export-worker (briefs, citation tables, JSON bundles)

**Event Bus:** NATS (`case.ingest`, `case.normalize`, `index.upsert`, `qa.ask`, `graph.update`, `summary.make`, `export.make`) + Redis Streams DLQ.  
**Datastores:** Postgres 16 + pgvector (paragraph embeddings), S3/R2 (opinions/exports), Redis (cache), optional Neo4j (graphs).  
**Observability:** OTel + Prometheus/Grafana; Sentry.  
**Security:** TLS/HSTS/CSP, RLS, Cloud KMS, signed URLs, audit logs.

## 2) Data Model (summary)
- **Tenancy:** orgs, users, workspaces, memberships.  
- **Cases:** metadata (citation, docket, court, jurisdiction, outcome, date, s3_text/pdf).  
- **Passages:** paragraph-level embeddings (HNSW index).  
- **Citations:** case_citations (edges: follow, overrule, distinguish).  
- **QA:** qa_sessions, answers (text + reasoning), citations (linked to case + passage).  
- **Graph:** precedent_graph nodes, edges stored in Postgres or Neo4j.  
- **Summaries:** holdings, reasoning, dicta.  
- **Audit:** audit_log.

**Invariants**
- RLS isolation; each answer must cite ≥1 case or return “no precedent found.”  
- Canonical citation formats (Bluebook).  
- Treatments normalized (followed/overruled/distinguished).

## 3) Key Flows

### 3.1 Ingest & Index
- Ingest sources (CourtListener, Caselaw Access Project, APIs).  
- case-ingest worker parses text; OCR fallback.  
- normalize-worker canonicalizes citations; enrich parties, courts.  
- Paragraph chunking → embeddings via embed-worker.  
- Index to pgvector HNSW + BM25 keyword index.

### 3.2 Ask & Cite (RAG)
- API `POST /qa`: rag-worker retrieves passages (hybrid), reranks, plans grounded answer.  
- Citations-first decoding ensures inline citations.  
- FE AnswerPanel streams tokens; citations hover preview.

### 3.3 Graph & Summaries
- graph-worker builds precedent graph (edges with treatment types).  
- FE GraphViewer displays interactive force-directed graph with filters.  
- summary-worker extracts holdings, reasoning, dicta.  
- API `GET /summaries/:case_id` returns structured summaries.

### 3.4 Exports
- export-worker composes briefs (DOCX/PDF), citation tables (CSV), JSON bundles.  
- FE ReportComposer assembles reports; exports downloadable via signed URL.

## 4) API Surface (/v1)
- **Auth:** login, me, usage.  
- **Cases:** ingest, query, detail, passages.  
- **QA:** `POST /qa`, `GET /answers/:id`, `GET /answers/:id/citations`.  
- **Graphs:** `POST /graphs/build`, `GET /graphs/:id`.  
- **Summaries:** `GET /summaries/:case_id`.  
- **Exports:** `POST /exports/brief`, `POST /exports/citations`.  

**Conventions:** Idempotency-Key; Problem+JSON errors; SSE for QA and graph builds.

## 5) Observability & SLOs
- OTel spans: case.parse, embed.upsert, qa.retrieve, qa.generate, graph.build.  
- Metrics: ingest latency, retrieval recall@k, citation precision, graph edge accuracy.  
- SLOs: ingest <12s p95; QA first token <2.2s p95, full answer <10s; graph build (100k nodes) <60s p95; pipeline success ≥99%.

## 6) Security & Governance
- RLS by workspace_id; RBAC with Casbin.  
- Signed URLs for exports; per-workspace keys.  
- Audit logs of searches, answers, exports.  
- DSR endpoints; configurable retention windows.  
- Disclaimer: “Not legal advice” watermark on UI/exports.

## 7) Performance & Scaling
- pgvector HNSW tuned for paragraph embeddings.  
- Redis caches for query → top-k; citation expansion.  
- Precompute embeddings for holdings; pin frequently cited cases.  
- Incremental graph updates; Neo4j optional for large graphs.  
- Workers horizontally scaled; DLQ for retry.

## 8) Accessibility & i18n
- High-contrast mode; keyboard navigation; ARIA roles for citation chips and graph nodes.  
- next-intl for localized dates/jurisdictions.