# Continued common-search experiments (no production adoption)

Baseline HEAD6663bab, implementationa42494f. Normal serverPID7424 was kept running throughout. User changes: only existing untracked .artifacts and docs/previews; no source edits existed at start. No data deletion, remote push/deploy, unrelated app/process intervention or new game policy.

## Findings and experiments

Existing detailed/sample evidence points to state creation, normalization and partition construction, not just cache misses. Computation values use public Board/joint histories, private law, past reports and observer under the engine's own strategy/rules; display/history occurrence IDs are not value-state identity. None of these value identities was relaxed.

All runs below used the same7-player citizen3/medium1/seer1/wolves2 allMAX/cutoffOn fixture, two seerCO both Day1white3 and mediumCO3; fixed initial expansion sequence, independent process/calculation/journal. Non-profile runs excluded browser rendering. The evaluator entry includes root/candidate/horizon calculation; recursive solve timings cannot be added as independent full work.

| Trial | Evaluator wall seconds | Decision |
|---|---:|---|
| Original uncached partition |109.089872|reference|
| Stop refining fully singleton groups |108.475558|less than1%; reverted|
| Owner-local256-entry pure partition memo |101.348367|initial apparent gain not reliable|
| Same code with memo disabled |87.550325|faster than candidate; memo reverted|
| Filter without cloning unchanged immutable hypotheses |104.342573|apparent wall gain not evidence of lower work|
| Same normalization with old clone flow |112.429688|CPU comparison below; candidate reverted|

Partition instrumentation recorded107,033 calls/6.398s, with39,327 potential hits at256 entries and39,407 at1024. This was a development cache simulation over the fixture, not an observed production cache hit count. The experimental owner-local key retained parent order, public event fields, past report timing, observer and selected target; it cached no value/P/Q law. It nevertheless failed the actual whole-run adoption criterion. Fully singleton short circuit and memo were not combined to manufacture a result.

For hypothesis filtering, only existing exact deeply immutable hypotheses could bypass a redundant replace; normalization, mass, joint memories and changed-owner records remained. Mutable/subclass handling needed the same eligibility rule already used by normalize; this was tested rather than silently weakened. CandidateCPU83.203125s vs old-flowCPU81.875s, despite candidate wall104.34s vs112.43s. Thus wall change was not proof of less computation. CPU/wall ratios (~79.7% vs72.8%) also differed. No claim of causal CPU-load attribution beyond this observation; no other applications were stopped. The additional helper/branch was reverted rather than retained on a misleading headline.

All six cases above have identical exact village89/224, every candidate and horizon value, source fingerprint c94710df19129901d4e0c811d0b202b4c39fdf0a53746c56bfc16613064c6d6d, value/action cache sizes and expansion counts. Candidate1/2=5/16,3=4/15,4..7=89/224. Numerical equality does not establish performance benefit.

## Retained deliverables

- dev_previews/profile_navigation_update.py: optional pure-partition reuse simulation and old-clone control, plus processCPU timing alongside evaluator/response wall time. All monkeypatching stays in its isolated dev process. No flags means normal evaluator semantics. Whole sample stacks are not printed to stdout.
- tests/test_partition_reference.py: independent old formula across every partition of5 people, reversed parent order, reports/timing/deaths/owners/target and list/generator compatibility. No optimized production path is assumed.
- dev_previews/experiments/frame-partition-memo.patch and actor-filter-reuse.patch: rejected code, not installed. actor-filter-tests.txt and actor-filter-microbenchmark.txt are research snapshots, intentionally not discovered as product tests. To reproduce rejected versions use a separate disposable checkout of6663bab, apply the relevant patch and copy the text test to tests/test_actor_filter_reuse.py as needed. The main checkout remains unchanged under werewolf/.
- Raw before/after/control JSON and logs in .artifacts/navigation-partition-*, navigation-frame-memo-*, navigation-actor-reuse-*. The local eligibility/secret-history research suite passed15 tests; an initial mutable-list fixture incorrectly assumed normalize accepts unhashable lists, then was corrected to compare actual old rejection behavior. Constructor validation was not removed.

## Stable-code acceptance and limits

56 affected Python tests and71 JS tests passed after rollback. Normal isolated Edge on18821:5-player allrandom setup, actual two-seer Table input, exact7/15, Currenth1,136 Boards/39 Day2day, reload and390px view, no Runtime exceptions; total smoke3.944s. This is functional smoke, not a comparable7-player speed benchmark. Existing normal session/server was not restarted. Transport checks are recorded after completion below. No full-repository pass or complete-DAG visualization fingerprint is claimed.

The goal of a reproducible full-search speedup remains unmet. No new production cache, branch omission, tracking-closure normalization or numerical expectation rewrite was retained. Next work should establish repeatable wall/CPU comparison and count repeated concrete transition generation separately from required distinct posterior work before a larger sharing redesign. Large structural changes remain a separate decision boundary; the existing exact state ownership/compatibility contracts must stay intact.


Final transport acceptance:26 stream/cancellation tests plus2 cut-out cancellation tests passed with their correct existing discovery entrypoints. ProcessCPU is measured over the calculation-stream interval (including small HTML/JSON work), not claimed as recursive solve self-time. No benchmark worker remains. git diff for werewolf/,app.py,static/,public/,templates/ is empty against6663bab; only dev measurement, independent reference tests and research documentation are retained. NormalPID7424 continues implementationa42494f; saved history remains untouched.
