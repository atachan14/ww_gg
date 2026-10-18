# 4/5-player information-set max comparison

This comparison-only entry connects the proven cut-out action representatives to the existing `InformationSetForecast.solve`. Ordinary factories and UI remain unchanged. `adapt_max_model_a` is explicit: W1/S1/H0/M0 or1, 4 or5 original players, seer1 CO, initial random-white report1→3, all other CO latent, full configured disclosure, random fake reports. Day is max; night is random or existing max. Initial support is at most9 and seer1 must have probability1. Seven-player max, latent-seer max, hunters/GJ and new CO/report policies remain outside scope.

Day choices maximize continuation values using the PUBLIC joint distribution. Ties remain uniform. A viewer's role/results condition evaluation, never the public action choice. Wolf choices use the public distribution conditioned on the wolf's own roster and attack history; the viewer's unknown-to-wolf role is not passed to policy selection. Existing night max minimizes village continuation values. The both-max case retains this existing sequential convention; it does not implement a new simultaneous mutual optimum/equilibrium.

The same `act` cut-out implementation is used for all continuation scores. Its exact key includes public and private joint state, observer, physical Board and past; groups refine public observations and explicitly owned information. Public Q, viewer law and physical branch mass remain separate. Full labelled reference uses the original solve with every labelled action evaluated. No per-world best-action mixture is introduced.

## Independent small-game values

With five players and public wolf candidates2/4/5, their execution wins immediately with probability1/3. After a miss, random night choices yield subsequent public day values1/2 (seer dies),5/6 (known white dies),1 (other candidate dies), average7/9. Thus a candidate execution scores1/3+2/3×7/9=23/27. Executing seer1 scores4/9 and known-white3 scores2/3. With existing night max, the wolf kills the seer after a miss, giving candidate value2/3; seer/white executions score1/3. The public optimal policy is uniformly2/4/5.

A private medium2 viewer has candidate2 score7/9 and4/5 score8/9 under random night, or1/2 and3/4 under max night. The shared public policy still gives23/27 or2/3, respectively. A per-viewer or per-world optimizer would incorrectly choose the larger value. Unknown medium identities remain three equally weighted possibilities in each five-player wolf information set, including when the viewer knows medium2.

Four players have public candidates2/4, each scoring1/2; other executions score0. Medium2 privately knows wolf4, but evaluation of the public tie remains1/2 rather than private best1. Night choices in this case tie at village value0 and stay uniform.

## Verification and limits

Run `python -B -m benchmarks.player_match_groups.cut_out_max_fixture`. Each fresh worker is limited to60 seconds, evaluation to25 seconds and Windows WorkingSet to1,500,000,000 bytes; the complete driver is capped at300 seconds. Evidence: `benchmarks/player_match_groups/cut-out-max-results.json`.

Six finite comparisons cover4/5, M0/1, public/private medium, day max with random/max night. They compare complete public formatted Table with primary/cumulative values, conditional private execution Table, every root action and dawn value, all encountered scalar contexts, wolf policy distributions, terminal branch probabilities, complete public/private joint distributions, acquired results, attack/death histories, physical Boards and SavedOrigin readback. Private execution rows are not an ability/scan-choice intervention Table. Existing42 regressions are retained, plus2 max regressions. The evidence reports measured cost rather than a general speed guarantee. Full project suite, normal UI adoption, general max information sets and hunter cycles remain separate work.

Final run: six comparisons plus44 regressions completed in34.422 seconds. Individual audited cases took0.064–0.827 seconds, peak WorkingSet27.8–34.8 MiB; terminal labelled readbacks14–252 per case. These timings include reference evaluation and terminal replay. No full project suite was run for this prototype change.
