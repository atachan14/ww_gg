# Finite checkpoint audit for dual-white matching

The retained runtime is 135c796/2f6ae27: only five/six-player uniform dual-CO same-white grouping, default OFF. This tooling does not enable seven-player production grouping. It creates provisional matching engines only inside isolated audit workers.

## Exact decomposition

Root phase is daytime and configured day/night/fake-medium policies are random; no hunter. Other strategies, including max, are rejected rather than replaced. For root intervention t, the existing action_flow gives physical outcomes o with mass q(o). A terminal contributes q(o) times its exact payoff. Otherwise the unchanged policy.project and continuation_context produce the night public/private/physical carriers. Existing wolf_information_groups gives information groups I with mass m(I); the unchanged wolf_policy gives bite probabilities pi(b|I).

V(t) = terminal/known-shortcut contribution + sum_o,I,b q(o) * m(I) * pi(b|I) * act(public, private_I, fixed_bite, physical_I).

Each checkpoint holds one fixed root intervention and next bite, retaining every information group and original coefficient. There is no normalization within a bite partition and no per-world optimization. Coefficients plus terminal/shortcut masses must sum exactly to one. Private information, physical branch base and public beliefs remain distinct carriers. Existing horizon_for_action supplies the independent dawn metric. The final random-day value is the arithmetic mean of all complete root intervention values; final Table assembly uses the original row builder.

## Persistence and limits

Original actual-input game snapshots are saved in .artifacts/player-match-checkpoints/inputs. Cache namespace keys include exact original input, engine/source content hashes, numerical worker version and decomposition contract. Every completed record has a numeric checksum; input/engine/root/bite/mode must match on reuse. Workers check source fingerprints before and after computation. Recalculation under changed input/source uses a new namespace. No engine heap/pickle is persisted.

Only exact completed components are reused. Pending units retain any completed horizon and primitive terms but never become action=0, complete forecast, or complete Table. Previously incomplete attempts are not automatically rerun. A persisted active-time meter prevents restarting a trial with a fresh 600-second allowance. Workers have a 120-second ceiling and a 1,500,000,000-byte high-water threshold (working set and process commit), cooperative cancellation on existing budget ticks, and parent watchdog termination. Parent terminates at the deadline; only an already fully completed record may survive process cleanup. Normal runtime still has no independent oracle.

Completed root/intervention values were not saved by the old 300-second monolithic attempt; only counters existed, so no numerical prefix can be recovered from it. The new trial does not rerun that monolithic scalar calculation. New split components are saved as they complete.

## Small-case acceptance

Root-only decomposition first matched complete five/six-player forecasts and cache reuse. The finer day-target/next-bite decomposition also matched saved actual-input ungrouped complete Tables and final values:

| Cast | Independent verified units | Complete roots | Final value | Active wall seconds |
|---|---:|---:|---|---:|
| 5/1 | 18 | 5 | 7/15 | 16.922 |
| 6/2 | 30 | 6 | 1/12 | 36.031 |

All units compare root physical outcome laws, full joint-input signatures, information/strategy coefficients, dawn values, every primitive scalar and weighted contribution. Matching workers additionally retain the existing full original-member transport/mass/terminal audit. Repeating each case reused all completed records. Tests cover missing-intervention pending semantics, max rejection, memory cancellation preserving an exact horizon without a final value, and stale-engine rejection: 4 tests passed in 0.183s.

A small-case first attempt encountered a transient Windows sharing error while reading an atomically replaced progress file. Reading the same path immediately succeeded. Bounded same-path read/write retries and worker-side completion checksums were added; no permission/configuration or alternative-path bypass was used. The corrected source namespace passed full small-case verification.

Reproduce small acceptance: python benchmarks/player_match_groups/verify_deep_checkpoints.py.
Run the finite seven-player trial: python -m benchmarks.player_match_groups.deep_checkpoint --players 7 --wolves 2 --total 600.
Do not delete or reset its meter to extend the authorized trial. Complete seven-player equivalence remains unproved until every required oracle/audit unit and aggregate match.
