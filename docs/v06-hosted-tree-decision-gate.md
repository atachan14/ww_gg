# Hosted Tree lifecycle decision gate (2026-10-27)

Numerical gate is resolved in898a01a; see v06-numeric-contract-resolution.md. This document records the next stage's verified boundary, not a completed hosted implementation or permission to publish.

## Existing implementation/configuration

- wsgi.py imports create_app(deployment=True) with hybrid/seer/dawn flags only. app.py rejects GAME_TREE_PREVIEW in hosted mode. No guard was removed.
- Persistent Tree uses NavigationStore at app.root_path/.artifacts/navigation. Its immutable reconstruction recipes are already common to local users; caches/locks/documents remain process-local. No provider-neutral durable backend or remote DB/client is wired in application Python. requirements.txt contains Flask3.1.2 only.
- Formal workspace has no .env and no .vercel/project.json. The old legacy backup's .env was previously inventoried by variable NAME only and includes Supabase-related names, but the current application has no usage of those keys. They were not imported, printed, transmitted, or used for a connection. Project purpose/schema/access scope and approval to store private game evidence there are unverified. Existing credential files are not automatically authorization to create tables, expand access, or upload historical Boards.
- CalculationJobs owns active Event tokens and cancel tombstones per process. Game runtimes, completion/cache owners and the semaphore are also local. Vercel worker/coldstart transport cannot preserve these owners merely by writing JSON to /tmp.
- Function maxDuration is300 and exact budget270sec/4000000work. No deployment plan/runtime limit or operational resource guarantee was inferred from local completion times.

## Bounded independent fixture checks

Temporary directories only, no existing user journal changed or uploaded:

1. Save an existing NavigationStore action to shared fixture directory in ownerA; ownerB reconstructs an exactly equal exported document at h1. A separate empty directory reconstructs h0 instead. This confirms current recipes are reusable with a genuinely shared store, but separate serverless filesystems do not preserve history.
2. Begin a CalculationJobs token in ownerA. ownerB.cancel returnsFalse and A's Event stays unset; A.cancel returnsTrue and sets its Event. Cross-worker cancellation does not exist today. The first diagnostic script failed Python parsing before executing due to indentation, then corrected script completed; it is not counted as a product failure.
3. SHA256 of all121 pre-migration journals still equals the frozen manifest. Normal server PID18648 and code/port remain unchanged. No local restart is needed for test/docs-only changes.

## Smallest common-flow implementation plan, pending destination decision

Do not create a separate Tree simulation. Keep NavigationDocument/NavigationGame recipes and calculation/evaluator outputs common.

If keeping Vercel, obtain explicit destination/schema authorization for an existing shared backend (or a separately approved new service). Use an owner-scoped durable journal with atomic revision compare-and-swap; process memory is only an acceleration cache. Define durable job identity/status/result and cancellation/lease ownership across workers before enabling the hosted Tree guard. Persist public recipe/evidence and exact results as needed; no guessed private distribution or unfinished action-table cache. Worker caches must include full mathematical identity and must never treat a viewer's P as public Q. Security/isolation tests must not rely solely on opaque game IDs.

If an already-available persistent Python host is chosen, the same current common flow and filesystem recipe store can be used with an explicitly durable data directory and controlled process ownership. This is an alternative deployment choice, not a newly contracted service. No host or contract was selected here.

Turning off durability, silently dropping old branches, forcing a tiny cookie-only history cap, using /tmp as permanent data, or simply deleting the local-only check would not satisfy the authorized history/coldstart/cancel requirements and was not done.

## Exact pending action/approval

**Pending, not denied:** select/authorize the actual public runtime and durable storage/job destination and its allowed data/access scope. In particular, confirm whether any existing Supabase project is for WW_GG and may receive new per-user game journals/job records, and whether schema/access changes are authorized. No external private Board upload, new credentials, permissions, tables, contract, charge, push or deployment was attempted. No operation has an uncertain external outcome.

Until that dependency is resolved, hosted-entry first load/Tree/Current/reload/failure/cancel/history/coldstart/multiworker acceptance cannot truthfully be reported as passed. Existing local behavior and guard remain safe. Independent numerical/test/documentation work is completed; do not publish v0.6 as hosted Tree-ready yet.
