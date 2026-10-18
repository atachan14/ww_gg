# Bounded profile and deferred diagnostic prototype

Investigated code: ee25046 / checkpoint 8122d99. Exactly one independent initial7 cProfile worker ran. Calculation time was capped at 7 seconds, with a 9.8-second hard process guard and 1,500,000,000-byte memory guard; the entire measured worker finished in 7.062 seconds. No 60-second initial trial, second profile, or increased limit was used. Raw evidence: initial-publications-profile.json. cProfile overhead changes traversal progress, so these counts are not a speed comparison with the previous 60-second attempt.

## Findings

The profile sample retained 2,109 source keys, 1,975 unique GeneratedBoard requests, 1,256 scalar values and 3,746 scalar actions. Source requests are distinct from game Boards. Public-equivalent sources may legitimately differ in complete Q history, past reports, P, observer or physical carrier. The 1,645 distinct (Board,Q,past) tuples therefore cannot be merged using the public Board alone.

There is real object duplication within exact values: among source-key references, public Board has 1,626 distinct identities for 245 exact values; Q has 1,504 identities for 805 values; P has 1,896 identities for 1,016 values; physical Board has 1,757 identities for 241 values. board_key_hashes holds 10,946 entries with strong references indexed by identity. Future exact interning could share identical complete immutable objects; marginal-role-only keys would erase correlations and are not an acceptable replacement. This prototype does not change keys or intern objects.

Named publication branches ARE eagerly restored: produce/restore -> public_report_branches constructs named Boards; cached_flow retains the complete vector list; record_publications registers each named public source; morning_value pushes actual P and evaluates every supported publication event. Representative target-action evaluation does not make publication continuations lazy. The sampled 327 publication laws generated 1,043 templates and 1,129 named vectors, so only a modest part of the reached expansion is due to template multiplicity. A true representative-publication value backup would require a continuation-equivariance certificate across Q/P/physical/history, not merely multiply a representative Q weight. It was not implemented here.

Evidence retention is also eager: 15,254 history references point to 1,977 unique operations and 1,874 retained frozen kernels. Frozen-kernel __dict__ storage alone is 2,968,416 shallow bytes, excluding objects referenced by those dictionaries. kernel_snapshot shallow-shares most large caches (it does not deep-copy the whole posterior on each call); it still creates a large engine shell per operation. Shared prefixes already reuse operation objects; history tuples repeat prefix references rather than deep-copying their laws. There is no current proof that snapshots alone dominate the prior 884MB peak.

The selected avoidable retention is branch detail for diagnostics plus terminal resolution memos. The sample retains 3,750 full branch records and 3,260 terminal records. RecordedPolicy and FullRecordedPolicy retain physical/public outcome Boards even for terminal scalar payoffs. board_action_kernels also retains the exact resolved (acquired,outcomes) tuple for all 3,750 resolutions, though a terminal action has no continuation replay. Merely deleting diagnostic lists would leave those same outcomes reachable through the memo cache. This is why the prototype addresses both retention sites for the same recomputable branch detail.

Repository CPU samples show 13,617 Board validations (0.759s cumulative), 7,500 action_outcomes calls (0.847s cumulative), 5,255 replace_worlds calls (0.448s cumulative), and 24,739 evidence_key calls (0.300s cumulative). These nested numbers are not additive. The sample supports a graph of many concrete histories, repeated validated Board construction, exact-law hashing and retained reconstruction/detail objects as contributors. It does not assign precise percentages of the previous 884,477,952-byte peak; no heap census was taken in that terminated process.

## One local prototype

cut_out_deferred_diagnostics.py provides opt-in DeferredInitialEngine and DeferredSmallEngine; no ordinary factory or shared werewolf source was changed. It preserves complete exact scalar keys, Q/P, physical laws, all SavedOrigin requests, inherited certificates and common transition/evaluation flow.

A lightweight ledger stores (Board, full action payload, target, terminal flag), rather than separate eager copies of full/terminal/branch outcome records. Inspecting the diagnostic iterator constructs the exact outcomes with a fresh ordinary kernel and the captured immutable Rules/Strategy. No diagnostic outcome is materialized during value calculation. The original configuration remains authoritative even after changing the live experimental engine configuration.

The resolution memo retains continuing results but does not retain an all-terminal result. A later miss recomputes the unchanged common physical/public law. This is cache eviction, not pruning: every original chance branch still contributes its exact scalar payoff. This is explicitly scoped to UNIFORM/H0. It makes no hunter, MAX or public-dispatch claim. Existing completed evidence and SavedOrigin replay remain in place.

## Local validation

Each case used a separate worker with a 30-second calculation budget, 120-second process guard and 1.5GB memory guard. No full initial value search was run by these cases.

| Case | Full branch records | Terminal records | Resolution memos old -> prototype | Eager diagnostic outcome rows old -> prototype | Independent initial-origin cold reads |
| --- | ---: | ---: | ---: | ---: | ---: |
| 4-player public | 29 | 25 | 16 -> 4 | 32 -> 0 | 15 |
| 5-player public | 152 | 94 | 131 -> 41 | 156 -> 0 | 77 |
| 5-player own wolf | 65 | 39 | 54 -> 16 | 65 -> 0 | 41 |

All three match the eager experimental engine and independent ordinary reference for complete Forecast and Table. Deferred full branch outcomes and terminal masses match eager records exactly when requested. Every generated source was independently reconstructed with an ordinary kernel and a fresh initial SavedOrigin: 133 reads total, preserving complete public/private laws, past and physical carrier. Case wall times were 0.187/0.844/0.422 seconds. Reported process peaks contain all comparison engines and validations, so they cannot establish a per-engine memory reduction.

Twelve focused regression tests passed in 5.353 seconds. They additionally exercise the actual seven-player day3 saved checkpoint without initial value search: identical scalar/action values, identical deferred full branches, no retained terminal resolution memo, no diagnostic materialization during solve, and captured configuration surviving a later live configuration change. Earlier separate-reporter Q/P/history/cold regressions remain passing.

This is a local prototype checkpoint. No initial7 speedup, memory-reduction amount, full completion, or full Table/joint/branch/cold equivalence is claimed. Remaining sources of memory include exact-law identity duplication, all named publication continuations, scalar/proof registries and eager per-evidence engine shells. A subsequent authorized bounded initial measurement would be needed to assess practical effect. Normal UI, HELP, MAX, public edition, servers and deployment remain untouched.