# Seer GameRule/UI verification (unpublished)

Base production is 7a81348f3490389544feeaf619f008a144d06963 (SystemLog). This separate worktree has not been committed, staged or pushed. Future-seer prototype files are in another worktree and are not included.

TOP hides the calculation-mode selector. Casts with seers automatically use the existing manual model; non-seer games retain their ordinary solver. Valid older explicit manual sessions remain supported. The role label keeps the manual-only scope. Report handling is fixed to truth-compatibility conditioning with constant fake likelihood; it is no longer a selection in the strategy pane.

Initial seer acquisition is now a Rules field: normal / random_white / none. TOP > Rules > Village > Seer edits it. MAIN displays it readonly. Sample rule presets expand the actual default random_white value, independent of cast presets. Starting a game stores the concrete rule; changing preset definitions cannot rewrite a saved game. Back preserves the game's rule snapshot. MAIN strategy requests cannot change this rule.

Normal supports true white/black results. Random-white excludes true assignments for an initial black report, without a blanket input prohibition. None excludes true assignments for every supplied initial result; fake claims can remain possible. Inputs inconsistent with all assignments still reject atomically. Report acquisition/publication timing, future generation, and fake generation policy are separate concepts.

Legacy missing/unselected likelihood migrates to fixed compatibility; missing/unselected initial rule defaults random_white; valid selected old initial rules and action snapshots are preserved. Missing mode in seer casts is migrated without invented seer results. Unknown modes and inconsistent saved rule snapshots are rejected. Non-seer numerical values remain unchanged.

SystemLog draft controls now belong to a separate inert form, so Enter within draft fields cannot submit the main progression form. Browser QA explicitly checks no revision/history change during Enter operations.

All 174 tests pass. Actual Edge native keyboard/mouse input verifies all three rule choices, TOP-only editing, absent mode/likelihood selectors, black report acceptance, sample preset reset, old missing-mode migration, non-seer 7/15, and draft Enter isolation. See seer-rule-ui-results.json and D:/CodexTemp/ww_gg-seer-rule-ui-qa-20261012.
