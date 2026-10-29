# Calculation design policy

- Production code should be the smallest algorithm that computes the defined formulas.
- State mathematical assumptions and reasons for equivalence/symmetry in design documentation.
- Put independent enumeration, counterexamples, named-result comparisons and cold reconstruction checks in development tests.
- Keep external-input validation, zero-support handling, cancellation and work/time limits as separate necessary responsibilities.
- Own immutable inputs and caches per calculation; create internal children only through common generators. Do not put issued ledgers, proof tickets or repeated owner/frame authentication in production loops.
- Reuse common probability, legal-action, configured-policy, Q/P-update and group-splitting operations. Do not add case-specific evaluators.

Start from docs/README.md. Record design decisions and evidence in the current docs (performance work in docs/PERFORMANCE.md). The previous migration ledger docs/archive/20261029/shared-symmetry-transition-plan.md is read-only history.
