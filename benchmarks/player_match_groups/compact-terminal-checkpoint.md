# Local prototype: exact terminal payoffs without eager complete Board children

The approximately95% figure in dc4e595 was198,443 terminal-containing action outcome records divided by208,548 total action outcome records (95.15%). A record qualifies if it contains at least one terminal physical branch. This is not a ratio of states or CPU time, and it does not imply every such record can use the new shortcut. The new hook requires EVERY physical branch to be terminal; any mixed continuing branch retains the ordinary flow.

## Common flow and unchanged winner rules

exact.action_world_groups extracts the existing action_outcomes validation/forced-action/winner partition verbatim, before child Board construction. Both complete outcomes and terminal-only outcomes use this same partition, legal-target rules, exact count-class normalization and existing winner_for. Winner thresholds and early-ending rules were not modified. For H0 standard deaths, only the resulting alive count and live wolf count determine each physical winner; the branch weight is still the exact original P integral, never a replacement Q or independent-role product.

The shared resolve_action accepts an optional policy terminal_outcomes hook ONLY when terminal_payoffs=True. It runs after the original night acquisition and observer-support validation. The default full history path never invokes it. The prototype declines for any physical continuation, hunters/GJ, MAX configuration, custom public/physical resolvers or a custom night resolver. Public-corpse support rejection, legality and terminal-input rejection remain consistent with the previous public kernel. Observed-roster filtering stays in the common flow without renormalizing retained mass.

TerminalFacts holds cheap alive/winner/day/phase/history facts. Explicit materialize(), context or a detailed Board attribute constructs the original complete FlowOutcome using a fresh ordinary kernel and the captured configuration/full action payload. TerminalPolicy.project first materializes before the existing SavedOrigin-backed projection. Complete acquisitions, past reports, attacks, public Q and actual P remain in the source and action ledger; no posterior is promoted into a new authoritative origin. Deferred diagnostics use the existing full unaggregated outcomes and their original saved evidence. Repeated diagnostic opens return identical full contents.

The resolution memo key now includes the optional terminal hook function, so replacing that hook cannot reuse incompatible complete/compact outcomes. A negative regression proves the invalidation rather than relying on cache disablement.

No normal engine factory enables the hook. CompactTerminalSmallEngine and CompactTerminalInitialEngine are explicit experimental classes. Normal UI, HELP, MAX settings and the public edition were not changed. The shared primitives have an optional route and an exact factorization; default behavior was covered by replay and legacy regressions. The initial long runner was not wired to the new class or executed.

## Finite comparisons

Each case ran in a bounded worker:30-second calculation budget,120-second process guard and1.5GB peak guard. The ordinary independent engine, previous deferred engine and compact prototype were compared on complete Forecast (including all action/dawn values) and complete root Table. Every deferred full branch, its public context and physical outcome/mass match the previous deferred engine exactly. Diagnostics were opened repeatedly and fingerprinted identically.

The Board construction counts below are Board.__post_init__ calls during complete Forecast+Table, excluding graph preparation and subsequent diagnostic/cold reads. They demonstrate deferred construction, not measured speedup. Each worker holds comparison engines; its peak memory is not a per-engine performance attribution.

| Case | Board validations: previous deferred -> compact | Compact all-terminal action evaluations | Complete branch records | Terminal-containing records |
| --- | ---: | ---: | ---: | ---: |
| 4-player public | 109 -> 43 | 22 | 29 | 25 |
| 5-player public | 552 -> 340 | 90 | 152 | 94 |
| 5-player medium | 1422 -> 906 | 246 | 300 | 249 |
| 5-player own wolf | 228 -> 136 | 39 | 65 | 39 |
| 6-player/two-night public | 1600 -> 767 | 282 | 524 | 287 |

Each case independently reconstructed three saved source requests and representative terminal requests in both engines with a new ordinary kernel and new initial SavedOrigin:12 cold reads per case,60 total. The cold helper includes stock MediumInstructionEvidence so the medium-publication case is fully replayed rather than dropped. Terminal history requests use terminal_payoffs=False, reconstructing full public/private acquisition and action histories. Terminal public-Q and physical-P role/confirmed-payoff rows were compared using the existing row formatter:12 comparisons per case,60 total. No missing public context was invented for a counterfactual physical terminal event.

Case workers completed in0.219/1.109/1.281/0.516/3.656 seconds. Raw results are compact-terminal-{four,five,medium,own-wolf,six}-results.json. These times include comparison/inspection/cold checks and are not an isolated timing benchmark.

## Negative and regression evidence

42 focused tests passed in three bounded groups (20 new/common-flow/deferred tests;8 existing terminal/guard/followup/saved-recipe tests;14 existing evidence/publication tests). The new cases cover: no child Board construction at scalar terminal day/night; full details only on demand; preserved predeath acquisition and observer failure; P differing from Q; configured self-bite permission and forced weights; continuation fallback; hunter/GJ exclusion; custom physical/night resolver fallback; MAX fallback; illegal actions, already-terminal inputs and invalid rules; Q-zero public corpse rejection; physical terminal payoff without invented public history support; observed-alive filtering; hook-specific cache invalidation; and the saved actual seven-player day3 checkpoint without initial root search.

Only local construction reduction and finite exactness are established. No initial7 long search, full-initial Table/joint/branch/cold comparison, measured initial speedup, adoption in the ordinary path, server restart, push or deployment occurred. The next meaningful step is an authorized isolated fixed-work comparison with this terminal hook enabled/disabled before another full initial attempt.