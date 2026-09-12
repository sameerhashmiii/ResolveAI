# RAG Knowledge Architecture

## Scope

Phase 5 implements the retrieval portion of retrieval-augmented generation. It ingests validated Markdown, creates source-preserving chunks and embeddings, stores them in PostgreSQL with pgvector, and returns ranked excerpts with real identifiers. It does not yet pass sources to a root-cause or response-generation model.

```text
Versioned Markdown + index + manifest
                -> strict metadata and checksum validation
                -> heading-aware chunking
                -> local-hash-v1 embeddings
                -> PostgreSQL + pgvector
                -> vector candidates
                -> lexical reranking + category diversity
                -> exact persisted excerpts in API and UI
```

## Ingestion

`python -m app.rag.ingest` reads only `data/knowledge/index.json` and its referenced Markdown files. Paths must remain inside the knowledge directory. Article IDs and source paths must be unique, Markdown title and article ID must match metadata, and every source must match the Phase 3 manifest checksum.

The chunker groups adjacent Markdown sections while retaining headings, caps chunks at 1,200 characters, and records token count and chunk order. The current 100-article corpus produces 300 chunks.

Ingestion is idempotent:

- New article: create document and chunks.
- Changed checksum or embedding model: update metadata and replace chunks.
- Unchanged active article: skip without rewriting identifiers or timestamps.
- Missing previously active article: mark inactive rather than deleting history.

Docker Compose runs migration and ingestion as successful one-shot gates before starting the API.

## Embeddings

`local-hash-v1` is a transparent 384-dimensional signed feature-hashing embedding over normalized technical unigrams and adjacent bigrams. SHA-256 selects dimensions and signs; vectors are L2-normalized.

Benefits:

- No paid API, model download, network, or GPU.
- Byte-for-byte deterministic across processes.
- Fixed dimensions compatible with one pgvector column.
- Fast enough for local startup and evaluation.

Limitations:

- It encodes lexical/domain similarity, not learned language semantics.
- Hash collisions and vocabulary differences can reduce relevance.
- Scores must not be interpreted as confidence or evidence quality.

The `EmbeddingProvider` protocol isolates this choice so a tested learned or hosted model can replace it with a new migration/model version.

## Query Expansion

Fixed support-domain mappings append visible synonyms for VPN, DNS, identity/MFA, Wi-Fi, email, and application access. A bounded rule recognizes “VPN connected but internal services unavailable” and adds name-resolution terms. No LLM rewrites the query and no answer is generated.

Category hints reserve space for categories explicitly signaled by the query. This prevents several near-duplicate DNS articles from crowding relevant VPN context out of the five-result primary scenario.

## Ranking

1. pgvector exact cosine distance selects up to 40-200 active candidates for `local-hash-v1`.
2. Cosine distance is normalized to a 0-1 similarity.
3. Lexical query-token recall is computed against exact chunk content.
4. Final score is `0.75 * vector_similarity + 0.25 * lexical_recall`.
5. Results use deterministic tie-breaking, at most two chunks per document, and category diversification.

Exact search is intentional for 300 chunks. An HNSW index would add operational complexity without measurable benefit at this corpus size.

## Citation Integrity

Each result contains persisted `source_id` and `document_id` UUIDs, source `article_id`, path, heading, and exact chunk content. The UI never constructs a title or excerpt. Expanding a source reveals the API excerpt, and the document endpoint resolves the same source ID to the same content.

Ground-truth evaluation files are not mounted into the API container and are never ingested into retrieval.

## APIs

- `GET /api/v1/knowledge/search?q=...&category=...&top_k=5`
- `GET /api/v1/knowledge/documents/{document_id}`

Both require authentication. Query and result limits are validated, vectors are never returned, inactive documents are excluded, and malformed frontend payloads become a safe retrieval error rather than a render failure.

## Next Boundary

Phase 6 can consume these typed retrieval results as one read-only investigation tool alongside similar tickets, telemetry, logs, and system status. Retrieval output remains evidence input; it is not itself a diagnosis.
