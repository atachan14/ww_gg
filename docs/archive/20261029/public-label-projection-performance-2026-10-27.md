# Public publication-label projection performance

Stable baseline: productionef24b6d, research1da836a. Same7-player citizen3/medium1/seer1/wolves2 allMAX/cutoffOn fixture, seerCO1/2 both Day1white3 and mediumCO3, identical initial Tree sequence. Individual/private-view expansion remains deferred. No game rule, likelihood, history identity or cache equivalence is changed.

## Profiling limitations and completed ranking

Two external process_time cProfile attempts exceeded the unchanged270s request budget. Both saved partial profiles and reported incomplete calculation; neither is a full-search result or a performance baseline. First included Cbuiltins, second excluded individual Cbuiltin calls. Windows external timer/event recording was too expensive. No production time limit was raised and no partial answer was installed.

A native-clock cProfile completed the whole search, retaining89/224, all candidates/horizons, fingerprint c94710df19129901d4e0c811d0b202b4c39fdf0a53746c56bfc16613064c6d6d and matching30984value/57145action records.242,093,405 recorded calls. Evaluator237.473872elapsed seconds; calculation-stream processCPU193.593750s. This includes major profiling overhead, so compare neither with an unprofiled75s run nor with historical104s as an optimization gain. Function self/cumulative below are elapsed profiling times, NOT per-function processCPU; nested cumulative values overlap.

|common function|calls|self s|cumulative s|
|---|---:|---:|---:|
|builtins.hash|13,010,546primitive /20,943,086total|9.669050|16.874551|
|dataclasses.replace|1,022,661|5.806795|36.968794|
|TrueScanState.__post_init__|170,033|5.482877|12.281609|
|normalize|150,495|5.390819|19.151127|
|Hypothesis.__post_init__|340,720|4.772211|14.289176|
|group_partition._fix|283,501|4.022919|7.780585|
|Fraction._add|3,147,611|3.836247|7.729493|
|public_convergence.transport_source|84,914|0.186513|11.771272|

Hash/equality, exact arithmetic and record validation are largely required work. Prior partition-memo/singleton and unchanged-hypothesis-clone trials are already rejected; they are not repeated. The clearest removable work is84,910of84,914transport_source calls made solely for publication_label inside anonymous_role_night.compile_abilities. These transform full public/private role distributions, Boards and acquisition/guard/attack histories although the renderer reads only public past-seer reports, medium reports and COclaims. It also exercises the more expensive constructors/normalization above. Its11.77s inclusive profiling cost is not additional to them.

Raw full evidence: .artifacts/post-death-reuse-full-call-profile.json/.prof. Partial CPU-clock evidence: .artifacts/post-death-reuse-cpu-profile.prof and post-death-reuse-python-cpu-profile.prof plus bounded error logs. No claim that full per-function CPU-clock profiling succeeded.

## One bounded candidate

publication_label optionally takes the existing bijective person mapping. _publication_facts projects only the visible fields from that mapping. It deliberately reproduces the old transport's ordering: identity map keeps original records; nonidentity map sorts seer reports after renaming, keeps medium report order and places claims in mapped player order. compile_abilities passes its existing mapping directly instead of creating two complete transported source states for this text.

All actual calculation/convergence/Current transports remain intact. No private history is discarded or identified with another history: these data simply were never inputs to this label. No new memo, approximation, branch omission, policy change or model-specific7-player case is introduced. External validation remains at the existing calculation boundaries; repeated construction of unused display-only copies is removed.

Independent tests compare all720six-person bijections against the original full-state transport plus old label formula, delayed/publication timing, identity/unsorted compatibility order, no-change/withdrawal labels and a visible-only object that raises on any private-state access. A real ability program is compiled through both paths and every complete Leaf is equal, not just counts/payoffs. Label-only construction is tested with full-state transport forbidden.5tests passed before timing; a sixth mixed true/fake simultaneous-reporter test was added and passed in the aggregate49test run.

Development-only --legacy-publication-label-flow installs the previous exact compile-label call path and original label formula for cold controls. It is never enabled by the app. Test/reference source is dev_previews/publication_label_reference.py; the old numeric strategy/evaluator are unchanged. Default dev timing uses the candidate, no profiler. ## Alternating unprofiled cold controls

|run|old full transport|evaluator wall s|processCPU s|
|---|---|---:|---:|
|a1|yes|103.409699|79.015625|
|b1|no|91.510737|74.171875|
|a2|yes|109.060585|78.281250|
|b2|no|97.405950|74.375000|

Independent process/calculation/journal, identical fixture/initial expansion sequence and no concurrent heavy tests. Full-flow control restores BOTH the original compile-label call and original publication_label formula; it is not just an extra wrapper over the new helper. All4 exactly retain89/224, candidates1/2=5/16,3=4/15,4..7=89/224, all horizon values, source fingerprint, existing cache sizes and value/action expansion counts. Both pairs improve wall10.7-11.5% andCPU5.0-6.1%. Two-pair sample; no universal speed claim and no comparison of these current-load totals with an older different-load72s measurement. Calculation timings exclude browser rendering. No output branches are hidden to produce the improvement.

## Regression status

Related Python49tests:48pass/1fail. Exact failure tests.test_recorded_public_projection.RecordedPublicProjectionTests.test_tree_arrival_updates_and_cold_Current_use_evaluated_records expects evaluation_trace.owner=evaluator but gets mixed-evaluator-day. Independently reproduced identically on git-archive1da836a in a validated owned Temp directory. It is deliberately not rewritten or claimed introduced here. No numerical/full-state failure was observed in this selected group. The earlier3unresolved phase/model-A cases remain unchanged and were not rerun in this slice; do not conflate them with this ownership-label expectation.

JS74/74pass. Stream/cancellation/position26pass. Initial combined invocation of test_cut_out_cancellation produced an import error because that old module imports test_cut_out_model_a by standalone name; use its documented discover entrypoint with tests onPYTHONPATH, not a package import. No test source was edited to hide the harness error. Separate cut-out result and runtime acceptance recorded below.

No full-repository or large6-person hunter-oracle pass is claimed. Runtime remains old stable code until scoped commit and normal browser verification. No saved data, remote push/deploy, policies or private-view features changed.

Separate cut-out cancellation discovery2/2pass(8.837s),268 labelled branches round-trip; combined with stream/cancellation/position26 gives28passing communication/cancellation cases. No test expectations were modified.


## Normal18821 browser acceptance

Implementatione2c47e1 committed before activation. Known WW_GGPID12796 alone was verified by listener and run_current_app.py --port18821 command, then normally restarted toPID7388. Saved data untouched. HTTP/main200. No app/browser permission or security change was needed.

Actual Computer/Browser Use IAB via supported cua_repl, background desktop plus narrow view. Same7-player Table flow, input previewOff, initial8/35, actual CO1/2 Day1white3 and CO3medium. Update adoption plus first observation297ms, Currenth1 and exact role rates1/2,1/2,0 while win remains未計算. Later89/224 and full automatic Tree complete. Observed win-complete checkpoint101.443s and tree checkpoint115.976s INCLUDE tool/observation intervals; they are not precise browser completion timestamps or a comparable UI speed benchmark. Improvement claim uses alternating nonprofiled evaluator/CPU controls only.

Full normal DOM before manual changes:749Boards/69Day2night. All2,108ordered rows (text/labels, itemIDs and fraction attributes),2,183ordered edges (source,target,probability) and1,738ordered toggles/state match the saved pre-change ef24b6d graph .artifacts/death-memo-normal-graph.json using two independently recomputed32bit ordered digests. Rows3e11dd79074e2e39,edgesd5e3db2338749bdd,togglesa3990fd79f8ec9cd. The initial attempt transferred full arrays and hit the browser-tool's2000element result cap; full DOM counts/digests were then computed in the read-only page scope, so no missing branches were inferred from the transfer cap. BigInt is unavailable in that restricted scope; a pure integer32bit FNV1a plus independentDJ B2XOR digest was used, with an independent UTF16-code-unit Python baseline calculation. These validation digests are not solver identity/caches.

Manual root storage changes749Boards to1 while Currenth1 is retained; reopen exposes2Boards with descendants still collapsed. Reload retains89/224. Do not claim reopening automatically restores every descendant. An extra Footer phase-next attempted after rebinding that same generated root returnsHTTP400 Invalid player (target inputs unavailable in that context). No numerical error/exception was swallowed; this additional navigation context was not independently baseline-classified or fixed in this bounded performance change. Keep it as a separate verification limitation, not a claimed newly introduced regression or a completed Footer fix.

A fresh disposable same-board Table flow was used for the explicit Tree navigation check before manual storage: enabled h1~93(public Day2night,value1) moves Current toh5, Main shows exact1/decided-village result, and reload retains h5/value1. Narrow viewport375CSSpx has panel347px; temporary viewport override reset. Screenshots saved from the browser. This verifies that selected terminal Current path; a further nonterminal Current browser traversal was not claimed. Existing related navigation/complete-state tests passed. No extra strategy, rule or private-view behavior was added.

Screenshots copied to .artifacts/publication-label-normal-overview.jpg and publication-label-normal-narrow.jpg. All diagnostic/benchmark/test processes completed. Only normal7388 intentionally remains running. No external push/deployment, credential change, saved-data deletion or unrelated project/process operation.
