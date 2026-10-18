# Exact immutable joint sharing: bounded audit and local prototype

Conclusion: exact sharing is possible, but this candidate did NOT produce a large structural improvement. At matched3000 actions the peak working-set median fell about1.194MB (2.3%), while search time rose about13.1%. The prototype remains disabled by default and was not connected to the initial long runner or ordinary UI. No long initial search was run.

## One bounded observation and snapshot audit

One compact-terminal initial7 worker stopped at3000 completed unique scalar actions:1007 completed values and1729 generated source keys. Exact identity versus COMPLETE value counts were:

| Retained component in the observation | Objects | Complete distinct values |
| --- | ---: | ---: |
| TrueScanState law containers | 2547 | 966 |
| Hypothesis objects | 4737 | 1821 |
| Hypothesis tuples | 2547 | 713 |
| Acquisition records | 2868 | 18 |
| WolfAttack records | 2673 | 9 |

There are37 role-marginal groups containing different complete laws; one role marginal corresponds to523 distinct complete laws. Thus marginal-role equality is insufficient for canonicalization. Full mass, role coupling, acquisitions, guards, attacks and law metadata must remain available.

The source recipes retain1536 proof kernel snapshots. Their __dict__ storage alone is2,433,024 shallow bytes. Forty-seven fields already point to the exact same objects across these snapshots (including the large memo/proof registries); kernel_snapshot does not deep-copy all those caches. Seven fields vary: action_policy, active_morning, board_sources, last_board, last_context, last_usage and terminal_compact_actions. The snapshots are mutable engine shells with per-event/replay state, not immutable values that can safely be merged by an abbreviated configuration key. They were not merged or removed. The observation reports shallow sizes and selected retained structures, not a whole-heap byte attribution; it does not establish that these categories alone account for most of the previous1.184GB peak.

Raw observation: immutable-joint-observation.json. The scan itself was bounded to eight seconds of calculation and a9.7-second process guard,1.5GB; it reached the finite checkpoint without initial completion.

## Selected candidate: weak, owner-scoped complete-value interning

joint_value_sharing provides an explicit share_joint_values(owner) context. It shares validated immutable Acquisition/GuardIntent/WolfAttack records and complete Hypothesis values. The key contains all four role masks, exact Fraction mass and every ordered private record. Python equality compares the complete immutable tuple, including under a deliberately tested hash collision; no digest-only or marginal-only identity is used.

All ordinary law validation runs BEFORE any sharing. Hypothesis record references are canonicalized only during construction of a new object, with equal immutable values; existing published inputs are not mutated. TrueScanState containers are never interned. Their rosters, initial_rule, tracked owners, observed_prefix and derived caches remain separate, so identical hypothesis entries do not collapse different law/observation contexts.

The context is isolated per evaluation owner and binds its immutable BoardData identity. Replacing owner.data (including an input/revision replacement) refuses further pool use. Complete immutable values carry no permission or owner authority; source containers, SavedOrigin, issued certificates and per-event proof snapshots retain their original checks. Separate/nested scopes do not share a global namespace. Weak-value indices do not keep discarded hypotheses or records alive; closing the scope clears all indices and releases owner/data references. Mutable and noncanonical joint inputs are not interned. Default constructors have no active pool and retain existing value behavior.

Only two small optional constructor hooks were added: record canonicalization after Hypothesis validation, and complete-hypothesis canonicalization after TrueScanState validation. No normalized weights, missing histories, actor choices, observations or legal moves were changed. Sharing is not enabled by any normal factory or UI setting.

## Local complete comparisons and negatives

Five bounded finite workers (4-player public,5-player public,5-player medium,5-player own wolf,6-player two-night) compared the independent ordinary engine, compact-terminal baseline and the same compact engine with sharing enabled. Complete Forecast/action/dawn values, complete root Table, full public-Q/physical-P branches and repeated diagnostics match. Each case includes12 independent source/terminal cold readbacks with sharing explicitly disabled and a new ordinary kernel/SavedOrigin:60 reads total. Cold hypotheses were checked not to borrow warm hypothesis instances. Terminal Q/P display-row comparisons also match60 times. Worker calculation/process/memory caps were30s/120s/1.5GB; the slowest complete case was3.25 seconds. Per-case process peaks contain comparison engines and are not a per-engine memory benchmark.

48 targeted tests passed:6 new sharing tests plus20 terminal/common/deferred regressions,8 existing terminal/guard/saved-recipe regressions,14 evidence/publication regressions. New negatives cover identical role/seer marginals with DIFFERENT joint coupling, distinct attacks/scans/guards/mass, distinct law metadata, an actual hash collision, owner/data replacement, nested owners, frozen mutation attempts, mutable/noncanonical inputs, weak release of discarded values and independent-cold masking. Historical compact-terminal test result files were preserved; this task's rerun records use immutable-joint-tests-*.json.

## Matched initial7 observation of the prototype

Four independent workers ran OFF/ON, ON/OFF. Both use the same compact-terminal engine and stop immediately at3000 completed unique actions. Each has an8-second calculation cap,10-second external timeout and1.5GB guard. All completed the checkpoint in under four seconds process wall. Full reached Q/P context and every completed partial value/action memo fingerprint match; both have1007 values,3000 actions and1729 source keys.

| Measurement | OFF run1 / run2 | ON run1 / run2 |
| --- | ---: | ---: |
| Search time to checkpoint (s) | 1.911581 / 1.877911 | 2.040748 / 2.244704 |
| Peak BEFORE census/fingerprints, with active indices included (MB) | 51.569 / 51.716 | 50.434 / 50.463 |
| Tracked joint law objects | 2547 / 2547 | 2547 / 2547 |
| Complete hypothesis objects | 4737 / 4737 | 1824 / 1824 |
| Acquisition objects (18 distinct values) | 2868 / 2868 | 22 / 22 |
| Attack objects (9 distinct values) | 2673 / 2673 | 9 / 9 |
| Proof snapshot objects / shallow dictionary bytes | 1536 / 2433024 | 1536 / 2433024 |

A few initial immutable inputs are created before the opt-in scope and deliberately left untouched, explaining1824 objects for1821 complete hypothesis values and22 acquisitions for18 values. Law-container count, source/evidence/proof counts and exact value sets are unchanged. Before scope close the weak indices have27 record values and1818 hypothesis values; after close indices are empty and owner/data released. Shared immutable values remain alive only through their actual retained inputs.

Peak medians are51.642368MB OFF and50.448384MB ON (2.3% lower). Search medians are1.894746s and2.142726s (13.1% higher). These are two short paired samples, not a general performance estimate. Post-census peaks are recorded separately and MUST NOT be used as solver-memory effect sizes because census allocations differ with object counts.

The result reduces redundant immutable objects but does not solve the larger retention structure. Snapshot engine-shell storage, full law containers and the existing source/hash/memo graph remain. Sharing whole mutable snapshot engines would weaken their isolation, so this task does not attempt that. No significant structural gain or whole-initial speed/completion claim is justified; the candidate stays an opt-in research path. Normal UI, HELP, MAX, external public edition, servers and deployment were not changed.