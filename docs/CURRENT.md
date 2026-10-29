# Current implementation and non-negotiable boundaries

Evidence snapshot: 2026-10-29, local `f871a7d`; cloud observations below were made 2026-10-27, not rechecked by this documentation-only task.

## Versions are different

| Surface | Verified revision / status |
|---|---|
| Published production | `03e4e31` (v0.5.2); last verified 2026-10-27 |
| Approved Vercel Preview | `4dc7246`, including cancellation fix `0f62a28`; deployment `dpl_2mXuEptCcsB339mSPqxjpGCNYomW`, READY at last check |
| Local checkout at start of cleanup | `f871a7d`: same product code as `4dc7246`, plus local cloud-verification documentation |
| v0.6 | Release candidate / work in progress; NOT published production |

Preview alone enables browser-history and persistent Tree flags in `../wsgi.py` when VERCEL_ENV is preview. Do not promote this branch or assume its flags are production defaults. Local `../dev_previews/run_current_app.py` is a distinct development entrypoint.

## Calculation and navigation

Public information plus explicitly configured shared strategies define exact expectations. Arithmetic is exact rational; percentages are presentation only. No Monte Carlo, silent approximation, branch truncation, or partial value advertised as completed.

The mathematical evaluator and its immutable inputs/caches differ from history occurrences. Current points to an occurrence in the persistent Day1-rooted navigation graph. A reused solver state does not imply two differently mapped or historically different occurrences may be merged. Representative person bijections must transport role assignments and correlated private histories together.

Public policy belief Q and physical/observer-conditioned mass P must remain separate. Observer knowledge must not leak into public action selection. Counts, role worlds, acquisition histories, guard memories, pack/attack knowledge, rules and strategy can distinguish states with identical visible labels. Do not broaden cache equivalence by dropping these distinctions.

Tree consumes evaluator-owned records on migrated paths; legitimate value-only reductions do not promise detailed action tables or all future display nodes. Unported compatibility paths remain explicit. The [migration ledger](shared-symmetry-transition-plan.md) gives per-scope evidence; do not call the whole migration universally complete. Never fabricate unseen action values, tie weights or secret outcomes for display.

Manual public updates are zero-selection-weight history edges: zero excludes them from the original strategy expectation, not from possible evidence. They preserve source values/old continuations. Compatible role assignments retain their prior mass without weighting by rarity of acquiring an observed private report; compatible secret histories are retained and renormalized within the assignment. Automatic strategy-generated branch likelihoods are unchanged.

## Actual UI flow versus design goal

Implemented staged path (`../werewolf/navigation_evaluation.py`, `../static/board_navigation.js`, `../app.py`): validate/adopt a supported Current update, return pending UI, calculate exact role rates, then forecast using the retained calculation owner and install matching results. Contradictory input is not an accepted valid Board. Save success and calculation failure are separate. Occurrence/revision/generation checks reject stale replies. Value completion is not full Tree-detail completion.

Main uses server templates plus panel/content replacement, not a fully normalized client-side canonical Node store. Inputs and Tree state have specific preservation adapters. A universal stable-DOM/Node redesign remains a design direction, not a completed rewrite. Board-displayable phase/update occurrences and choice/chance nodes should not be collapsed into a single mutable numeric cache.

Input calculation has Off / roles / all (default roles); roles returns before future forecast/action/Tree work. Update always performs full validation/adoption/evaluation. Explanations belong in Help > operations > display. [Evidence](input-calculation-three-modes-2026-10-25.md).

## Adopted rule chronology (do not use obsolete numeric oracles)

- The earlier corpse-scan record [corpse-scan-rule-fix](corpse-scan-rule-fix.md) allowed already-dead targets. It is superseded for target legality.
- User correction dated 2026-10-20, implemented `bb3f5b6`: targets must be alive at night start. A target killed later that same night was legal at acquisition; earlier acquired/published results are not erased by later death.
- `898a01a` resolves two omitted stale test contracts by independent Fraction enumeration, without changing production math: information-set example 5/6 versus distinct legacy public-choice measure 7/8; tied wolf action scores 7/10. They are different measures, not interchangeable expectations. [Full proof](v06-numeric-contract-resolution.md).

Supported random hunter semantics do not authorize an invented hunter MAX/mixed policy. Future automatic Day2 CO timing, multiple-hunter semantics and cooperative joint fake-report policies are not newly selected by these docs. Check exact existing scope before extending any family. The roll-skip certificate is conservative, supported-role/QP restricted and forces the approved MAX public execution policy; unsupported cases fall back to ordinary exact evaluation, not approximate victory.

## Storage, hosting and cancellation

Local journals use `../.artifacts/navigation`; preserve them. Preview uses IndexedDB signed reconstruction recipes within one browser origin. Server requests validate/replay recipes with the same evaluator; client probabilities are not trusted. No cross-device sync or tab-closed durable job continuation was promised. Different immutable deployment URLs have different storage; stable branch origin can retain history across deployments. Current app has no wired shared DB requirement; legacy credential names are not permission to connect or migrate data.

`../werewolf/calculation_budget.py`: cooperative 270second / 4,000,000work application limits; `../vercel.json`: 300second function configuration. Reaching a limit means uncomputed, not a settled value. Cancellation registry is process-local. Cloud explicit cancellation stopped one run after 43,463work/7.399422seconds total lifetime; a subsequent disconnected run completed after110.029623seconds. Thus neither fetch abort nor another-worker acknowledgement proves CPU termination. Actual270/300second cloud kill/retry remains unverified.

2026-10-29 communication-failure test was NOT executed: Chrome app-control approval card blur/loop and timeout prevented DevTools access. No offline setting was applied. This is a tool approval/UI blocker, not a demonstrated WW_GG code failure. Page-exit explicit cancellation is a proposal only, not implemented or authorized in the docs task.
