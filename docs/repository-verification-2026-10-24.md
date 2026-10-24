# Bounded repository verification — 2026-10-24

Production baseline:14a5dbf. Standard documented commands are `python -m unittest discover -s tests -v` and JavaScript checks. This pass did NOT complete that monolithic command: it discovered1632 entries without import errors, normalized duplicate import aliases to1616 unique logical cases, and ran isolated modules sequentially under finite limits. Counts are coverage evidence, not an all-green release claim.

## Results

- JavaScript: all56 tests passed, zero skips/failures,0.465s (`node --test tests/*.test.cjs`).
- Python:834 logical cases completed:753success,62assertion failures,19errors.782 IDs remain incomplete/unattempted.13 modules hit case/setup/module/global time limits; these events are NOT classified as mathematical failures. A stopped test may have a later verified result, explicitly annotated.
- Bounded segments: first540.72s/125modules, HTTP180.83s/23modules, explicit expensive enumeration90.53s/7modules, import recovery36.86s/8modules. No parallel CPU test workers; only one test child at a time. Case/setup limits15/20/40s for heuristic fast/HTTP/exact tiers, module limits60/90/120s. Tier classification is heuristic: older benchmark helpers can hide expensive recursion.
- Full exact IDs/outcomes/exclusions/limits are committed in `repository-verification-2026-10-24.json`. Detailed traces, per-module start/finish events and logs remain in `.artifacts/repository-*` and `.artifacts/repository-coverage.json`.

The runner initially used endTest instead of unittest's stopTest, so early children emitted start/finished but no end events. Actual tests ran; reconciliation infers completion only on the next sequential start or an explicit suite finish and checks testsRun against start count. No expectedFailure decorators exist in this checkout. Future children use stopTest. The initial isolated import path also lacked tests/:8 modules were rechecked with the standard discover path and all41 cases executed (35success,2failures,4errors); those product/test failures are retained. These runner issues are disclosed rather than counted as product regressions.

## Independently confirmed maintenance fix

`test_closed_calculation.ClosedCalculationTests.test_input_and_owner_validation_support_errors_and_bounds_remain` still expected eight players to raise unsupported Pending and launched an expensive search to establish it. Count generalization already admits3–9. It now checks eight-player admission and normalized Q/P masses, then uses calculation_budget(1) to verify resource exhaustion separately. The SAME remaining owner/private-input checks remain; targeted test passed twice, final0.062s. No production evaluator or private-view feature changed. The whole ClosedCalculation module is not claimed passing.

## Representative unresolved failure

The closed-full-tree fixture fails BEFORE forecast/terminal enumeration at `a.read()==b.read()==cold`. A bounded initial-state diagnostic showed identical public board, physical board, public reports and observer, but unequal secret-law containers; visible metadata includes tracked=None vs tracked=(1,). This is not proof of a wrong win rate or proof the metadata may be discarded. Do not change assertions to compare scalar values only. Exact hypothesis/actor-visible future equivalence must be established before changing the cold oracle or source comparison. See `.artifacts/cold-source-bounded.log` and `benchmarks/player_match_groups/{closed_full_tree_fixture,cut_out_compact_terminal_fixture}.py`.

## Next work, finite priority

1. Safe maintenance: align obsolete count/admission tests and test import conventions with established contracts, one failing group at a time with independent oracles. Do not blanket-update expected results. Repair cold-source comparator/fixture only after proving the significance of tracked/history fields, retaining full Q/P coupling.
2. Safe tooling: use measured durations to classify old benchmark-backed tests; isolate their JSON output. This pass observed tests overwrite4 tracked benchmark reference JSONs and create5 new outputs. All generated evidence was preserved in `.artifacts/repository-generated-backup/`; original tracked bytes were restored from14a5dbf. No user game saves were deleted. See `.artifacts/repository-generated-restoration.json`.
3. Verification debt: resume the exact excluded IDs from the committed JSON after failure groups are understood; run integration and expensive cases in budgeted slices. Fresh end-to-end browser suites were not rerun in this pass because no production/UI behavior changed; prior14a5dbf browser evidence is historical, not counted as a fresh pass.
4. Design decisions remain separate: root-policy combinations outside root_policy_supported, root_guard_policy_dependency_cycle, multiple_fake_report_correlation_unselected and automatic future-CO timing. They are not authorization to invent hunter/mixed or joint fake-report semantics. Individual/private-view expansion remains deferred.

Normal18821 server stayed on14a5dbf/PID18904 throughout. No restart, remote push/deploy, new credentials or saved-data deletion. A test-only maintenance commit does not require local runtime replacement.
