# Night public conditioning reuse investigation

Baseline: implementation ef24b6d, acceptance21cbf26. This investigation does not change game policies or merge secret histories.

## Measured identity and cost

The original7-player fixture and exact initial navigation sequence are reused from dev_previews/profile_navigation_update.py. Optional --transition-count now separately instruments phase_updates.condition_night_corpse. Complete diagnostic key=(Board,target,Rules,guard_state); Board equality includes all public history, claims, reports and exact role probabilities. No digest-only equality or label grouping. guard_state retains all private relational histories even where a no-hunter implementation does not consume it.

One instrumented run:26,383 condition calls,2,613 distinct successful complete inputs; generation1.453125CPU seconds, repeated-input generation1.25CPU seconds. Diagnostic hash0.09375CPU and membership/simulated256+1024LRU operations0.46875CPU.256-entry potential hits22,502;1024entry23,084. Nested night_observation generation4.515625CPU includes this instrumentation and inner action work; times must not be added or treated as unprofiled latency.

Scope audit: without a hunter, condition_night_corpse uses only Board,target,Rules. It does not read guard_state or wolf strategy. With one hunter, repeat-guard and no-repeat-guard conditioning differ; the latter reads complete correlated guard memories and history provenance. Any memo that omits these facts would be invalid. Hunter paths are not silently enabled by this experiment.

## Development-only candidate

Optional --trial-night-observation-memo wraps InformationSetForecast.public_children only for canonical immutable no-hunter night Boards. The exact complete key=(Board,target,Rules,Strategy), with structural hashes plus full equality, retains the configured-vs-observed strategy distinction. guard_state is omitted only because the original no-hunter function does not read it. Original physical/private projection continues separately.256-entry/768outcome-row LRU, input law<=64, calculation-owned; failed/incomplete generation not stored. Hits still check cancellation/deadline with tick(0). Mutable/subclass/numeric-alias compatibility falls back to original path. No production solver file is changed by the dev flag.

Compare alternating independent cold processes, no profiler and no parallel heavy tests. Every comparison must retain89/224, all candidate/horizon values, exact source fingerprint, existing cache sizes and expansion count. A small component micro-speedup alone is not enough to adopt additional cache complexity.

## Alternating cold controls and decision

|run|mode|evaluator wall s|processCPU s|warm calculation response s|
|---|---|---:|---:|---:|
|a1|stable ef24b6d|75.502447|70.546875|0.008779|
|b1|candidate|79.215573|69.625000|0.012120|
|a2|stable ef24b6d|76.972451|70.859375|0.009949|
|b2|candidate|81.256586|70.343750|0.012198|

Independent fresh process/calculation/journal for every row; same7-player CO fixture, initial Tree sequence and policies; no profiler and no concurrent CPU-heavy test suite. Wall is evaluator forecast time; CPU is the calculation-stream process interval, not recursive self-time. Warm response does not redo solved evaluation. Raw evidence: .artifacts/night-memo-a1/b1/a2/b2.json.

Candidate wall is slower in both pairs (+4.9%,+5.6%); CPU falls only1.31% and0.73%. These are small2-pair samples and do not establish causal wall slowdown or a universal speed difference, but they do not justify extra retained state/cache machinery. Reject the candidate; no production code or runtime change. Do not compare these times to historical104s as optimization gains. The larger original forced-death reuse remains adopted and unchanged.

All4 runs exactly equal89/224, all candidate and horizon values, source fingerprint c94710df19129901d4e0c811d0b202b4c39fdf0a53746c56bfc16613064c6d6d, existing cache sizes and expansion counts. This does not claim new whole-Tree or browser equivalence for an adopted optimization: none was adopted. There is no reason to rerun costly graph/browser acceptance for unchanged product code.

The optional candidate has been removed from the active profiling script. A nonexecutable reproducibility patch is retained at dev_previews/experiments/night-observation-memo-rejected.patch.txt. Only the condition-specific diagnostic wrapper remains available under existing --transition-count; default profiler execution and production solver do not install it.

No correctness assertions, baseline test expectations, private tracking closures, policies or error handling were changed. Known3 failures from the previous101-test run remain unresolved and reproduced on fc3eadb: PhaseBoundaryTests.test_shared_roster_excludes_execution_but_keeps_night_casualty; ModelATests.test_corrected_corpse_targets_preserve_explicit_model_difference; ModelATests.test_new_private_black_holder_does_not_change_wolf_information_policy. No assertion normalization was attempted.

At this boundary no well-supported further night-conditioning memo is available. Hunter-dependent conditioning requires full correlated memory and separate profiling; it is not authorized into this no-hunter candidate by relaxing guards. A much larger cross-state ownership or policy redesign would be a separate proposal, not an extension of this negative micro-optimization result. Normal18821 remains on ef24b6d, saved data untouched.


Final validation: stable tests.test_death_transition_memo8/8pass(0.152s), profiler syntax compilation passes. Prior broad101/98pass/3baseline failures was not rerun because no production change; no new JS/browser pass is claimed. Normal18821 remains PID12796, GET/main HTTP200, no restart or saved-data operation. All launched diagnostic/alternating benchmark/test processes completed.
