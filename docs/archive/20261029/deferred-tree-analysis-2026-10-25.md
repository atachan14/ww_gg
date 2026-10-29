# Defer unopened secret analysis in public Tree responses

## Evidence

Same seven-player saved fixture as count-joint-tree-2026-10-25: citizen3/medium1/seer1/wolf2, two seerCO both reporting player3white, mediumCO3, execute4, MAX policies. Isolated saved-journal restoration took45.756s under profiling and46.323/46.794s in separate unprofiled baseline/candidate processes. Normal user journals and server were unchanged during diagnosis.

The profiler found `CalculationTree.read -> summary -> value -> solve` evaluating composition-conditioned P laws merely to serialize a native public Tree response. These are different full states from the parent's public-Q/physical-P evaluation and can legitimately miss the mathematical cache. No public policy should be replaced by the private composition's policy. The cost was not JSON formatting: measured JSON0.004s for362080bytes under this fixture.

Unprofiled same-stage results (cold response after the same journal restore and actual night expansion):

| Stage | Baseline | Deferred |
|---|---:|---:|
| Night expansion |0.414s|0.374s|
| First response summary |4.792s|0.017s|
| Warm response summary |0.015s|0.007s|

All12 value calls slower than5ms in baseline were secret composition routes; none remained in the deferred response. This is a response-generation improvement, not an initial86–90s MAX-evaluation improvement or a guarantee about every possible Day2-night branch.

Normal-server logs independently showed hundreds of serial automatic expansion requests, usually3–4s apart, one46s gap. This patch does not reduce the logical number of automatic expansion requests or alter auto-expansion rules. One profiled Day2-night path itself took0.053s to expand, summary0.004s. The worst46s request was not isolated in this bounded pass.

## Scope and contract

`defer_analysis=1` is an opt-in addition to persistent compact public Tree responses. Native rendering retains all public action/observation children and exact values/probabilities, role-composition metadata and navigation mappings; it does not recursively summarize secret-composition children. Non-native composition-as-navigation rendering and anonymous-owned compatibility are unchanged. The existing no-flag/full API retains its exact response contract.

The public frontend requests this opt-in. Explicit `analysis=1` computes the requested Board's conditional distribution and values through the existing evaluator. The read phase still defers other unopened future panels; only the requested distribution is evaluated. Before that reply, absent conditional values are omitted rather than replaced by the parent value. No new permanent UI prose, math policies, state ownership, belief normalization or cache-key changes were introduced. Personal-view requests remain on their existing path.

## Verification

Final focused suite:20 tests passed (deferred analysis/public response/evaluation branch); default-response exact parity remains tested. New guards reject any unopened composition value request, including other future panels when opening one panel. Public items and complete night-stage structures match the full response exactly. Explicit five-player conditional composition masses1/4,3/4 and values1/3,1/3 are independently checked.

Final-code isolated Edge five-player named public flow passed: real Current visible, inline analysis network request with both flags, exact1/3 and1/3 shown, no JS exceptions. Generated public assets synchronized.

Seven-player bounded browser API path: day-root0.025s, Day1-night0.559s, Day2-day0.074s, Day2-night0.126s; generated Current HTTP0.159s. Session-wide browser metrics were Layout0.191s, style0.036s, script0.025s, task0.435s; these are cumulative observed browser CPU, not end-to-end/server timing.13 Tree requests in that bounded probe; this is not a full-tree request-count comparison. Opening the fallback root panel completed without exceptions.

Important verification limit: the probe preloaded deep states through HTTP before selecting a generated deep Current; its Current card was not visible in the root graph. A separate same-state graph comparison reproduced the same missing intermediate public references/current reachability with the legacy no-flag response and deferred response (both missing h1~1/h1~2). This is not fixed or hidden here; API state selection succeeds, but that deep preloaded/cold navigation rendering path remains follow-up work. The first browser attempt additionally waited on the initial-load flag instead of navigationUpdate; corrected, not a product change.

Artifacts: `.artifacts/day2-tree-profile2.log`, `summary-values.log`, `deferred-summary-values.log`, `deferred-final-regressions.log`, `deferred-analysis-browser.log`, `deferred-tree-browser2.log`, `deep-current-baseline.log`. No full-repository-suite or exhaustive Tree completion claim.

## Architecture

The evaluator-owned immutable state/transition DAG is the suitable shared source; it need not materialize the full visual path tree. Existing graph records already support much of this. Display-only conditional analyses must be explicit additional evaluations, not an implicit requirement of serializing public nodes. Canonical public/physical states, private histories, policies and representative transports remain part of exact identity. Reversing dependency to a fully expanded DOM Tree would not remove exponential state/path counts or legitimate value-only reductions.

## Normal local acceptance

Applied verified code to normal18821 with a controlled restart (PID35680), MainHTTP200. Isolated browser on the actual URL created a five-player public game, exited anonymous ownership through real manual seerCO/report input, executed the known-white target, and verified the named night Current card, explicit inline analysis exact1/3, and defer_analysis network flag. JS exceptions empty; `.artifacts/deferred-analysis-normal.log`. Saved journals untouched. No external push/deploy. The seven-player bounded Day2-night API measurement above was isolated local, not an exhaustive normal-session full-tree verification.
