# v0.6 numerical comparison resolution (2026-10-27)

The two numerical failures are stale **corpse-target** expectations, not a newly chosen rule. No production evaluator was changed.

## Chronology

- c3d3163 allowed original-player corpse targets; 573dad4 changed the two test expectations for that rule (legacy5/6, information-set7/9, tied wolf scores2/3).
- bb3f5b6 (2026-10-21 local time) explicitly superseded it after the user correction recorded under "2026-10-20 User correction: seer targets are alive at night start" in shared-symmetry-transition-plan.md. Executed/previously dead targets are illegal, same-night casualties remain legal. The source and other131focused checks were updated, but these two tests were omitted.
- Current seer_future_uniform.candidates and private_adapter.private_slots implement that later rule. Do not revert them to satisfy a pre-correction oracle.

## Independent first example: two distinct measures

After executing fake1, alive2,3,4,5; true seer2 previously saw3white; wolf4or5 each1/2. Unvisited night-start scan domain is4/5, not dead1. Acquisitions happen before casualties; only surviving2 publishes.

Physical information-set night: each world attacks one of its three nonwolf living targets uniformly. Bite2 has combined mass1/3 and leaves a1/2 optimal final execution; bite3 has mass1/3 and all scans resolve4/5; uncertain citizen4/5 deaths have combined mass1/3 and identify the remaining wolf. Value=(1/2+1+1)/3=5/6.

Legacy PUBLIC-choice compatibility forecast: the public random instruction chooses2/3/4/5 each1/4, and then reweights the public prior to exclude the selected non-self-bite corpse. It is intentionally not the wolf-information-set law. Values are1/2,1,1,1, giving7/8. A separate12leaf Fraction enumeration groups actual public corpse/report observations and picks the maximum posterior execution mass under each measure. Both complete laws sum to1; no production transition/posterior/evaluator helper is used.

## Independent second example: wolf scores7/10

After execution7, alive1..6. True seers1/2 are public in both role worlds; wolves are3/4 or4/5. Consider attacking either seer. The surviving seer has five uniform first-scan targets. Targets3or5 distinguish the two role worlds (2/5), proving victory with two remaining executions. Targets dead-this-night seer, knownwolf4, or knowncitizen6 leave ambiguity (3/5).

In the ambiguous continuation, executing knownwolf4 is safe. On the four-person night the wolf can bite the remaining seer before publication, achieving final execution success1/2; the public can always execute one of the equiprobable3/5, giving the matching lower bound1/2. Hence score=2/5+3/5*1/2=7/10 for both seer attacks. The obsolete2/3 used the six-target domain including already executed7. The original policy tie and observed payoff3/4 checks are retained.

## Changes and checks

Only tests/test_information_set_model_a.py's two numerical contracts and their superseded comment/name changed; production numerical code and other expectations unchanged. Independent oracle module tests/test_model_a_night_oracles.py contains no production imports. All13tests pass in2.764seconds across the two oracle tests, complete ModelATests class and night-start-target regressions. Log:.artifacts/v06-numeric-contracts.log.

The private_slots and trace-owner assertions identified by the prior audit were not edited in this unit. The audit's two numerical release holds are now resolved by chronology and independent proof, not by fitting expectations to output. The separate hosted Tree/storage/jobs blockers remain.
