# Short initial7 retention comparison at a common exploration point

Compared the c393ba0 eager and deferred options on the same actual initial7 UNIFORM input. Four independent processes ran in alternating paired order eager/deferred, deferred/eager. Each process contained one engine, an 8-second calculation budget (including preparation), a 9.7-second internal hard guard, an external 10-second timeout, and a 1,500,000,000-byte guard. Actual process walls were 9.0020, 8.8778, 8.8357 and 8.9677 seconds. No long or complete initial trial was run. All four stopped on the calculation time limit, not an unproved structural guard.

Only diagnostic-outcome retention and terminal-resolution memo retention differed between modes; common actor policy, likelihoods, Q/P/physical transition laws, inherited groups and scalar search were unchanged. Identical lightweight checkpoint instrumentation was applied to both. No diagnostic iterator was opened in the deferred runs (materializations=0).

## Common fixed exploration point

The checkpoint fires immediately after the 3,000th unique scalar action evaluation is completed. In all four workers it had exactly 1,007 completed scalar values and 1,729 generated source keys. The current action's full (Board,Q,past,P,observer,physical,target) is saved in each raw JSON and has the same SHA256 `84cc6b215c9ef57b52ed70d07605e720d20194ef6355a1332314d6b79929062b`. Thus the comparison is at the same reached branch and exploration counts rather than comparing memory solely at a wall timeout.

| Fixed-point measurement | Eager run 1 / run 2 | Deferred run 1 / run 2 |
| --- | ---: | ---: |
| Search time to checkpoint (s) | 2.1870 / 2.3410 | 2.2167 / 2.2495 |
| Peak working set before checkpoint census (MB) | 58.143 / 58.548 | 51.200 / 51.085 |
| Completed values / actions / generated sources | 1007 / 3000 / 1729 | 1007 / 3000 / 1729 |
| Tracked retained Board objects | 7358 / 7358 | 2134 / 2134 |
| Tracked joint laws / joint hypotheses | 2547 / 4737 | 2547 / 4737 |
| Retained full outcome objects / resolution entries | 3004 / 3004 | 392 / 392 |
| Retained expanded diagnostic outcome references | 3004 / 3004 | 0 / 0 |
| Deferred lightweight recipe inputs | 0 / 0 | 3004 / 3004 |
| Identity hash entries | 8892 / 8892 | 8892 / 8892 |
| Unique saved requests / evidence operations / frozen kernels | 1622 / 1624 / 1536 | 1622 / 1624 / 1536 |

The fixed-point peak median falls from 58.345MB to 51.143MB (7.203MB, 12.35%). Time medians are 2.2640s and 2.2331s, with only two samples per mode and overlapping ranges; this is not evidence of a robust speedup. One deferred sample is slower than its eager partner. The Board/outcome reduction is consistent with removal of retained expanded terminal outcomes, while tracked Q/P hypotheses and reconstruction evidence remain present.

Object counts are an identity census of explicitly named engine hash/source keys, resolution/diagnostic outcome containers and source-evidence histories. They are not a whole-heap object count or a complete byte attribution. Census timing is recorded separately; fixed-point time and peak are taken BEFORE the census. Timed-stop counts include that checkpoint instrumentation overhead and must not be used as a throughput benchmark.

## Timed-stop results (unequal search coverage)

| Run | Values | Scalar actions | Generated source keys | Peak at search stop (MB) | Tracked Board / joint law / hypothesis objects |
| --- | ---: | ---: | ---: | ---: | ---: |
| Eager 1 | 3778 | 11248 | 5764 | 125.415 | 27136 / 8896 / 17360 |
| Deferred 1 | 3814 | 11347 | 5831 | 98.750 | 7414 / 8982 / 17577 |
| Deferred 2 | 3814 | 11347 | 5831 | 99.037 | 7414 / 8982 / 17577 |
| Eager 2 | 3659 | 10905 | 5493 | 120.992 | 26267 / 8553 / 16213 |

The timed stops have different state counts, so their memory difference is descriptive rather than a matched-work effect size. Generated source keys are recorded Board requests, not a count of unique Board instances. Cooperative budget ticks stopped at 8.000/8.062/8.031/8.000 seconds; preparation plus final census and shutdown remained inside the external 10-second limit in every case.

No initial Forecast/Table, joint-selection mass comparison, full labelled branch-mass comparison or representative cold validation completed in this short search. The fixed full-Q/P branch match is narrower evidence; whole-initial semantic equality still rests on no completed run. Prior completed finite-case/cold evidence is unchanged and remains separately identified.

Raw evidence: initial7-short-retention-comparison.json and the four initial7-short-{eager,deferred}-{1,2}.json files. Read-only assertions verified all process/memory caps, shared fixed branch fingerprint and state counts, identical tracked Q/P and evidence counts, time-stop status, and zero deferred materializations. No solver/core code, normal UI, HELP, MAX or public edition was changed. The explicit deferred option remains available; no next full initial retry was started. The result supports a memory-retention benefit at matched early work, not a completion or speed promise.