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

## Seven-player first measurement window

The authorized first window stopped at 600.143 seconds including watchdog termination and final record writes. The longest measured chunk wall time was 120.124 seconds including termination; its computation was cut at the 120-second deadline. No automatic extension or retry occurred. Maximum worker high-water across working set/process commit was 613,826,560 bytes, below the 1,500,000,000-byte threshold. This is a per-worker measured bound, not a claim that a completed full solver uses that memory. The old monolithic run had reached 3.56GB without completing.

Out of 42 planned (day target, next bite) units, 15 ungrouped oracle units and 14 matching-plus-independent-audit units completed. Fourteen pairs matched exactly. Root interventions P1 and P2 are fully checked, with exact village value 3/10 each and matching dawn/root joint laws. Global forecast.value and forecast.table remain None/pending. There is no completed seven-player Table or final overall win certificate.

Unit (3,4)'s oracle completed, but its audit reached the chunk deadline. Three of its six original wolf-information group primitives were completed and exactly matched to the oracle: each has coefficient 1/32 and conditional value 2/15. These do not complete that unit or root. Unit (3,5)'s oracle then reached the remaining overall window with no complete primitive. No missing contribution is filled with zero. The other units remain unattempted. Full plan, partial records and meter remain in .artifacts/player-match-checkpoints/2b40cf9e423c2680c229613fcec6e0baa27d492cc4c9a7c94b3095faccc5ba18.

Committed export: checkpoint-seven-assessment.json includes fingerprints, unit values/coefficients, checksums, completion states, exact completed root values and partial primitive matches. checkpoint-seven-input.json preserves the original actual-input snapshot. Exporting verifies already computed checksums/prefix equalities only; it does not run further continuation evaluation after the ceiling.

A safe next numerical unit is the individual original wolf-information group inside a pending (root,bite) unit. The complete 14 pairs and the three completed primitive matches must be retained; a subsequent authorized refinement should evaluate only missing primitives and preserve the same coefficients/full conditioning. No further numerical run was started here. The seven-player dual-CO runtime guard remains fallback. Medium/max scopes were not expanded during this checkpoint task, keeping the cached engine version stable.

## Original-information-group refinement

The separately authorized follow-up is documented in docs/player-match-primitive-audit.md. It reused the old confirmed work, added 24 exact values within one new 600-second window, and reached 95/240 verified primitive expectations. Full seven-player win/Table remain pending and no same-form extension was automatically repeated.
