# Initial7 retry after separate-reporter integration

Code under test: ee25046. Exactly one fresh new-route worker ran the same actual initial7 UNIFORM root. The worker enforced a 60-second calculation budget and 1,500,000,000-byte memory limit. The process exited normally after saving an unverified result; it has ended and its engine is no longer retained.

Outcome: time budget exhausted, not a structural guard refusal. Budget elapsed 60.0 seconds, recorded wall elapsed 60.0391658 seconds, work 69,334, peak working set 884,477,952 bytes. This is an incomplete search and supplies no speedup or end-to-end equivalence claim.

Search size: 37,074 cached values, 111,322 scalar actions, 50,908 generated Board sources; 111,326 branch records and 105,337 terminal records. The producer handled 3,484 publication laws, 29,079 pattern representatives, and 29,998 named vectors. These are internal partial-search counts, not validated coverage counts.

The last recorded solve Board was day 3, living 1/2/7, after execute 4, bite 3, execute 5, bite 6, with public world (wolf=18, medium=4, seer=1, hunter=0) at mass 1. Its recorded budget was 59.984 seconds/work 69,294. This Board is a diagnostic snapshot, not a complete minimized failing condition: no new unproved structural condition was encountered before the budget expired. The raw JSON retains this full Board, detailed counters, and the exact budget stop.

Validation completion in THIS retry:

- Initial Forecast and Table: incomplete, no result.
- Joint-selection mass and labelled branch/terminal mass comparison: not reached.
- Representative independent cold validation: not reached.
- Old independent reference worker: not run, because completion of the new worker was its explicit prerequisite.

The separate local ee25046 validation remains separate evidence: ten tests and 49 initial-origin cold reads; it does not establish full initial equivalence. No further initial attempt was made, and no ordinary UI, HELP, MAX, public-edition, or solver code was modified for this retry. No new tests were needed for this results-only checkpoint.

Raw evidence: initial-publications-separate-new-trial.json. Reproduction uses cut_out_initial_publications.run('new', a fresh output path); re-running is a new full trial and requires a subsequent task instruction.