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

## Coordinated rerun after f4551d4 / audit 2eac553

Morishi's UI comparison had completed and the same one-case comparison was explicitly reauthorized. Tested HEAD: 2eac553ff8bc6dcc7fe0730ba4464748cfb074e0, including the f4551d4 publication proof repair. Source remains exactly the same six-world/six-hypothesis public uniform clone. No source/strategy/UI change was made for this run.

Result remains **unverified**: both inherited and old independent routes returned comparison evaluation budget exhausted under the unchanged five-second calculation budgets. Measured route elapsed times were 5.140 s inherited and 5.000 s independent; the inherited elapsed value includes budget exception unwind/return overhead, so it should not be described as a strict five-second wall completion. The worker wall watchdog remained thirty seconds and peak-working-set watchdog 1.5 GB. Actual worker elapsed: 10.187 s; peak: 124,805,120 bytes.

Forecast, Table/joint, branch mass and terminal restoration equality remain null/uncompared. The previous publication guard error did not recur within this attempt's evaluated portion, but completion of every initial continuation is still unproved. Monitored canonical, CandidateRules and legacy-root calls remained zero in both attempted routes.

The Board constructor's two full-history validation passes remain an explicit per-reconstruction cost, along with the supplied-world projection/validation and full equality check documented in cut-out-seven-publication-audit.md. They were not optimized in this run. Neither a speed comparison nor a successful full-forecast comparison can be inferred from these time-limited attempts. No automatic budget increase or further numerical retry was performed. The machine-readable initial result now records this latest attempt; the earlier result remains in commit ac87c55.
