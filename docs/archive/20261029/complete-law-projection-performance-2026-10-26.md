# Common state-construction cost: complete-law projection

## Boundary and cache audit

Baseline7192aa9 (implementation555e794). No user code edits; generated artifacts/preexisting previews preserved. No new game policy, private-view feature, state-key change, state merge, branch truncation or global cache.

Each InformationSetForecast owns its configured Rules/Strategy and completed value/action/policy/flow dictionaries. Values use public Board, public joint history law, past publications, private value law and observer (or existing separately justified scalar reduction); action keys additionally retain target/physical context. Board fields include full probabilities and public history, not merely visible labels. TrueScanState retains acquisitions/guard/attack correlation, rosters, tracking and observed prefix. Grouped keys share only existing proven reductions; they are not display/history IDs. These conditions are unchanged. Cache hits still observe existing cancellation/work contracts; exceptions never install completed entries.

## Same7-player case and profiling

Citizen3, medium1, seer1, wolves2; allMAX/cutoffOn. CO1 and2 both Day1white3;CO3medium. Same initial tree request sequence, fresh process/calculation/journal for each cold run. No normal user session used for profiling.

Detailed process-local instrumentation:118.6643s response vs118.6504s evaluator forecast.40,692 solve calls,9,714 value hits/30,978 misses;58,543 action lookups,1,403 hits/57,140 misses. Cumulative cache sizes30,984 values/57,145 action values include initial setup. These are computation keys, not Tree Board counts; inherited method calls must not be counted twice.

Main measured common costs: Board construction272,763 calls/11.787s inclusive(8.117s excluding other instrumented methods); normalize150,495/6.306s; TrueScanState construction170,033/5.243s; Hypothesis construction340,720/5.003s; public_children76,694/11.924s inclusive; physical_children76,694/6.018s; physical_board281,631/6.530s. Nested times overlap; do not sum them. Value lookup contains0.252s; public history readiness0.274s; day-value recording0.434s, so these are not the primary cost. Further low-rate stack sampling(3,040 samples,102.647s) likewise pointed to exact state construction/projection/normalization; it is approximate attribution, not an uninstrumented speed baseline. Some solve-exclusive time includes generator/context work, not wasted cache lookup.

## One bounded change

replace_worlds previously projected complete role mass into role_belief, then Board.__post_init__ validated the complete law and replaced that projection. For tuple complete laws with seer/hunter fields, construct Board with empty discarded priors and pass the same full world tuple directly. All Board validation/projection still runs once. Ordinary marginal-only and non-tuple compatibility inputs keep the old path. No fields of hidden hypotheses are normalized away. Invalid total mass, overlaps, role counts, live counts, claims and public history remain rejected.

## Measurements and decision

Uninstrumented cold response105.1095s before /107.4150s after; actual evaluator forecast105.0959s/107.4044s. Thus **no end-to-end speedup established**; one-pair wall times vary and must not be advertised as improvement. Warm completion is about11ms after, retaining the existing cache.

Same-process alternating old/new constructor,500 calls each,5 pairs:20-world median new/old0.6334;60-world0.5094;360-world0.6712. The redundant local projection is measurably removed, so retain this small construction simplification, while explicitly not claiming overall search acceleration. No further optimization added to rescue a headline number.

Exact public value89/224, every candidate and horizon value, full source fingerprint c94710df19129901d4e0c811d0b202b4c39fdf0a53746c56bfc16613064c6d6d, cache sizes and expansion counts equal before/after. Candidate1/2=5/16,3=4/15,4..7=89/224. No browser time is included in these evaluator/response measurements. The evaluator forecast includes root value plus candidate/horizon work; it is not an additive sum of recursive solve timings.

## Verification

54 affected Python tests passed, including5 new independent old-formula/full-state cases covering unequal masses, several role mixes, multiple wolves, post-death live-count derivation, different posterior identity, invalid inputs and compatibility.71 Tree/input/cancel JS tests passed.26 stream/cancel tests passed; the cut-out cancellation module initially failed import when called as a package because it imports a sibling top-level module; correct unittest discover invocation passed its2 cases without test changes(28 actual communication/cancel tests total). No unrelated old failures modified and no full-repository pass claimed.

Reproducers: dev_previews/profile_navigation_update.py (--profile --detail, --sample or no flag); dev_previews/benchmark_complete_projection.py. Raw outputs stay in .artifacts/navigation-next-profile.json, navigation-next-sample.json, navigation-projection-before/after.json, projection-local-timing.log, projection-regression.log, projection-js.log and projection-cutout-cancel.log. Sample stacks are never printed wholesale.

Normal server/actual browser smoke are recorded after local activation. Saved data untouched; no remote push/deploy.


Final normal acceptance: implementation a42494f, normal serverPID7424 on18821. No preexisting listener after reboot; started only this WW_GG launcher, same cookie name. Fresh isolated Edge profile:5 players citizen2/medium1/seer1/wolf1, allrandom/cutoffOff; actual Table seerCO1/2 bothwhite3; initial exact7/15, updated Currenth1 value7/15;136 rendered Boards,39 Day2day; Main→Table update→Tree→reload/narrow completed2.412s, no Runtime exceptions. Screenshot .artifacts/projection-normal-tree.png visually inspected. This small browser smoke is not the seven-player performance benchmark; that case was measured in the separate exact HTTP/evaluator fixture above. The normal server's four shared JS assets equal both static and public/static bytes.

All benchmark and test sessions finished. One nonessential attempt to tail the13MB sample log stalled in output handling; only that own read session95523 was interrupted, without touching server/tests. Subsequent tools read bounded JSON aggregates instead. No denied operation, approval wait or remaining blocker. Generated artifacts and preexisting docs/previews remain untracked; production/test/docs changes committed.
