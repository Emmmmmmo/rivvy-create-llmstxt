# Ranked Findings and Suggestions

1. **ElevenLabs sync state leaves obsolete documents online** ✅ **RESOLVED**  
   - **Impact:** `scripts/knowledge_base_manager_agnostic.py` skips the deletion branch for changed shards during routine syncs, so new uploads accumulate while the old documents remain in ElevenLabs. The growing `config/elevenlabs_sync_state.json` already shows `kits_sets_part1_part1`-style duplicates, and the remote KB keeps outdated content.  
   - **Suggestions:** Always delete (or overwrite) the prior document when a hash changes, persist the new document ID atomically, and introduce a reconciliation pass that compares the sync state against ElevenLabs' inventory to purge retired shards.
   - **Resolution:** ✅ **FIXED** - GitHub Actions logs from 2025-10-05 show automatic old version cleanup working perfectly: `🗑️ Deleting old version: llms-jgengineering-ie-baercoil_inserting_tools_ireland.txt (ID: EJut4oTEzajIGtavO7Sq)` followed by successful upload of new version. Hash comparison and incremental sync working correctly with `uploaded_count: 1, skipped_count: 37`.

2. **No cleanup path for removed shards**  
   - **Impact:** When a local shard file disappears (rename, re-split, product removal), it stays in both `config/elevenlabs_sync_state.json` and the remote agent. Over time the KB diverges badly from the files in `out/`.  
   - **Suggestions:** Diff the local shard list against the sync state each run, delete missing entries from ElevenLabs via `_delete_document`, and trim the sync state map so it mirrors the filesystem.

3. **`sync --force` crashes before uploading**  
   - **Impact:** `scripts/knowledge_base_manager_agnostic.py:389` indexes `self.sync_state[normalized_domain][file_path.name]` without verifying the key exists. Running `sync --force` for a new domain raises `KeyError`, preventing the first upload.  
   - **Suggestions:** Guard the lookup (e.g., `if file_path.name in self.sync_state[normalized_domain]:`), or fetch with `.get()` before attempting deletion.

4. **GitHub workflow still calls legacy tooling**  
   - **Impact:** `.github/workflows/update-products.yml:401-419` invokes `scripts/update_llms_sharded.py` and reads `manifest.json`, neither of which exist in the agnostic pipeline. Any push-trigger run will fail at that step.  
   - **Suggestions:** Replace that block with calls to `update_llms_agnostic.py` (or remove the push-path entirely) so the workflow matches the current architecture.

5. **Domain change detection relies on `HEAD~1` diff**  
   - **Impact:** After the workflow commits scraper output, `git diff --name-only HEAD~1` no longer represents the pre-commit tree. That can cause the ElevenLabs sync step to miss domains or re-sync everything.  
   - **Suggestions:** Capture the changed paths before committing (e.g., store `git status --porcelain` output) or diff against `origin/main` before writing the commit.

6. **Workflow creates unused dotted directories**  
   - **Impact:** The job logs and `mkdir -p` using `out/$domain` (dots) while the scraper writes hyphenated names. This spawns empty dirs (e.g., `out/jgengineering.ie`) that never get cleaned.  
   - **Suggestions:** Normalize the directory string in the workflow the same way the scraper does (`domain.replace('.', '-')`).

7. **Manifest sharding repeatedly duplicates suffixes**  
   - **Impact:** `scripts/split_large_shard.py` will re-split files already ending in `_partN`, producing names like `kits_sets_part1_part1`. The manifest now contains compounded keys that make diagnosis harder and confuse downstream mapping.  
   - **Suggestions:** Detect `_part` suffixes and skip re-splitting or merge shards before re-running the tool; update the manifest writer to normalize shard keys.

8. **Index stores JSON as a quoted string**  
   - **Impact:** `out/jgengineering-ie/llms-jgengineering-ie-index.json` serializes Firecrawl output as JSON-within-JSON under `markdown`. Consumers expecting Markdown receive double-encoded data, and file size balloons.  
   - **Suggestions:** Persist actual Markdown there (or move structured JSON to a dedicated property) so shard writers and RAG consumers get a clean format.

9. **Navigation cleaner is not truly agnostic**  
   - **Impact:** `scripts/update_llms_agnostic.py:144-185` filters by hard-coded keywords (`"power tools"`, `"drill bits"`), so unfamiliar sites can lose real product copy and keep irrelevant boilerplate.  
   - **Suggestions:** Move stop-words into `config/site_configs.json` or derive them from DOM structure per site.

10. **EUR currency enforcement is global**  
    - **Impact:** `_ensure_eur_currency` forces `currency=EUR` for every scrape and `_normalize_url` preserves only that query key. Sites priced in other currencies or using meaningful params (`?variant=123`) break or dedupe incorrectly.  
    - **Suggestions:** Make currency handling configurable per site and allow a whitelist of query parameters to survive normalization.

11. **Retry logic only handles HTTP 502**  
    - **Impact:** `retry_with_backoff` retries on 502 but not on 429/503/timeouts that Firecrawl commonly emits, so long crawls still fail despite the helper.  
    - **Suggestions:** Broaden the retryable exceptions (timeouts, 429, 503) and add jitter/backoff tuning.

12. **Knowledge-base file locking is POSIX-only**  
    - **Impact:** `fcntl` usage in `scripts/knowledge_base_manager_agnostic.py:102-259` breaks on Windows, preventing local tooling from working cross-platform.  
    - **Suggestions:** Wrap the locking with platform checks or adopt a portable library (e.g., `portalocker`).

