# Final bounded public UI and asset maintenance

## Deduplicated cases (four distinct tests)

- `tests.test_boardlog_ui.BoardLogUITests.test_permanent_boardlog_has_no_forms_or_instructions`: obsolete `data-public-open` expectation. Read-only Log removal was intentional in commit b7aaf6e. Assert section-scoped readonly/no editable controls instead; Table CO entry hook remains present. Bound extraction to the actual closing section rather than including subsequent page content.
- `tests.test_boardlog_ui.BoardLogUITests.test_legacy_baseline_is_not_labeled_simultaneous`: obsolete legacy edit-button expectation. Preserve existing unknown-order text and absence of simultaneous batch ID; assert legacy order marker and no edit button.
- `tests.test_seer_game_rule.SeerGameRuleTests.test_draft_controls_belong_to_separate_inert_form`: separately observed case, not a duplicate. Keep the inert compatibility form, assert Log has no mode/input/select/button controls and Table CO input remains available. Do not restore removed Log entry UI.
- `tests.test_deployment.DeploymentTests.test_public_assets_exist_before_build_and_match_source`: genuine generated-output synchronization defect plus obsolete fixed module list. Build already promises all first-party JS/CSS. Synchronize with existing `build_vercel.build()` and derive expected names from that contract. Keep exact byte equality; add actual rendered-template static HTTP availability and byte-equality test.

## Evidence and limits

Initial read-only hash/size comparison found7 missing modules and7 outdated files in public/static. Added Board navigation, Tree calculation/expansion/layout/viewport, personal navigation and shared probability display modules; copied existing source assets without edits. This includes already-supported private assets because the common build contract copies all first-party assets, not a private-feature expansion. Local Flask serves static source files, while public files are needed before deployment output planning. No external deployment occurred.

Related complete modules `test_boardlog_ui`, `test_seer_game_rule`, `test_deployment`:25/25 passed, final4.592s (first pass5.003s). All18 public JS files pass Node --check. HTTP test creates an isolated test-client game, resolves actual template script/style URLs and requires200 and exact public/source response bytes. It closes file-backed responses. Existing BoardLog tests also exercise publication, edits, draft preservation, revision and invalid duplicate handling. No real-browser visual claim: this pass changed no template/design/sourceJS; HTTP and byte/syntax checks cover the observed defects. Normal18821 server/session unchanged, no restart or saved-data operations.

Three failures from the original81 plus the separately observed UI failure resolved. Accounting after prior6 repairs:9/81 addressed,72 originally reported unresolved, not a fresh full-suite pass. Eight night/API cases remain unchanged. Denied broad tracking normalization remains untouched.

## Stop inventory

- Independent mathematical work: pre-execution scan intervention support, legal coupled7-player synthetic seer/medium fixtures with recomputed posterior, legal unsupported dead-owner-history counterexample (eight cases).
- Remaining original broad clusters: full-state/tracking comparisons, numerical/structural expectations, Pending/conditioning and initial-none fake reports need independent triage; do not normalize away differences.
- Full repository rerun and expensive exact cases remain incomplete; current25-test pass is scoped.
- Product decisions remain deferred: new automatic CO timing, unsupported hunter/MAX combinations or joint fake-report policies. No new cluster started in this pass.
