# Alternating isolated comparison and explicit memory option

Code tested for the retention comparison: 414f4d2. Three finite cases were completed: 4-player public, 5-player with two medium claimants, and explicit 6-player/two-night with two medium claimants. Each mode had its own fresh process containing exactly one evaluation engine. Each case ran four paired rounds in alternating order: eager/deferred, deferred/eager, eager/deferred, deferred/eager. All 24 workers completed, each under 30 seconds of calculation, 120 seconds process wall, and 1,500,000,000 bytes. The slowest complete case was below four seconds. There was no initial7 value search, profile rerun, limit increase or incomplete case substitution.

Every worker includes startup imports, identical prior/graph preparation, complete Forecast (all original-player action and dawn values), complete Table, and three deterministic representative saved requests cold-reconstructed using a fresh ordinary kernel and initial SavedOrigin. It then opens all full-branch, terminal and branch diagnostics once and again. The output rows are streamed to full-content SHA256 fingerprints rather than retained as another duplicate list. This avoids measuring simultaneous eager and deferred engines or a comparison-only retained diagnostic tree.

For each case, root Q/P, Forecast, complete Table, representative cold Q/P/history/physical carriers, and all diagnostic contents match across all eight workers. The first and repeated diagnostic opens also match in each worker. There are 72 representative cold reads across the 24 workers; this is representative validation, not all-terminal cold enumeration. Prior exact in-process equality tests remain independent evidence.

## Medians across four fresh workers per mode

Times include startup and preprocessing. Memory is the process peak working set at the stated endpoint, in decimal MB. These are small finite workloads and are not estimates of initial7 runtime or memory.

| Case | Result + Table + cold, eager / deferred (s) | Peak through cold, eager / deferred (MB) | Through first diagnostic open (s) | Through repeated open (s) | Peak through repeated open (MB) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 4-player | 0.3749 / 0.3691 | 32.762 / 32.705 | 0.4024 / 0.4106 | 0.4295 / 0.4515 | 32.969 / 32.885 |
| 5-player medium | 0.4998 / 0.4964 | 34.744 / 34.132 | 0.7466 / 0.8199 | 0.9896 / 1.1404 | 35.230 / 34.796 |
| 6-player medium | 0.8588 / 0.8639 | 41.159 / 38.803 | 1.9153 / 2.3166 | 2.9722 / 3.7599 | 42.138 / 40.178 |

The 4-player memory ranges overlap and do not establish a useful effect. For 5-player medium, peak-through-cold ranges are eager 34.714-34.820MB versus deferred 33.948-34.251MB. For 6-player medium, they are 41.046-41.193MB versus 38.625-38.912MB. The latter is a stable median reduction of 2.355MB (5.72%), retained after repeated diagnostic opens at a 1.960MB median difference. Repeated-open total time is 26.5% higher in the six-player case. This is a reproducible memory/time tradeoff, not a general speed improvement. Detailed diagnostics are recomputed on every open, so repeated openings preserve content without retaining the expanded outcome tree.

The six-player case has identical 451 scalar values, 1,103 actions, 860 source keys, 1,149 full branch records and 751 terminal records in both modes; retained resolution memos decrease from 1,122 to 374. Thus the measured change does not come from pruning the state search. Five-player medium retains 29 rather than 275 resolution memos while preserving all 300 full branch records when opened. Raw per-phase times, min/max ranges, process-wall measurements, peaks and complete fingerprints are in deferred-diagnostics-alternating-results.json.

## Adoption and next bounded step

Adopted as an explicit memory-saving choice in the experimental initial trial entry: run(kind='new', diagnostics='deferred') / CLI `python -m benchmarks.player_match_groups.cut_out_initial_publications new deferred`. The eager default is retained because opening diagnostics repeatedly is slower. The deferred option writes a distinct initial-publications-new-deferred-trial.json by default and records diagnostics='deferred' in every saved row. Invalid modes are rejected; the independent reference cannot silently use the deferred engine. No new trial was executed by adding this selector. No normal UI, HELP, MAX, public edition or shared werewolf code changed.

Thirteen focused regression tests passed in 5.436 seconds, including no-search checks for the explicit selector, rejection of unknown modes/reference fallback, the actual saved day3 state, captured configuration, Q/P correlation and fresh SavedOrigin replay.

The next useful experiment would be an explicitly authorized short initial7 eager/deferred pair (for example 10 seconds each, separate workers, same caps) to see whether the stable memory effect transfers to the W2 initial distribution. The current finite evidence gives no reason to predict a substantial win-rate calculation speedup or completion within 60 seconds. No such initial7 pair or long retry was run in this task.