# Board B evaluation and measurement

Targets are fixed Git snapshots: old `ec513c2eb60bd20d5dbfbbe6c29bceb5648ff049`,
B `c6dd47539644c65e83c708b824b7792410c62130`. Product code is not instrumented or
modified. Python and the repository's existing dependencies are required.

Run from the repository root, serially (do not run these commands in parallel):

```powershell
python -B -m unittest tests.test_board_b_benchmark -v
python -B benchmarks/board_b_benchmark.py run --output .artifacts/b-benchmark/final-baseline --repeats 5
python -B benchmarks/board_b_benchmark.py run --output .artifacts/b-benchmark/final-ablation --repeats 3 --select seven,seven-observed --experiment bypass-generated
python -B benchmarks/board_b_diagnostics.py run --output .artifacts/b-benchmark/counts --repeats 1 --diagnostic counts
python -B benchmarks/board_b_diagnostics.py run --output .artifacts/b-benchmark/profile --repeats 1 --select basic,private-history --diagnostic profile
python -B benchmarks/board_b_joint_audit.py run --snapshots .artifacts/b-benchmark/final-baseline/snapshots --output .artifacts/b-benchmark/joint-audit
python -B benchmarks/board_b_cache_control.py run --output .artifacts/b-benchmark/warm-control --repeats 3 --select seven,seven-observed
python -B benchmarks/board_b_cache_audit.py run --snapshots .artifacts/b-benchmark/final-baseline/snapshots --output .artifacts/b-benchmark/cache-audit
python -B benchmarks/board_b_report.py --baseline .artifacts/b-benchmark/final-baseline/summary.json --ablation .artifacts/b-benchmark/final-ablation/summary.json --counts .artifacts/b-benchmark/counts/summary.json --profile .artifacts/b-benchmark/profile/summary.json --cache .artifacts/b-benchmark/cache-audit/summary.json --joint .artifacts/b-benchmark/joint-audit/summary.json --warm-control .artifacts/b-benchmark/warm-control/summary.json --output benchmarks/results/board_b_results.json
```

The runner archives both exact revisions into its output directory, starts one
fresh worker per case/version/repetition and waits for it to exit. Order alternates
AB/BA and case order reverses on odd repetitions. All `werewolf` modules are imported
before the evaluation clock starts. Module setup and process wall times are separate.
Each worker runs one cold computational-cache request and one identical warm request.
Cold is not OS filesystem-cache cold. Background processes are not stopped; system
CPU minus worker CPU is recorded as an approximate background-load estimate. Short
workers have noisy load estimates. All raw observations and a low-background subset
(10% threshold) are retained. No trials are silently removed. No frequency/power or
permissions are changed.

Each timed request prepares a Board and requests public role rates, CO groups/counts,
and the specified public/private evaluation. B reads its already-prepared RoleState
marginals; old computes the corresponding displayed marginals. JSON proof production,
LRU counter inspection and process startup are outside the timed interval. The worker
compares exact Fractions, world candidates, role rates, groups, legal rows, full results,
root public-day tied action distribution and Pending; report validation additionally
uses the pre-existing 7/15,149/324,113/504 and private 5/6 fixtures. The seven-player values are frozen old-version compatibility references, not independent mathematical proofs. A known old bug is
not justified merely by equality. This is API evaluation time, not full HTTP/render time.
Top-level public-day policy is audited; this does not enumerate every future policy
choice in all private information sets.

Budgets remain 250000 work / 20 seconds. Pending/timeouts are censored, never included
as completed runtimes. A 150-second process guard catches a stuck harness; it is not
an increased solver budget. Completed-time medians, ranges and IQR are descriptive,
not general performance guarantees or confidence intervals. Windows process CPU time
may have coarse granularity for millisecond cases.

Diagnostic runs are separate. Counts instrument immutable constructors, normalization
lookup aliases, origin/history reconstruction, solver cache accesses and GC pauses.
Element totals count constructor hypothesis sizes and materialized normalization inputs;
generators are not consumed just to count. Phase times use the active innermost
3a/3b boundary: solver recursion inside replay switches back to 3b; nested cumulative
times are not summed. These are operational boundaries, not a complete semantic
partition of every shared kernel. Diagnostic overhead remains in diagnostic times.
Only complete diagnostics may be compared as complete workloads; censored profiles
are prefixes. cProfile self-time and cumulative time are stored separately. Do not
sum parent and child cumulative times. Peak process working-set/pagefile figures
include imports/proof output and allocator behavior, not just retained Board objects.

The ablation is diagnostic-only: it bypasses generated-Board evidence orchestration,
source/key registration and repeated publication reconstruction while retaining the
same existing projection/evaluation kernels. It removes one architectural layer,
not one mathematical operation. Exact output must still match. It weakens B's
provenance/reconstruction responsibility and is not adopted into product code.
Baseline and ablation are sequential blocks, so temporal confounding remains;
CPU time, load and repeated results help qualify it. It cannot assign separate
causal percentages to hashing versus copying versus replay.

Cache audit mixes base/input/history/strategy/rule/public/private/secret-location
requests in one process, returns to base after each, and compares every response
with a separate fresh worker and the other revision. Incomplete latent-seer support
is compared as Pending, not made into a number. Generated artifacts/snapshots/profiles
stay outside Git; the compact results file retains raw timings and proof digests.

`baseline` and `ablation` without the `final-` prefix are pilot data. Their B harness
redundantly recomputed already-prepared role rates. They are retained for provenance
but excluded from the final performance conclusions. Formal runs use the corrected
harness and matching display outputs.


Warm reuse control (`board_b_cache_control.py`) keeps the same process/input and
routes both revisions through their existing completed-Forecast LRU public facade.
Root role marginal preparation remains native. This explicitly supplies comparable
completed-result reuse eligibility: the native B application currently bypasses it.
The diagnostic B cold miss uses a kernel-input origin rather than the native saved
origin, so its cold times are not substituted for native B or used as a pure cache
causal estimate. Proposed product work is a versioned complete-result cache at B's
own boundary with saved-origin reconstruction preserved on misses, not replacing
the product entrypoint with this diagnostic.

Historical formal raw files expose B role marginals as role/value pairs and old
marginals as dictionaries. The normalizer creates a separate copy, converts only
that representation, recalculates proof digests, and preserves all times/values and
original raw files. The final harness canonicalizes that field outside the timed
interval. Its timed evaluation code is byte-identical to the formal recorded code.
Cache audit includes pending/partial root wolf rows and completed night wolf rows;
it does not call a legal-but-uncomputed row a completed result.


Captured formal data for this run uses `final-baseline-normalized`,
`final-ablation-normalized`, `counts-verified`, `profile-normalized`,
`cache-audit-final-immutable`, `joint-audit`, `warm-control`, and `ablation-counts`.
Rebuilding the captured compact evidence (without recomputing timings):

```powershell
python -B benchmarks/board_b_report.py --baseline .artifacts/b-benchmark/final-baseline-normalized/summary.json --ablation .artifacts/b-benchmark/final-ablation-normalized/summary.json --counts .artifacts/b-benchmark/counts-verified/summary.json --profile .artifacts/b-benchmark/profile-normalized/summary.json --cache .artifacts/b-benchmark/cache-audit-final-immutable/summary.json --joint .artifacts/b-benchmark/joint-audit/summary.json --warm-control .artifacts/b-benchmark/warm-control/summary.json --ablation-counts .artifacts/b-benchmark/ablation-counts/summary.json --output benchmarks/results/board_b_results.json
```

The optional ablation count reproduction is:
`python -B benchmarks/board_b_diagnostics.py run --output .artifacts/b-benchmark/ablation-counts --repeats 1 --select seven --diagnostic counts --experiment bypass-generated`.
Final probes separate eligible event-cache hits/misses from calls that do not perform
lookup. Earlier `counts` raw files used a coarse None-return label and are pilot
material; `counts-verified` replaces them in the final evidence. No old raw file was
rewritten to manufacture a hit rate.
The legacy seven and observed-model seven are different saved inputs, not a
single-model-flag ablation; compare old/new within each case, not their outcomes to
each other as an isolated public-observation effect. Hash seed and CPU frequency
were not pinned; repetitions/load/CPU data qualify the result, not universalize it.

Completion is scoped to the requested outputs: public Forecast includes its
requested final/action/by-dawn metrics and nonempty pending_metrics is incomplete.
The private-history case requests legal scan rows' final values. Its unsupported
seer dawn is compared as None and never claimed computed. Partial legal final
rows are censored. All formal public pending_metrics were empty.
