# Calculation queue completion and stalled transport

Local fix based on published bc605d9. No server cancellation endpoint, shared service, mathematical change or deployment.

The old coordinator waited for `response.clone().arrayBuffer()`, and the NDJSON consumer also waited for HTTP EOF after a complete event. A complete/error frame followed by an open transport therefore retained the frontend queue. There was no frontend transport deadline. This does not establish that the user's exact production incident had a missing EOF; it establishes a reachable defect in the published source.

The fix drains NDJSON through its terminal complete/error/redirect frame. The consumer likewise finishes at that frame, and both reader branches are cancelled without awaiting the tee cancellation promise. The native response still drains while computation is active, including when an obsolete caller aborts. A complete frame remains required for a successful calculation: EOF before complete, malformed JSON, stream failure and timeout never turn roles or partial results into final values.

Transport guards are separate from calculation budgets: an absolute 330-second deadline from dispatch covers missing headers/body/EOF, while a 45-second inactivity guard is enabled only after a heartbeat/position has established a live periodic stream. Every received chunk then refreshes it. This avoids imposing a 45-second computation limit on non-heartbeat paths. Timers are cleared on every exit, and there is no automatic retry. A timeout aborts the browser's real transport, which does not guarantee that Vercel cancels server computation. An ambiguous mutation timeout must not be silently retried: existing revision checks and draft preservation remain in force.

Normal waiting is still possible: the current published example completed its old calculation in about 19.23 seconds and the next request waited on the same process slot for about 18.55 seconds. A latest calculation may then take its own full duration. These are separate from the missing-EOF defect. The process semaphore remains server-owned and is released in server finally blocks, never by the browser.

## Verification

- A controlled browser transport reproduces complete-with-open-body and error-with-open-body blocking the next request in the baseline. Sending EOF manually releases both. The fixed coordinator starts the next request within the test's 200-ms observation window without that EOF; this is a local protocol fixture, not a production latency claim.
- Missing complete plus EOF is an error, not a completed calculation. Network failure releases the frontend queue.
- Absolute timeout before headers, absolute timeout during body and idle timeout after heartbeat release the queue and preserve the input fixture. Timeout expiry is simulated by invoking the registered one-shot timer; the tests do not wait 330 seconds.
- Existing CO/report/strategy edit tests retain the save FIFO, coalesce obsolete previews, ignore old results, retain latest declarations/results, and permit manual retry after errors.
- Existing public/private role-first and position-generation checks remain in place.
- Existing Flask worker/slot/budget tests cover cooperative close and deadline release. No permanent server-slot leak was reproduced.

New browser checks: `node tests/dom/calculation_queue_lifecycle.cjs` and `node tests/dom/calculation_queue_deadlines.cjs`. Existing checks: editable_calculations.cjs, position_stream_ui.cjs, roles_first.cjs. All use isolated headless Edge, not the user's Chrome.

## Cancellation without an added service

A process-local owner-bound cancel route could set an existing worker Event when routed to its owning process. It must bypass both the frontend calculation queue and server computation semaphore. It cannot guarantee delivery to another Vercel instance, and must report accepted/not-local rather than claim a stopped worker. A signed owner/session check plus an unguessable per-request capability would be required before implementation. No such route has been added here. Shared control state would still be needed for reliable cross-instance delivery.
