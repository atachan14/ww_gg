# Default-OFF future computation sharing prototype

`benchmarks/player_match_groups/future_reuse.py` is a local numerical experiment, not connected to normal app dispatch. No production solver file changed. The original independent path is the OFF comparator. Every complete comparison includes exact Fraction terminal value and every legacy Table row.

The first useful duplication was missing complete canonical continuation keys for two live seer claimants without a hunter. The existing general full key route was gated on hunter presence; the reduced single-seer route did not cover this state. Enabling the existing complete key before scalar/action recursion avoids generating repeated subtrees. This is different from grouping already computed audit values.

A separate exact physical kernel cache removes repeated `action_outcomes` calls for the same full frozen Board/target/rules/strategy even when private histories differ. It never merges same-marginal/different-joint Boards. Day raw casualties share this kernel; night public observations retain their original count-conditioning law.

The guarded scope is random day/night/fake reports, unvisited/uniform true scans, uniform or noncontradictory/uniform fake reports, no medium or hunter, public entry with no opaque observer. It includes two live seer claimants, the existing single-claimant size gap and projected retired-seer states with at most five alive. Existing max and external private evaluation fall back. Memoization and exact-renaming disable switches are respected.

Key construction became a measurable cost. The local fast adapter replaces only the exact bit permutation mask summation with an equivalent lowest-bit recurrence, uses bounded completed-mask caching and recent completed serialization caching. It checks the original implementation text before adapting it. This is deliberately a benchmark adapter; a production implementation would require a normal explicit helper refactor. Compact evidence keys retain the complete value for equality, including hash collisions. No cached partial values or partial work budgets become a terminal answer.

Reproduce: `python -m unittest tests.test_future_reuse tests.test_exact_renaming tests.test_certificate_renaming`. Run numerical comparisons with `python -m benchmarks.player_match_groups.measure_future_reuse 6 2` and the same command with `--enabled --physical --retired --compact --fast-parts`. Trials have a 30-second calculation budget and 1.5GB cancellation guard. Numerical trials run sequentially.

Committed `future-reuse-final-results.json` records final source SHA256, exact values/Tables, expansions, kernel/key counters, timing and process peak memory. Earlier `future-reuse-results.json` and `future-reuse-kernel-matrix.json` describe earlier staged flags, not the final adapter.

Seven-player two-wolf same-white two-CO trials remain pending at 30 seconds. The final fast-key trial reached 8,263 action expansions /3,009 value expansions with 823 physical kernel computations, 8.599 seconds canonical-key time and about 292.5MB peak. That is improved throughput, not a complete seven-player win rate or Table. No further 600-second checkpoint extension was used. The existing independent partial checkpoint reference remains unchanged. Medium/max heavy targets and general history coverage remain open in `matching-groups-completion-checklist.md`.

A further candidate is retirement provenance: projection drops the initial publication ledger, potentially reintroducing known fake report noise. The current experiment does not change that behavior; safe elimination would need a retained proof of the already initialized public law and independent validation, rather than treating all zero-seer Boards as initialized.

Final sequential complete comparisons (single paired measurement, not a stable speed guarantee):

| Players/wolves | OFF seconds | ON seconds | OFF/ON actions | ON kernel computations | ON key seconds | ON peak MiB |
|---|---:|---:|---:|---:|---:|---:|
| 5/1 | 0.818 | 0.411 | 1961/269 | 69 | 0.229 | 59.1 |
| 6/1 | 8.042 | 1.257 | 14958/690 | 136 | 0.678 | 142.8 |
| 6/2 | 4.787 | 0.696 | 6316/475 | 235 | 0.289 | 146.1 |
