# Local follow-up: private restore race and incomplete calculation UI (2026-10-27)

## Scope and result

No additional Preview deployment, remote push, key/SSO change or data migration was performed. Current cloud Preview remains65c5fa7. Local bundle contains cancellation fix0f62a28 plus this narrow private restoration fix.

An independently reproduced race exists in personal_navigation.js cold(): a failed obsolete restore unconditionally activated the public view, clearing a newer chosen observer. Capture the activation generation and clear only if it still owns the current generation. Also handle rejected public BrowserHistory.ready without an unhandled personal cold-restore rejection. This does not establish that every previously observed selection reversal has this single cause; public Board navigation already fences stale responses.

The exact old source ran against the new five-case regression:2pass/3fail. Fixed source:5/5pass. Combined browser/cancellation/input/private JS tests:24/24pass. Browser protocol and calculation-cancellation Python suites:27pass in the aggregate invocation; adding the cut-out cancellation module initially hit its existing tests-path import requirement (one import error, no executed numerical failure). Rerun with PYTHONPATH=.;tests:2/2pass in7.119s. No broad suite or new heavy seven-player benchmark was run.

## Real browser, local public-equivalent endpoint only

Local-only tests/browser_history_ui_probe.py injects one failure or a short real calculation_budget deadline at the existing forecast boundary; no production budget or numerical policy changes. Synthetic five-player citizen4/wolf1, port18824.

- Deadline0.05seconds: server logged stop=time at0.062seconds. Main failed state retained role rates80%/20%, showed win rates as uncomputed and a retry button. Retry completed at exact7/15 (display46.67%) and8/15.
- Injected recoverable forecast failure: Main showed the failure and uncomputed win rates, retained the adopted Board, and retry completed46.67%/53.33%. Reload reconstructed the same completed result.
- Screenshots: .artifacts/ui-timeout-browser.png and .artifacts/ui-failure-retry-browser.png. No extra product UI patch was necessary for these two failure paths.

The private generation race has deterministic deferred-request VM coverage, including success/failure of obsolete restore and selection while public readiness is pending. It was not reproduced as a deterministic live-browser overlapping cold request in this pass. Do not claim that particular concurrency flow as browser-verified.

## Next authorized Preview checklist (not executed)

1. Deploy the local cancellation and private-generation fixes together only after separate deploy approval. The previous allowance of one same-version recreation has been consumed.
2. Confirm private selection stays selected when obsolete cold restore succeeds/fails after a newer selection; verify Current, reload and public return on the same origin.
3. Measure actual owning-worker CPU stop after an explicit cancel. A fetch AbortError or active=false acknowledgement is not CPU-stop evidence.
4. Check different-worker cancellation honestly: current CalculationJobs registry is process-local. Another worker cannot stop the owner by ID. Real Vercel Python disconnect propagation remains unverified; Node-only native supportsCancellation cannot be assumed for Python. A distributed cancellation guarantee would require a separately approved design.
5. Verify actual application270second deadline and platform300second kill/failure UI, retry and retained IndexedDB recipe. Local injected deadline proves application behavior only, not Vercel hard termination.
6. Preserve stable branch origin for history continuity. A new immutable deployment hostname has separate browser storage. Existing121local journals must never be uploaded as test data.

Normal18821 PID18648 and isolated18823 PID14332 were retained. Original121journal SHA256 values match the migration manifest. Temporary18824 fault-injection server is stopped after checks. No approximation, probability/cache-key/strategy change, or accepted-save cancellation was introduced.
