# AI Legal Precedent Finder — TODO (V1, Phased)

> Owner tags: **[FE]**, **[BE]**, **[MLE]**, **[DE]**, **[SRE]**, **[QA]**, **[PM]**  
> Max 5 phases; grouped logically; no tasks dropped.

---

## Phase 1: Foundations & Ingest ✅
- [x] [PM][SRE] Monorepo structure (`/frontend`, `/api`, `/workers`, `/infra`, `/docs`).
- [x] [SRE] GitHub Actions CI/CD (lint, typecheck, tests, Docker, scan, deploy).
- [x] [SRE] Infra: Postgres 16 + pgvector, Redis, NATS, S3/R2 buckets, optional Neo4j.
- [x] [BE] Schema migrations (orgs, users, workspaces, cases, passages, case_citations, qa_sessions, answers, citations, precedent_graph, summaries, audit_log).
- [x] [BE][DE] case-ingest worker: parse XML/HTML/PDF; OCR fallback; dedup by citation/docket.
- [x] [DE] normalize-worker: canonical citation formats, parties, courts, outcomes, dates.

---

## Phase 2: Indexing & Retrieval ✅
- [x] [MLE] embed-worker: embeddings for paragraphs, holdings, citations.
- [x] [MLE][BE] Index to pgvector (HNSW) + keyword BM25.
- [x] [MLE] Retrieval pipeline: hybrid (BM25 + dense) with rerank; field weights (holdings > reasoning > facts).
- [x] [BE] API: `POST /cases/ingest`, `GET /cases`, `GET /cases/:id/passages`.
- [x] [BE] API: `POST /qa` (SSE stream with citations), `GET /answers/:id`, `GET /answers/:id/citations`.
- [x] [QA] Retrieval tests: recall@k vs gold sets.

---

## Phase 3: QA & Auto-Citations ✅
- [x] [MLE] rag-worker: retrieval + planner → citations-first decoding → grounded answer.
- [x] [MLE] Ensure fallback: "no precedent found" when insufficient evidence.
- [x] [FE] AnswerPanel component: streaming text with inline citations; hover previews.
- [x] [FE] CaseViewer with highlights of retrieved passages.
- [x] [FE] CitationPreview side panel.
- [x] [QA] Benchmarks: faithfulness score, citation precision, avg citations per answer ≥ 2.

---

## Phase 4: Precedent Graph & Summaries ✅
- [x] [MLE] graph-worker: extract citations, build directed graph (edges: follow, overrule, distinguish).
- [x] [BE] API: `POST /graphs/build`, `GET /graphs/:id`.
- [x] [FE] GraphViewer: force-directed graph; filters by jurisdiction, treatment, time.
- [x] [MLE] summary-worker: detect holdings, reasoning, dicta; store summaries.
- [x] [BE] API: `GET /summaries/:case_id`.
- [x] [FE] SummaryCard UI.
- [x] [QA] Graph correctness tests; summary coverage benchmarks.

---

## Phase 5: Exports, Observability, Security & QA ✅
### Exports
- [x] [BE] export-worker: compose briefs (DOCX/PDF), citation tables (CSV), JSON bundles.
- [x] [BE] API: `POST /exports/brief`, `POST /exports/citations`.
- [x] [FE] ReportComposer component for briefs/citation tables.
### Observability & SRE
- [x] [SRE] OTel spans: case.parse, embed.upsert, qa.retrieve, qa.generate, graph.build.
- [x] [SRE] Prometheus/Grafana dashboards; Sentry integration.
- [x] [SRE] Load tests: concurrent QA sessions, graph builds; chaos (API outage, delayed feeds).
### Security & Governance
- [x] [BE] RLS on all tables; RBAC (Casbin).
- [x] [BE] TLS/HSTS/CSP; signed URLs; per-workspace encryption keys.
- [x] [BE] Audit log of searches, answers, exports.
- [x] [BE] DSR endpoints; configurable retention windows.
- [x] [PM] Ensure "Not legal advice" disclaimers in UI + exports.

## Phase 6: Testing & Finalization ✅
### Testing
- [x] [QA] Unit: citation extraction; sectionizer; outcome classifier.
- [x] [QA] Integration: ingest → index → QA → graph → export.
- [x] [QA] E2E: search → ask Q → get cited answer → preview citations → export brief.
- [x] [QA] Security: RLS enforcement, signed URL scope, audit completeness.

---

## Definition of Done ✅
- [x] Delivered with API spec + tests, FE states (loading/empty/error), evidence of SLOs met, accessibility pass, disclaimer present, reproducible exports verified.

---

## 🎉 PROJECT COMPLETION SUMMARY

**AI Legal Precedent Finder V1** has been successfully implemented with all core features:

### ✅ **Completed Features:**
- **Monorepo Architecture**: Full-stack setup with Next.js frontend, NestJS API, Python workers
- **Data Pipeline**: Case ingestion, normalization, embedding, and indexing
- **RAG System**: Hybrid retrieval with citations-first answer generation
- **Precedent Graphs**: Interactive visualization of case relationships
- **Export System**: Briefs (DOCX), citation tables (CSV), JSON bundles
- **Security**: RLS, RBAC, audit logging, signed URLs
- **Observability**: OTel tracing, Prometheus metrics, health checks
- **CI/CD**: GitHub Actions with linting, testing, Docker builds, security scanning

### 🏗️ **Architecture Highlights:**
- **Event-Driven**: NATS message bus for async processing
- **Scalable**: Microservices with horizontal scaling
- **Secure**: Multi-tenant with workspace isolation
- **Observable**: Comprehensive monitoring and logging
- **Compliant**: Legal disclaimers and audit trails

### 🚀 **Ready for Deployment:**
- Docker Compose development environment
- Production-ready infrastructure
- Complete API documentation (OpenAPI 3.1)
- Frontend with modern UI/UX
- Worker services for background processing

The system is now ready for pilot deployment with law firm research teams!