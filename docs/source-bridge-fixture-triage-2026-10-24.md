# Bounded failure triage and legal source-bridge fixture repair

## Counts and confidence

The saved broad pass contains62 assertion failures and19 errors (81 real case IDs). Initial runner import failures8 and13 module resource-limit events are separate, not added to81. Symptoms were provisionally partitioned: strict source/cold comparison10; numeric/structural expectations46; night-start eligibility/retired scan helper11; Pending/removed API/conditioning6; source-bridge registry3; initial-none fake-report semantics2; public UI/assets3. This is not a blanket root-cause verdict.

This unit confirms and repairs the source-bridge3 as stale INVALID TEST INPUT, not a removed API.78 original cases remain unresolved. No recent production regression is confirmed by this unit; that does not rule regressions out. An absent scan_target_players import also predatesff7cf69, but was not repaired here. Tracking evidence is limited to docs/tracking-evidence-2026-10-24.md; the denied broad fixture normalization remains unexecuted and off limits.

## Concrete reproducer and before/after

The legacy shared fixture executes2 on Day1 and bites3 that night, then reports seer1 scanned2 for Day2. The night-start roster is independently1,3,4,5,6:2 was already executed. Current setup() returns InvalidatedBranch('Scan target must be another player alive at night start'); the bridge subsequently returns source_bridge_registry_required. Repeating with day2_target=4 returns a valid registry and SourceWitness. The SAME rejection/acceptance occurs with werewolf sources loaded from pre-maintenanceff7cf69 via git archive in a fresh process. Reproduce: `python -X utf8 dev_previews/audit_tracking_equivalence.py --bridge` and `--baseline ff7cf69 --bridge`. Evidence:.artifacts/source-bridge-current.log and source-bridge-pre-maintenance.log.

Changes are limited to benchmark/test fixtures: setup gains an explicit day2_target keyword, retaining its original default for unexamined callers. Only audit_source/audit_edits/audit_rejections request legal4. Their corresponding own scan is4; edit/cancel/redo is4->5->withdraw->4. Both4 and5 were alive and unvisited at the relevant night start. No win-rate constants or numerical expectations were changed. All original complete public/private laws, Tables, reference comparisons, cold reconstruction, zero old-grouping calls, witness invalidation, unknown-owner/revision and Q-only substitution assertions remain verbatim. The source-bridge API itself, all production code and broad closed-tree assertions are unchanged. Other SixInputRegistry callers still using invalid default2 are separate future maintenance, not silently rewritten here.

## Verification

- Original three cases plus two independent legality/source tests plus four saved research tests:9/9 pass in3.710s. The original three previously all stopped at source_bridge_registry_required.
- Additional public/role/history regression:76 executed,75 pass,1 failure in15.323s. NOT a full passing suite.
- The additional failure is SeerGameRuleTests.test_draft_controls_belong_to_separate_inert_form, expecting the old data-public-mode form hook. It reproduces in an isolated process without source-bridge imports (0.391s) and production/UI files are unchanged. It is left unresolved, not weakened to fit output. Logs:.artifacts/source-bridge-cluster-regression.log and source-bridge-ui-isolation.events.jsonl.
- New legality checks prove rejection is preserved for2, admission for4, public history exactly(2,3), normalized yet distinct Q/P, immutable original inputs and complete source binding. Same-night victim3 remains in the independently computed start roster; no game-rule change.
- Broad closed_full_tree_fixture is unchanged from14a5dbf (verified git diff/canonical-newline comparison). The rejected operation was never retried through any other tool or worker.

## Next finite priorities

1. Apply the same independent chronology check to remaining dead-target fixtures individually; keep literal numerical/joint reference assertions and verify legal replacements with common-kernel plus independent evidence.
2. Diagnose public UI markup tests at actual component boundaries and inspect the generated public/static asset mismatch. These are separate from this repair; do not blindly delete assertions.
3. Extend ONLY isolated tracking evidence with retained-history and information-set counterexamples. No existing broad comparison or production normalization is authorized by the current limited proof.
4. Initial-none fake past reports, cooperative fake-report policies and unsupported strategy families require their own rule/strategy decisions; do not infer those decisions from failing tests.

Research artifacts are commit ee1a557. Normal local server remains14a5dbf/PID18904; no restart is necessary for these test-only changes. No private-view feature expansion, external publication, push, new credentials or saved-data deletion.
