# Cooperative cancellation of obsolete read computations

## Cause and scope

The frontend previously rejected an obsolete caller but deliberately kept its native fetch and queue slot until the server completed. Thus the existing solver cancellation checks were never signaled. Aborting a browser alone was not enough. The server also has one process-wide exact calculation slot, so stale computations held up subsequent requests.

Read requests now carry a cryptographically generated32-hex request ID. A separate unqueued same-origin cancellation POST signals only the matching ID and signed-session owner. A bounded330s tombstone closes cancellation-before-registration races. Active records are request-owned and removed on completion, error or response close; this registry owns no results. Cooperative checks stop both normal requests and streaming workers. Waiting acquisition polls50ms; the worker retains its slot until its actual finally block, never releasing a live computation's slot prematurely.

The frontend waits for cancellation acknowledgement before aborting native transport and starting queued replacement work. Same-kind preview requests coalesce; saves/public updates remain ordered and are not discarded. Public GET game-tree requests participate with their full query identity. Existing caller generation/revision checks remain, and expected cancellation is propagated as AbortError. Cancellation-only checks in long immutable hypothesis loops do not charge work, normalize away history, change equality or alter formulas. Partial local results are abandoned; valid completed subresults may remain cached. Interrupted requests do not publish a complete action/value table or overwrite newer browser session cookies.

## Final verification

-53 Python tests passed in6.748s: cancellation, existing calculation and exploration streams, immutable sharing/hashes, budgets, deployment/static parity. Covers owner isolation, early/repeated cancellation, real worker exit, public Tree read scope, exact next7/15, session preservation, interrupted hypothesis construction, and resumed real CO solver probabilities equal to a separate fresh instance.
-59 JavaScript tests passed in0.414s, including explicit stop acknowledgement before next request and accepted-write preservation.
-Ephemeral threaded HTTP server + isolated headless Edge: actual8-player public work canceled; next light configuration/response ready289ms after replacement. Valid rapid previews returned AbortError, AbortError, complete; subsequent exact7/15 completed; no console exceptions or asset errors; worker registry empty. Screenshot `.artifacts/cancellation-browser.png`; log `.artifacts/cancellation-browser-final.log`. No arbitrary sleep-only solver was used for this browser case.

Cold non-profiled separate-process benchmark, identical8-player citizen3/medium1/seer1/hunter1/wolf2 random workload with2s exact budget, cancellation requested around0.2s:

| Condition | Request obsolete to worker exit | To next configuration POST completion |
| --- | ---: | ---: |
| aaedf84 old wait-for-finish policy |1.969s|2.203s|
| new explicit cancellation, before extra loop polling |0.453s|0.671s|
| final polling code measured run |0.516s|0.719s|

The cap prevents an unbounded benchmark; the baseline hits the time budget, not a completed8-player numerical answer. It is not a full-tree speed claim or browser-render timing. Additional polling did not demonstrate an improvement in this particular cold run; it provides cancellation checkpoints during large state construction. Browser289ms is a separate real HTTP observation, not interchangeable with these test-client phases. Absolute latency varies with scheduling and the longest block between checks.

## Limits

Cooperative stop cannot interrupt arbitrary native code or a thread that never reaches a check. No thread/process kill is used. On cancellation-network failure the frontend retains the old slot until normal terminal/timeout rather than assuming the server stopped. The registry is process-local: the supported normal localhost server is one threaded process; cross-worker routing requires shared cancellation infrastructure or sticky routing before equivalent guarantees can be made. Native document navigations and old clients without request IDs retain existing finite-budget/disconnect behavior. Personal-navigation compatibility endpoints classified as writes are not silently made cancellable. No new strategy, role, private-view feature, saved-data deletion or broad tracking normalization is included. Known unrelated old failures remain unmodified.

Normal local URL remains http://127.0.0.1:18821/main. Activation and final live smoke are reported separately after the verified local commit.
