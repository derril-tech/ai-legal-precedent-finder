# AI Legal Precedent Finder — Delivery Plan (v0.1)
_Date: 2025-08-28 • Owner: PM/Tech Lead • Status: Draft_

## 0) One-liner
**“Ask a legal question and instantly see precedent-backed answers—with citations, case passages, and a dynamic precedent graph.”**

## 1) Goals & Non-Goals (V1)
**Goals**
- Hybrid semantic + keyword search across case law.
- RAG answers with inline auto-citations (case, docket, court, page/paragraph).
- Precedent graph visualization with treatments (followed, overruled, distinguished).
- Summaries of holdings/reasoning/dicta.
- Exports: briefs (DOCX/PDF), citation tables (CSV), JSON bundles.

**Non-Goals**
- Legal judgment or advice; strictly research support.
- Drafting new filings, motions, or pleadings.

## 2) Scope
**In-scope**
- Ingest case law from CourtListener, Caselaw Access Project, APIs, firm repos.
- Normalize citations, parties, courts, judges, outcomes.
- Sectionizer + chunking (paragraph-level embeddings).
- QA pipeline with evidence-grounded answers and auto-citations.
- Precedent graph construction and visualization.
- Exports (briefs, citation tables, JSON).

**Out-of-scope**
- Integration with e-filing or litigation management systems.
- Non-case legal sources (statutes, regs) — reserved for future.

## 3) Workstreams & Success Criteria
1. **Ingest & Normalize**  
   ✅ Parse case texts, normalize citations/parties/outcomes, sectionize into passages.
2. **Index & Retrieval**  
   ✅ Hybrid retrieval (BM25 + pgvector) with rerank; top-20 retrieval < 1.5s p95.
3. **RAG & QA**  
   ✅ Answers with inline citations; “no precedent found” fallback; avg ≥ 2 citations per answer.
4. **Precedent Graph**  
   ✅ Directed graph edges labeled with treatment type; correctness ≥ 80% vs benchmarks.
5. **Summaries & Exports**  
   ✅ Summaries of holdings/reasoning; briefs export < 12 min median from query.

## 4) Milestones (~12 weeks)
- **Weeks 1–2**: Infra, DB schemas, ingest pipeline (case-ingest, normalize).  
- **Weeks 3–4**: Indexing + retrieval pipeline; frontend search workspace.  
- **Weeks 5–7**: QA pipeline with auto-citations; answer panel; citation previews.  
- **Weeks 8–9**: Graph-worker for precedent graphs; graph viewer frontend.  
- **Weeks 10–12**: Summaries + exports (briefs, citation tables); QA, hardening, pilot rollout.

## 5) Deliverables
- Dev/staging/prod environments with IaC.
- OpenAPI 3.1 spec (/v1); TypeScript SDK; Postman collection.
- Synthetic benchmark sets (retrieval gold, citation extraction, graph edges).
- Playwright E2E flows.
- SRE dashboards + runbooks.

## 6) Risks & Mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| OCR errors in scanned judgments | Medium | Dual OCR engines; fallback to manual flag |
| Citation parsing ambiguity | High | Use regex + ML parser; canonicalize to standard citation IDs |
| Graph over-complexity at scale | Medium | Incremental updates; Neo4j optional backend |
| Answer hallucination | High | Citations-first decoding; “no precedent found” fallback |
| Latency from large corpora | Medium | Redis caches; ANN tuning; precompute for top cases |

## 7) Acceptance Criteria
- Faithfulness ≥ 0.85 (human-rated).  
- Citation coverage avg ≥ 2 per answer.  
- Graph correctness ≥ 80%.  
- Brief export median < 12 min.  
- SLOs met in staging 72h burn-in.  

## 8) Rollout
- Pilot with law firm research team.  
- Beta with feature flags (graph, summaries).  
- Public GA with disclaimers and jurisdiction configs.