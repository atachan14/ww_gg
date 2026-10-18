# Initial seven-player uniform: coordinated 60-second attempt

Explicit user authorization extended this one correctness case to 60 seconds per route, a 150-second worker wall limit and 1.5 GB peak working set. This is not a performance comparison. Numerical source/strategy/UI code is unchanged; the dedicated fixture calls the same common _evaluate recursion with the authorized larger budget and existing 1,000,000-work cap. The root remains the six-world/six-hypothesis actual public uniform clone, C3/M1/S1/W2/H0.

Result: **unverified**. No route completed a Forecast.

* Inherited: time budget stop at work 291,337/1,000,000, measured elapsed 60.031 s. Saved route status and counters before starting independent. Value cache 44,169; scalar actions 132,691; branch records 132,695; terminal records 125,724; generated boards 60,864; inherited contexts 42,086. Canonical/CandidateRules/legacy-root calls all zero.
* Independent: interrupted by worker-wide memory watchdog at worker elapsed 93.703 s and peak working set 1,503,817,728 bytes. At interruption: value cache 28,677; scalar actions 87,412; branch records 87,417; terminal records 81,069; generated boards 41,054. Throwing forbidden-call guards were active, but the old watchdog did not serialize their final counters. Independent zero-call status is therefore not reported as a captured measurement.

The watchdog samples every 50 ms, hence the high-water observation is slightly above the 1.5 GB threshold when stopped. Worker exit code 137. The saved inherited result survived the later worker stop; no complete numerical result was discarded. Independent status is normalized from running to unverified/memory_limit in the machine record.

Forecast equality, complete Table/joint equality, branch mass equality and terminal restoration equality are all null/uncompared. No numerical retry or automatic limit increase followed.

## What the resource result does and does not show

The harness retained the incomplete inherited engine in a local variable during the independent route. The memory threshold is therefore a combined-worker observation, not the standalone memory requirement of independent recursion. Both engines retain large value/action/generated-board and diagnostic branch/terminal collections. Do not compare the two partial cache counts as speed evidence: they cover different unfinished portions of the game tree.

Inherited inclusive law_seconds was about 21.59 s, key_seconds 3.88 s and cut_out_seconds 3.55 s. Nested inclusive action_seconds must not be added to wall time. These counters do not isolate the constructor's full-history validation cost. Its two history scans per reconstructed Board remain unchanged, as do world projection/validation and equality costs. Full cost attribution needs separate investigation.

The immediate observed limits are inherited time and accumulated retained memory. After this attempt, only the harness was corrected to release an incomplete engine before starting its peer, save complete scalar/Table output before optional snapshot serialization, retain watchdog counters and use a fresh artifact directory per future run. These bookkeeping corrections were syntax-checked but not numerically rerun. Completed routes, if any in a later authorized attempt, retain Forecast/Table/branch/terminal snapshots before their peer starts.

Machine record: cut-out-user-seven-initial-60-results.json. Original per-route checkpoint/watchdog/log artifacts remain under .artifacts/user-seven-initial-60/. This attempt made no MAX, ordinary UI, external publication or exploration-strategy changes. Return for a new checkpoint before any further full initial exploration or constructor optimization.