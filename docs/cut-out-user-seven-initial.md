# Coordinated initial seven-player uniform comparison

Target: f68d873's actual saved7 C3/M1/S1/W2/H0 public input, with only policy.day/night/fake_reports changed from max to random. Initial source retains six worlds and six hypotheses. Morishi's browser measurement had ended and this one-case comparison was explicitly authorized.

Result: **unverified**, not a successful comparison.

| Route | Result | Elapsed |
| --- | --- | --- |
| Issued inherited | common flow pending: inherited_publication_or_CO_transition_unproved | 0.235 s |
| Old independent labelled recursion | comparison evaluation budget exhausted | 5.000 s |

Worker elapsed 5.282 s, peak working set 119,083,008 bytes. Enforced limits: each evaluation 5 s, worker 30 s, memory 1.5 GB; outer subprocess timeout 31 s. No limit increase or numerical retry was performed.

Forecast equality, Table/joint equality, physical branch mass comparison and terminal readback comparison remain null/unverified because neither route completed. Monitored canonical, CandidateRules and legacy-root calls were all zero during both attempted routes. Zero calls alone do not establish numerical correctness.

The inherited route exposes a previously untraversed publication/CO proof boundary. Its precise failing transition has not yet been diagnosed. The independent route needs separate budget/load consideration; its timeout does not establish a wrong result. Neither issue was masked by a fallback or uniform fill.

The first harness setup failed before any evaluation because comparison_game returns (original, uniform_clone). The harness now selects the clone explicitly, matching the existing preparation path. That pre-evaluation setup failure is retained in .artifacts/user-seven-initial-setup-failure.log. The one actual numerical case is recorded in cut-out-user-seven-initial-results.json, with path progress in .artifacts/user-seven-initial-comparison.log.

Run command: python -B -m benchmarks.player_match_groups.cut_out_user_seven_initial_fixture. This is an explicit coordinated benchmark entry, not a normal UI route. Initial max and the public version remain unchanged. No speed measurement was performed.