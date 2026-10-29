# Actual-seven component-hash experiment: complete comparison, no adoption

Source preparation1e1ab5a. No application factory, CLI default, numeric rule, scope gate or public setting was changed. Current ExtensionForecast and comparison-only ComponentReuseForecast used the SAME saved actual seven-player game (C3/M1/S1/W2, P1/P2whiteP4, P3MCO, allmax), flags,4M work/115-second internal limit and fresh processes. Controller enforced120s/run,600s combined stage and1.5GB peak working set OR commit. No timeout/memory stop/incomplete result occurred.

## Complete results and timings

| Fresh cold run | Solver(s) | Whole worker(s) | Peak RSS(bytes) |
|---|---:|---:|---:|
| Current1 |48.738|52.768|769458176|
| Component1 |49.504|53.578|826241024|
| Component2 |49.502|53.586|826433536|
| Current2 |50.595|54.719|768675840|

All four complete values were3487/7200 and EVERY public Table row matched each other and the corrected saved record. Action/value expansions remained76987/31675, with121693 key requests. This is a same-condition cold comparison, not a comparison against historical49.755s. Solver time includes evaluator construction but excludes some preparation/Table writing; whole-worker time includes them. Two repetitions are descriptive, not a statistical performance proof.

Current median49.667s versus component49.503s is only0.33% with opposite pairwise signs and larger baseline variation. There is NO material speed improvement established. RSS increases consistently by~57MB. Complete-key time medians26.185s /24.445s vary within the runs and do not establish end-to-end gain.

A SEPARATE audit process completed in74.827 solver seconds /80.000 whole-worker seconds, peak RSS829607936bytes. Every one of113178 newly constructed keys AND hash values matched an independent CURRENT constructor with independent serialization/marginal caches; source-cache hits reuse already checked complete keys. Audit full result/Table also matched3487/7200. Audit time is not included in speed medians.

Hash memo counts per non-audit component run:150432 complete component tuples created,452712 hash requests,141116 first structural hash computations,311596 cached hits. This confirms actual reuse, not usefulness: most newly created components still need their first hash, and the final-hash subphase is small.

Evidence: `component-seven-results.json`, `component-seven-summary.json`, `compare_component_seven.py`. Raw worker logs remain in.artifacts/component-seven. Unit preparation7 tests passed0.335s, including full canonical keys/mappings, invalidation, physical/private/profile context, same-marginal correlation negatives and collision-safe equality. No full suite was rerun for this unadopted experiment; production-path860/860 remains distinct.

## New corrected CURRENT-input phase evidence

Two CURRENT-only instrumented readouts also completed with the same full value/Table. The detailed readout took52.629 solver /56.678 worker seconds under the REMAINING59.561-second combined-stage allowance. All stage calculations ended at approximately597.12s of the600-second envelope. No further heavy run was started. These instrumented times are NOT speed comparisons.

Detailed current complete-key phases (seconds):

| Phase | Seconds | Calls |
|---|---:|---:|
| Source identity/component hash lookup |0.482|121693|
| Final full-key structural hash |0.695|113178|
| Canonical constructor TOTAL |25.616|113178|
| └ exact colour/marginal construction |7.267|113178|
| └ colour grouping hash / sorting |1.399 /1.015|792246 /113178|
| └ rules/strategy serialization |1.264|226356|
| └ Board / joint-state signature builds |2.877 /2.378|60148 /90284|
| └ past-record transformation |0.964|691048|
| └ private/physical equality checks |0.207 /0.245|126905 each|
| └ mask mapping |0.220|126735|

The TOTAL includes the indented categories; do not sum it with them. These are timed scopes with instrumentation overhead, not an exhaustive CPU self-profile; roughly7.8s inside canonical construction remains unassigned to these named leaves (cache access, snapshot assembly/comparison and other control work). The earlier instrumented readout also measured final hash0.704s and source hash0.481s. Thus the premise that repeated FINAL tuple hashing explained the25s key cost is not supported. Existing source EvidenceKey and fast-mask caches were already doing useful work.

Evidence: `component-seven-key-phases.json` (first readout), `component-seven-key-phases-v2.json` and process-limit metadata. `profile_key_phases.py` reproduces the detailed readout only when a fresh comparison stage leaves budget; it refuses to manufacture a new600-second allowance.

## Decision and next specific target

Do NOT wire the tuple-hash prototype into normal/local app factories: exactness was established for this input, performance benefit was not, and memory grows. No tuple payload, private information, role weight or history was removed, but a mathematically safe cache can still be a poor optimization.

The strongest named remaining target is the CURRENT exact colour/marginal builder (`exact_renaming.colors`,~6.3–7.3s in the two readouts). It currently revisits every secret hypothesis and adds its mass once for each role bit. A next candidate is exact aggregation by the COMPLETE role tuple before expanding to per-player colour vectors, reusing the existing bounded marginal cache. This is only a proposed preparation step: exact Fraction sums must produce the SAME vectors/canonical keys; the full joint law and secrets still remain in final snapshot equality. Equal role marginals must NEVER become the equality criterion. Small-law overhead and cache invalidation must be tested before another real-case measurement. No such aggregation was implemented in this stage.

All measurement workers ended; dedicated18801 remained untouched. No backend/9-player/latent policy expansion, default enable, push or deployment.