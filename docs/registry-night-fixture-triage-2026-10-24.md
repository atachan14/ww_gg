# Registry night-start fixture subcluster

Scope: three cases in `tests/test_cut_out_six_registry.py`: current-result/root-CO roundtrip, own complete table/lazy branch, and medium reports/complete table. No production code or running server changed.

## Independent contract

Execution precedes night targeting; a simultaneous bite does not make its victim ineligible for that night. In the first two cases execution2 and bite3 leave night-start players1,3,4,5,6. Initial scan3 was already visited. The original Day2 scan2 was illegal. Use scan5, preserving the correction to scan4: wolf4 has positive compatible private mass before that correction and zero after it. Thus the old-actor invalidation assertion still tests a real change. Undo, redo and root restoration use the same legal scan5. Foreign-owner rejection now starts from a valid registry rather than passing vacuously.

The medium fixture executes5 and bites6. Both medium reports must still concern5. Only the seer report changes from already-dead5 to simultaneous-victim6. Existing complete forecast/Table, primary/cumulative, public reports, past history and unit branch-mass assertions remain unchanged. No bulk target replacement or numerical expectation adjustment.

## Verification

- Three original cases: 3/3 pass, 3.904s (`.artifacts/night-fixture-registry-three.log`).
- Two independent chronology/support checks plus existing legal-target, four bounded tracking research and three source-bridge checks: 11/11 pass, 2.854s (`.artifacts/night-fixture-related.log`).
- Existing dead-target rejection evidence remains in `test_source_bridge_night_targets`; prior ff7cf69 comparison documented in source-bridge triage already established the same night-start rule before maintenance. No new full baseline suite run.
- Numerical and complete-state assertions retained. Denied broad tracking-normalization operation not retried; `closed_full_tree_fixture.py` unchanged.

Accounting: resolves3 of the provisional11-case night-start/old-API group, leaving8 unexamined in that group. Together with the previous3 source-bridge repairs,6 of the original81 reported failures are addressed;75 remain unresolved, not reclassified as passed. The separately observed UI form assertion remains unresolved. No full-suite or browser pass claimed because this change only repairs development fixtures. Stop at this coherent subcluster.
