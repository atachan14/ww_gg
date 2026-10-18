# Inherited candidate groups for the existing max comparison

The four/five-player first-night max comparison now uses an inherited public group context instead of reconstructing candidate equivalence with the legacy canonical matcher. This changes candidate grouping only; every legal candidate still receives its existing exact strategy value evaluation.

## Construction and boundary

`ModelAInitialGroups.start()` supplies the constructed product of symmetric player blocks. `RecordedPolicy.project` records the genuine common `ActionEvidence` child. The child context fixes the newly observed execution target in the parent blocks. Candidate equivalence is then the orbit of the ordered wolf/attack-target pair: its two block indices and equality flag. No permutation enumeration, law-row comparison, or canonical search is relocated into context creation or update.

Contexts bind the complete public Board, state and past; their exact dictionary keys/equality protect cache/source identity, rather than discover a group. Only the existing four/five-player, one-wolf, one-seer, no-guardian, first-night comparison shapes are admitted. A missing or mismatched inherited context remains Pending/unsupported. There is no runtime legacy fallback and no scope expansion.

The context belongs to the public candidate policy. Private value evaluation still uses its own conditioned law and the existing observer point fixes, including a future scan target. Other players' private observations do not enter public policy selection. Rule/strategy inputs, joint state weights and candidate replacement distributions are retained.

## What remains

The no-read proof still evaluates every legal candidate using fresh exact evaluators and rejects an actual profile read. The white-joint complete-support check still inspects support. This change removes legacy group matching from these runtime probes; it does not eliminate candidate-value proof cost or make all descendant groups incremental. The explicit `legacy_reference` option is used only by diagnostic old-oracle/read-control fixtures, never as a runtime fallback.

## Finite verification

`cut_out_candidate_context_fixture` executes five bounded cases and focused regression patterns. During actual evaluation it replaces both legacy canonical entry points and the legacy CandidateRules constructor with failing mocks, and checks their actual call counts are zero. Afterward an explicitly separate old oracle compares candidate equivalence, complete action maps and candidate profile replacements, including active-report contexts.

Existing reference fixtures compare complete Tables, joint/terminal branch masses and private conditioning, including initial-white, medium report ties/cold recipes and own scan interventions. A boundary case checks unsupported missing context and that the future private scan target stays fixed. See `benchmarks/player_match_groups/cut-out-candidate-context-results.json` for measured results. Timing is a bounded correctness observation, not a before/after speed claim. The 62-case aggregate and full project suite are intentionally outside this focused run.

Final focused run: five cases plus eight unit regressions passed in 54.594 seconds; maximum case worker 22.485 seconds and peak WorkingSet below 103 MB. The active-five case includes 29 cold candidate recipes and six private-posterior witnesses. Complete-support initial-white contexts also match the explicit old candidate oracle. No broad aggregate or server action ran.

Subsequent recursive-group checkpoint: [cut-out-inherited-groups.md](cut-out-inherited-groups.md) replaces the four/five-player descendant root/history rebuild described under remaining work above. Candidate value evaluation and white-support validation still remain.
