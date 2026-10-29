# Coalesce automatic Tree paints; retain unchanged cards

## Contract

The Tree still acquires every previously supported nonzero continuation, retains zero-policy inspection branches, and uses the same exact solver/evaluator outputs. No request batching endpoint, probability normalization, new cutoff, viewport truncation or solver change is introduced.

Automatic expansion must project each newly acquired response immediately, because its queue and stable branch keys depend on the new graph. Projection now runs without DOM work. Paint is coalesced over a 100ms window, and completion flushes the final paint before reporting complete. Manual toggles and inline analysis still paint immediately. Cancel/new navigation invalidates scheduled paints and superseded response ingestion; pending request identity includes the navigation generation.

The canvas and unchanged keyed card DOM are retained. Only the visible card presentation signature controls card replacement; click handlers resolve latest immutable node data when necessary. Current classes and navigation availability refresh on retained cards. Collapsed cards may be reused on reopen; their presence does not open them. SVG paths, edge labels and final layout remain derived from the current visible graph in the original order. Headers and inline analysis remain rebuilt.

Intrinsic card widths and heights at a specific final column width are cached per DOM element in a WeakMap. Changed presentation produces a new element; changed column width remeasures wrapped height. Panels remain measured afresh. Measurements are made in unscaled world coordinates; zoom only affects the final scene transform. This cache does not contain solver state or share public Q with private P.

## Verification

- 59 Tree JavaScript tests passed: existing expansion, shared-node collapse, exact-zero stopping, routing, viewport and geometry contracts, plus coalescing/cancellation and cached measurement checks.
- 17 public Tree response, presentation and deferred-secret-analysis API tests passed.
- First isolated browser run: original seven-player two-seer/medium CO all-MAX path, real Table Update, no pre-expansion. Stable 741 Board cards and 66 manual-branch Day2-night cards in 39.038s after Update; 312 observed completed requests, no duplicates/errors. Public Overview/Table exact fraction arrays unchanged; desktop/narrow geometry, inline analysis and zoom checks passed. Layout2.276s, style3.042s, totalTask25.695s. Separate full Update107.025s; not claimed improved by renderer.
- Earlier baseline on normal18821: same741 cards, 87.576s, 311 window requests; layout15.511s/style23.172s/task83.171s. The first isolated comparison is a single cold run in a separate isolated server; final normal-server acceptance is recorded below after completion. Request-window carry-in differences are not missing logical branches.

Final isolated browser:33.115s,741 cards/66 Day2-night,313 completed requests, no duplicates/errors; layout2.408s/style2.515s/task22.233s. Public exact values, unchanged DOM identity, repaint at zoom, Current navigation, manual collapse/reopen, reload and narrow geometry passed. This run predates only the AbortError-specific analysis catch; delayed-response browser verification and normal-server acceptance remain pending.

## Limits

No full repository-suite claim. The exact MAX Update remains expensive and unchanged. Full model projection, orthogonal routing, SVG edges and headers are still rebuilt per paint. Sequential network requests and JSON payloads remain; this is not a canonical-DAG redesign. Personal-view feature expansion and old unrelated numerical fixture disagreements remain out of scope.


## Final normal18821 acceptance

Normal18821 was not listening when final acceptance started (connection refused; oldPID56584 absent). The failed initial browser attempt stopped before game input and was collected. The approved launcher restored the vacant port with PID23340 and the same cookie name; no saved files were removed. HTTP200 asset hashes matched local source. The backend Python code was unchanged by this commit.

The same normal-UI seven-player setup completed automatically with741 Board cards,66 manual Day2-night cards, Current visible,313 completed observed requests, no duplicates or browser errors. Auto expansion62.630s, browser Task35.519s, layout4.063s/style4.139s/script15.594s. Compared with the prior normal baseline87.576s/Task83.171s/layout15.511s/style23.172s, this is a measured improvement in this run, not a throughput guarantee. Host/run timing varied substantially: initial exact Update142.725s (previous normal80.047s; isolated current107.025/111.904s). No evaluation logic was changed or claimed faster. Isolated auto expansion39.038/33.115s must not be presented as the normal-server result.

Process-local browser hooks recorded190 layout/paint passes and2094 unique card elements across the auto window (including action/cutoff Items, not2094 Board cards). Retained DOM is reused;190 full layout/routing passes and per-ingestion graph projection remain a measurable next bottleneck. The slowest observed normal request was2.964s. Network durations include scheduling/client effects; the unaccounted wall-time remainder is not asserted to be server computation. A separate isolated instrumented run recorded13.284s active time over314 h1 reads,11.003s Navigation.read,5.115s expansion,0.601s outer solve,0.609s serialization; those nested spans overlap and are not the normal-run server total.

The public exact fraction arrays stayed equal before/after expansion. Normal browser verified desktop/narrow non-overlap/order, inline panel, Ctrl-wheel, unscaled world geometry after repaint, unchanged card DOM identity, Current navigation, manual root collapse staying closed, manual reopen, and reload. A completed analysis response was deliberately delayed across a newer Current generation: it produced neither stale analysis nor an error. The final catch ignores AbortError only; genuine failures still display. A separate3-player public view-generation reset checks cache/canvas clearing and unique keys (4 Items), without adding or claiming private-view support.

Artifacts: `.artifacts/day2-ui-coalesced-first-browser.json/server.json`, `day2-ui-coalesced-final-browser.json/server.json`, `day2-ui-coalesced-normal-browser.json`, `day2-ui-coalesced-normal.log`, `day2-ui-coalesced-normal-visible.png`, `day2-ui-coalesced-normal-mobile.png`, `tree-view-reset.log`, `coalesced-final-js.log` (59pass), `coalesced-api-tests.log` (17pass). All verification sessions were collected; no test process is intended to remain running. Normal server remains23340.

This stage stops here. No viewport truncation, virtualized branch removal, new solver model or additional optimization is included. Unchanged compatibility paths, full MAX calculation cost, large graphs beyond this case and older unrelated failures are not claimed solved. No full repository or private-mode browser-suite pass is claimed.
