# Batch Tree writes and geometry reads

## Separate fixes

3211e82 fixes exact legal-target support in the named compatibility observation boundary. This separate renderer change does not touch probabilities, policies, state/group identity, history or transition generation.

The previous renderer appended one row then read its rectangle, repeatedly flushing layout. It later wrote a final width and immediately read height for each row, again flushing per Item. The new TreeLayout.measure reads intrinsic widths together, writes all final widths together, then reads wrapped card/panel heights together. Rows/panels are attached before measurement; unnecessary preliminary per-row height reads are removed. Panel maximum width is read once. Existing arrangement, semantic order, shared destinations, orthogonal routing, edge anchors, view transforms, pan and controls are unchanged.

## Comparable bounded normal-UI scenario

Seven players: citizen3/medium1/seer1/wolf2; two seerCO1/2 both reporting3white, mediumCO3; MAX policies, cutoff enabled, first scan random-white. Fresh isolated browser/local server, no HTTP pre-expansion. Wait for the initial Tree, edit real Table fields, click Update, then observe normal automatic expansion for up to120s. Input-preview Off avoids unrelated preview work; Update still fully evaluates. Both runs include the legal-target repair. Process-local timing hooks are identical, no statistical speed claim from a single run.

| Metric after Update | Interleaved DOM baseline | Batched DOM |
|---|---:|---:|
| Outcome |not finished at121.580s|stable at90.156s|
| Board cards |409|741|
| Completed observed requests |80|313|
| Repeated node requests |0|0|
| Browser layout |98.064s|15.790s|
| Browser style recalculation |10.689s|23.485s|
| Browser totalTask |118.114s|85.188s|
| Longest retained long task |3.760s|0.465s|

The baseline did not complete, so this is not a same-work full-completion speed ratio. The batched run did more work and reached completion. Initial full Update83.344s in the batched run is outside this optimization; it was93.109s in baseline, not attributed to DOM batching. The full auto Tree still takes about90s and313 requests; no requests/branches were removed or falsely merged. The old46s log gap is not a measured HTTP request duration; not reproduced in this bounded path.

## Acceptance

-45 focused JS tests passed, then all56 Tree JS tests passed (measurement, order/height/spacing, routing, collapse/reopen, convergence, viewport/zoom/wheel contracts).
-New measurement tests independently check widths240/260, wrapped card heights40/22/54/20, panel ownHeight138, expanded348, no stale collapse height, stable entry order. A400-row fixture enforces one width-write phase between two measurement phases.
-Actual browser normal UI completed stable, no application/JS errors, all observed requests completed, Current visible and66 Day2-night cards present in the manual branch. Public Overview/Table fraction arrays match exactly before/after Tree expansion.
-Desktop and390px narrow browser geometry has no card overlap and identical row-key order. Inline analysis opens. Ctrl-wheel changes scale while world positions/widths remain unchanged. Desktop/narrow screenshots were inspected.

Artifacts: day2-ui-prebatch-browser.json/server.json, day2-ui-prebatch.log; day2-ui-browser.json/server.json and day2-ui-batched.log; day2-ui-visible.png, day2-ui-mobile.png; batched-all-tree-js.log. The regression dev_previews/verify_day2_visible_ui.py has fixed observation and subprocess limits and asserts stable completion; timings include normal UI refreshes, never manual GameTree HTTP pre-expansion.

No full repository-suite claim. The separate initial-read/early-edit empty-Tree race and HTTP-preloaded deep-Current missing-reference path remain outside this change. No shared-DAG rewrite, role changes, tracking normalization, approximation or saved-data deletion.

## Normal18821 final acceptance

Controlled restart applied both scoped commits to normal18821 (PID56584), MainHTTP200. Same isolated-browser real Table inputs and Update, no GameTree HTTP pre-expansion. Initial Tree14.816s, full Update80.047s, subsequent auto Tree87.576s to stable;741 cards including66 Day2-night cards, Current visible, empty status.311 observed requests completed, zero duplicates, no JS exceptions. A first-night request began before the measurement origin (carry-in); window request counts313 versus311 must not be interpreted as fewer logical branches. Browser layout15.511s, style23.172s, totalTask83.171s; maximum retained long task329ms. Public fraction arrays unchanged, desktop/narrow no overlap, order/panel/zoom-world-geometry assertions passed. `.artifacts/day2-ui-normal-browser.json`, `day2-ui-normal.log`, `day2-ui-normal.png`, `day2-ui-normal-mobile.png`.

The full automatically expanded Tree is still substantial (~88s here); no instant-completion claim. Initial exact MAX evaluation remains outside this optimization. Saved histories were preserved; only the approved ephemeral session reset occurred. No push/external deployment. Tracked source clean after local commits; unrelated untracked artifacts retained.
