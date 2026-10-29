# ww_gg documentation / AI handoff

Updated 2026-10-29 against local HEAD `f871a7d`. This index describes evidence in this checkout; it is not authorization to publish or change rules.

## Start here

1. [Current implementation and invariants](CURRENT.md): what exists, mathematical boundaries, public versus local/Preview.
2. [Run, test, and release handoff](HANDOFF.md): setup, bounded checks, release gates and protected data.
3. [Document catalogue](CATALOG.md): every pre-existing top-level document, grouped for discovery. Plans and dated reports are not automatically current specifications.
4. [Original user requirements](requirements.md): requirement history; its v0.3 status and deferred Tree statements are historical, not the current implementation inventory.

## Primary records by purpose

| Purpose | Read |
|---|---|
| Exact model, information ownership and policy | [CO grouping](co-group-model.md), [candidate policy coherence](candidate-policy-coherence.md), [simultaneous actions](simultaneous-action-design.md), [ownership review](information-ownership-cache-and-extension.md) |
| Current flow adoption / roles / win stages | [Implemented staged evaluation](staged-navigation-evaluation-2026-10-26.md), [three input modes](input-calculation-three-modes-2026-10-25.md) |
| Tree records, migration scopes and compatibility | [Transition migration ledger](shared-symmetry-transition-plan.md), [model review](current-model-structure-review.md) |
| Correct numerical rules | [Night-start target rule and independent proof](v06-numeric-contract-resolution.md); see CURRENT for chronology |
| Public Preview and browser-owned history | [Prototype](browser-history-prototype-2026-10-27.md), [private restoration](browser-history-private-cold-acceptance-2026-10-27.md), [latest cloud acceptance](fixed-preview-acceptance-2026-10-27.md) |
| Cancellation and failure boundaries | [Transport cancellation](calculation-cancellation-2026-10-24.md), [local failure/retry](browser-history-ui-followup-2026-10-27.md), [cloud positive and negative results](fixed-preview-acceptance-2026-10-27.md) |
| Formal local workspace / rollback | [Repos relocation](repos-migration-2026-10-27.md) |
| Historical failures and bounded verification | [Repository verification](repository-verification-2026-10-24.md), [remaining night comparisons](remaining-night-fixture-triage-2026-10-24.md), [numeric resolution](v06-numeric-contract-resolution.md) |

## Reading status safely

- **Current** means verified implementation described in CURRENT, with an explicit scope; it does not mean every strategy/observer/role combination is supported.
- **Proposal / investigation** is not an adopted user rule. Never implement a rule merely because a design document suggests it.
- **Dated evidence** records a particular commit, fixture and environment. A test count or timing is not a current full-suite result.
- **Historical / superseded** records remain accessible for their rationale. Later explicit user decisions take precedence; preserve conflicting evidence rather than silently rewriting it.

No documents were deleted or moved in this cleanup. The 233 pre-existing top-level files include substantial numerical/prototype evidence; an index and explicit supersession notices avoid breaking their numerous cross-links. Untracked `previews/` and `v0.6-release-audit-draft.md` are pre-existing work, not adopted or published by this cleanup.
