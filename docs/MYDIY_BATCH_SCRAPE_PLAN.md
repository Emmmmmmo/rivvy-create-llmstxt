# Incremental Scrape Plan for mydiy.ie

## Context
- `scripts/update_llms_agnostic.py` currently scrapes complete category trees for configured domains and writes shards plus `llms-*-index.json`/`manifest` files.
- Existing output for mydiy.ie lives in `out/mydiy-ie/` (~5k products across shards + index/manifest), so we must reuse these artifacts instead of regenerating them wholesale.
- Full reruns are slow and fragile; we want repeatable, small batch updates that only fetch new or changed URLs for mydiy.ie while preserving the current dataset.

## Goals
1. Scrape mydiy.ie incrementally in user-defined batches (e.g. 25–100 product pages per run).
2. Skip writing shards or index entries for URLs that already exist in `out/mydiy-ie/` unless explicitly forced.
3. Provide reliable progress tracking so multiple batch runs eventually cover the full catalog without duplication.
4. Maintain compatibility with other domains handled by `update_llms_agnostic.py`.

## Key Design Decisions
- **Batch Controls**: introduce CLI flags such as `--batch-size`, `--max-batches`, and `--batch-offset` (or `--resume-token`) so operators can throttle work. Default to full scrape for other domains, but for mydiy.ie default to conservative batch size if none provided.
- **Existing Data Guardrails**: load `llms-mydiy-ie-index.json`/`manifest` before requesting pages. Treat URLs already present as immutable unless `--force-refresh` is set. When a candidate URL is seen, skip scraping if it exists in index with recent timestamp.
- **Work Queue Snapshot**: persist a per-domain queue file (e.g. `out/mydiy-ie/pending.json`) capturing URLs discovered but not yet scraped. Each batch pops the next N URLs, writes results, then updates queue + manifest.
- **Discovery Strategy**: reuse current sitemap/category discovery logic but funnel results through `QueueManager` that deduplicates against both existing index and pending queue. Support optional seed URL list for targeted batches.
- **Shard Updates**: when writing shards, append only new URLs to existing shard lists, then rewrite shard files deterministically. Avoid touching shard files when a batch adds nothing.
- **Resilience**: wrap API calls with exponential backoff (reusing existing helper) and add retry for queue persistence. Add logging to surface skipped URLs and batch progress.

## Implementation Steps
1. **Refactor Initialization**
   - Extend `AgnosticLLMsUpdater.__init__` to detect `batch_mode` based on CLI flags or domain default.
   - Load existing index/manifest and derive `self.existing_urls` set for O(1) membership checks.
   - Add new attributes for queue file path and in-memory pending queue.
2. **CLI Enhancements**
   - Update argparse in `main()` to accept `--batch-size`, `--batch-offset` (or `--resume` token path), `--force-refresh`, `--pending-queue` path override, and `--dry-run` to preview batch contents.
   - Document new flags in script docstring and README usage section.
3. **Queue Management Module**
   - Create helper class (inner or separate module) responsible for loading/saving pending queue JSON with schema `{"discovered_at": iso8601, "url": ..., "meta": {...}}`.
   - Provide methods `enqueue(url, meta)`, `dequeue_batch(size)`, `peek_remaining()`, and `prune_existing(existing_urls)`.
4. **Discovery Pipeline Adjustments**
   - Where product URLs are currently added directly to manifest/index, route them through queue manager.
   - On discovery, skip enqueue when URL already exists in manifest/index unless `--force-refresh`.
   - After discovery, persist queue snapshot before scraping to guard against crashes.
5. **Batch Processing Loop**
   - New method `process_queue_batch()` to pop up to `batch_size` URLs, fetch via Firecrawl, update index/manifest/shards, and record timestamps (e.g. `last_scraped_at`).
   - Ensure shards are rewritten only for affected shard keys. Keep backup strategy for existing files (current script may already support this—reuse logic).
   - For each processed URL, remove from queue and update existing sets to avoid reprocessing within same run.
6. **Safety Checks**
   - Validate queue is empty before full-run modes to preserve legacy behaviour.
   - Add guard: if batch requested but queue empty, auto-discover new URLs (unless `--disable-discovery`).
   - Log summary: counts of skipped existing, queued new, processed in batch, remaining pending.
7. **Testing & Verification**
   - Dry-run test loading existing mydiy assets to ensure queue contains only new URLs.
   - Unit-style tests for queue manager (e.g. using `pytest` or script-level assertions) to confirm persistence + dedupe.
   - Local batch run with small size (e.g. `--batch-size 10 --dry-run`) to verify nothing in `out/mydiy-ie` changes.
   - Full batch execution on staging to ensure shards update only for new products.

## Data Migration Plan
- Before deploying new version, archive current `out/mydiy-ie/llms-*` files and manifests for rollback.
- On first run, prime queue by auto-discovering categories but preview with `--dry-run` to confirm only unseen URLs are enqueued.
- Gradually execute batches (e.g. daily 50-product runs) while monitoring index diff sizes and log warnings.

## Open Questions
- Do we need automatic pruning for URLs removed from site? (Current manifest cleanup flow may need batch-aware adaptation.)
- Should batch metadata (timestamps, batch id) be stored alongside index entries for audit?
- Is there a maximum acceptable queue size before we chunk discovery by category?
- Should `knowledge_base_manager_agnostic.py` be updated to respect new batch metadata?
