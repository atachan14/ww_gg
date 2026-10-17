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


Fresh-process reproducibility: `python -m benchmarks.player_match_groups.repeat_future_reuse` runs AB/BA/AB with one new Python interpreter per trial, no checkpoint import and a newly constructed solver. `future-reuse-fresh-results.json` contains all six raw complete Tables/counters/source hashes. All three pairs match exactly. OFF times were 3.397/3.540/3.490 seconds; ON 0.879/0.717/0.745 seconds (medians 3.490/0.745, about 4.68x). Every OFF trial expanded 6,316 actions and computed 9,068 physical kernels; every ON trial expanded 475 and computed 235. The ON per-solver source-key cache had exactly 32 hits each time. This is within-run memoization, not inherited interprocess warm state. Process start and preparation are separately included in `wall_seconds`.


The next seven-player trial uses the exact committed audit game rather than a newly generated session. Its Board, complete acquisition state, public report tuple, rules and strategy match a newly generated fixture; the view scope has session-specific metadata, so that metadata is not asserted identical. The saved game's digest and the frozen production/oracle engine hash match the prior assessment. `future-reuse-seven-attempt.json` records the 120.072-second pending result: 13,919 action /4,949 value expansions, 1,326 physical kernel computations, 56.806 seconds key construction and 709,701,632 bytes peak working set. This did not complete a whole forecast, and prior partial checkpoint values cannot establish all Table rows.

Retirement diagnostic: in the five-player one-wolf two-CO case, executing P1 has a mass-1/2 branch leaving exposed fake P2 alive. Before projection `can_retire_scans` is true and the actual initial white reports exist. Projection reduces seers to zero and empties `past`; the same predicate then becomes false. The old path regenerates 48 day-1/day-2 report vectors whose total mass is one and whose complete role posteriors are all unchanged. `retirement_probe.py` records this without modifying the solver.

`retirement_proof.py` is a separate default-OFF experiment: when the original predicate already proves retirement and the public random/no-medium/no-hunter guard holds, retain the actual observed `past` tuple at the existing solver-only projection boundary. Do not invent an initial fake law, change saved/replayed Boards or erase private acquisition evidence. The original predicate can then still verify the initial report, and its existing uninformative-publication retirement applies. Unknown initial histories, external private entries, trace, max and unsupported policies do not opt in. This is an attempt at payoff-preserving noise marginalization, not a claimed correction to previous win rates.

Initial retirement-proof comparisons: complete exact value and every Table row agree with the independent OFF solver for 5/1, 6/1 and 6/2. OFF/ON times were 0.820/0.094, 8.195/0.491 and 4.108/0.741 seconds. No value difference has been found; these timings are single pairs. New guard/diagnostic tests plus the previous future-key/renaming tests passed: 23 tests in 18.641 seconds. Seven-player validation is recorded separately, and the overall completion checklist remains open.


Seven-player retirement-proof result: complete in 11.391 seconds, 170,397,696 bytes peak working set. Overall village payoff 8/35; root interventions P1/P2 =3/10 each, P3 =2/15, P4-P7 =13/60 each. Every Table row was produced. This is numerical completion of the prototype, not yet equality against an entirely unmodified complete original forecast.

`validate_retirement_primitives.py` recomputes all 98 complete original oracle primitives in 4.302 seconds. It verifies frozen engine and input digests, each original full night plan, stored primitive checksum/weight/signature, and equality of complete public/private/physical inputs. At the validated retirement boundary the only adapted component is the actual original initial public history retained where the old projection emptied it. All 98 exact values match. It does not import uncomputed primitive values or reset old audit work meters.

The labelled reference with only the same retirement retention (canonical/physical/fast/compact sharing all OFF) remained pending at 89.993 seconds, 175,450 action /56,824 value expansions and 1,093,206,016 bytes peak working set. `exact_value_and_table_equal` is null because the reference did not complete; this is not a numerical mismatch.


The labelled reference with physical-kernel caching alone also remained pending at 59.999 seconds /146,176 actions /47,265 values /652,632,064 bytes peak. These finite failed reference runs were not extended.

A separate independent acceptance reference (`uniform_count_reference.py`) now validates the completed seven-player result. Under the explicitly checked random/no-medium/no-hunter/no-self-bite fixture, future decisions do not use report contents. Summing normalized true/fake observation kernels therefore leaves the terminal recurrence on living-player and wolf counts: a random vote removes a wolf with w/n; a non-self random wolf bite removes a villager. Root interventions are evaluated using the actual complete public wolf distribution, not equal per-player wolf marginals. From the initial 7/2 state neither the vote nor the next bite can reach terminal parity, so all by-dawn probabilities are independently zero. The reference's full values and by-dawn metrics are supplied to the same presentation adapter; every resulting Table row and terminal payoff agrees exactly. This count reference is acceptance-only, guarded to this fixture, and never fills Pending results or changes application behavior. It does not validate max, medium, hunter or unspecified fake joint laws. It is distinct from a completed entirely unmodified old-engine run, which remains unavailable.

Final targeted validation: 24 tests passed in 18.819 seconds, including independent seven-player count-reference equality and assertions that existing max comparisons actually complete. Frozen app/production/original audit source diff against e8b8d42 is empty. No application dispatch/default, server process, push or deployment changed.
