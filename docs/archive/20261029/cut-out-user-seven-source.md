# Seven-player / two-wolf issued source adapter

Checkpoint after ac76eb1. This is a local, explicit uniform adapter, not a normal UI route. The actual saved input comes from `actual-seven-max-results.json.game`: C3/M1/S1/W2/H0, P1/P2 seer CO with initial white P4, P3 medium CO. Only the three configured max policies are changed to random for comparison. All other input fields and initial batches are retained.

`cut_out_user_seven_source.py` supplies a typed seven-player baseline and a separate issued witness ledger. A witness binds the registry identity, SavedOrigin, owner lineage, input revision, complete public/private/physical source, and inherited group contexts. A copied, stale, cross-origin or one-carrier substitute cannot authorize evaluation. The adapter has no legacy-root fallback.

Initial preparation retains six worlds/six secret hypotheses and groups `{1,2}/{3}/{4}/{5,6,7}`. Replay keeps public Q, private P, the two-bit initial wolf roster and physical attack branches distinct. The first-night fixture demonstrates Q != P inside the saved night and checks cold replays and both carrier permutation laws.

Subsequent same-owner simultaneous seer reports preserve P1/P2 together when acquisition/publication day, target and color agree. Provenance is required: an otherwise identical single-report origin conservatively fixes its reporter. Asymmetric edits also split. No canonical recovery or merging of an existing proof is attempted; cancel/reinput issues a fresh trace. Medium Board snapshots retain only the current day's rows, while earlier evidence remains bound through the saved log and parent contexts.

## Bounded validation

The synthetic first night adds execution P7, attack P6, then simultaneous Day2 P1/P2 white P7 and P3 medium white P7. A separate synthetic tiny endgame adds execution P5, attack P4, then simultaneous Day3 P1/P2 black P5 and P3 medium black P5. These are validation timelines, not additional observations from the user's saved game.

Only sources with at most three living players can run value evaluation. At the synthetic endgame, public village win is 1/3; actions P1/P2/P3 are 1/2, 1/2, 0. P1's own seer evidence gives action values 0, 1, 0. Public/own results and complete Table joint masses match the explicit official labelled reference. Two attacks and the original two-wolf roster remain present.

The fixture also checks one-sided edits, legal cancellation/reinput, identical information from distinct report provenance, stale owner/revision, copied witnesses, substituted Q/P, max policy and CO changes. A contradictory withdrawal is deliberately refused: after P1 changes its report on known-wolf P5 to white, removing P2's report leaves no consistent true seer under the configured full-report rule. No uniform fill is introduced.

Run: `python -B -m benchmarks.player_match_groups.cut_out_user_seven_source_fixture`.

Recorded results: four isolated cases plus eight relevant unit tests, all passing; 8.922 seconds overall; maximum worker peak working set 36,855,808 bytes. Limits: 30 seconds per worker, 90 seconds overall, 1.5 GB peak working set. Prefix work called neither solve nor action-value evaluation. Monitored canonical, CandidateRules and legacy-root calls were zero. Results are in `cut-out-user-seven-source-results.json` and local test output in `.artifacts/user-seven-source-light.log`.

## Remaining scope and expected load

Initial max and the normal UI are unchanged. Full seven-player Forecast is explicitly disabled, including the five-player first-night source. No initial full Forecast, long benchmark or speed comparison was run. The earlier six-player inherited path's measured 7–8% slowdown versus the old root remains the available performance result; this checkpoint makes no speed claim.

The connected root has six hypotheses/four groups; the synthetic first-night and endgame sources each have two hypotheses. Tiny value checks have at most three live action targets and terminal children. The first-night bridge reads one literal action observation without evaluating its continuation. Full seven-player continuation load remains unmeasured and can grow through future true/fake reports. Any later measurement should begin with one explicitly selected case under the existing 60-second / 1.5-GB cap, with the proposed target and estimated scope reported before execution.