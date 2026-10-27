# Fixed Preview acceptance, 2026-10-27

## Single authorized deployment

User opened actual Chrome Usage after the prior login blocker. Team Hobby, aggregate Last30Days snapshot: FluidCPU50m15s/4h, memory2.9/360GB-Hrs; projectCPU47m10s. No upgrade/add-on/payment/key/SSO action. Snapshot is not a quota reservation. Remote Preview branch fast-forwarded65c5fa7 to4dc72466141dfa162b382a209481a834324d6f04. Vercel Git integration automatically created exactly one deployment; no manual create/redeploy API call.

Deployment dpl_2mXuEptCcsB339mSPqxjpGCNYomW, sourcegit, targetnull, READY. URL https://ww-e3wwekwb1-aklius14pg-8355s-projects.vercel.app/. Stablebranch https://ww-gg-git-preview-v06-browser-54993f-aklius14pg-8355s-projects.vercel.app/ automatically routed. Productionmaster remains03e4e31f965247da65a62386b8f38863459b5cc1. SSO all_except_custom_domains unchanged. Includes0f62a28 cancellation transport classification and4dc7246 personal cold-generation repair. No user journals uploaded.

## Actual cloud UI verified

Synthetic5players citizen3/seer1/wolf1: initial46.67% (7/15), CO1seer withDay1white2 Update66.67% (2/3), choose execution3, nightCurrent50%. Seer observer1 completed (runtime private_view104work/.019503seconds); reload restored Day1night and personalNavigation1, scope占い師1の視点, publicOverview50%. This is an ordinary complete restore; the deliberately overlapping old-failure/new-selection race remains deterministic local JS coverage, not cloud fault-injected proof.

Stablebranch origin retained earlier syntheticcitizen4/wolf1 Player1wolfCO revision1 and100%/0% with original46.67% root/manual0weightbranch after new deployment reload. No browser storage copied across origins.

Later explicitly reset five-player case: incomplete seer report showed roles and uncomputed win values; filling target2white and Update completed66.67%/33.33%, reload same. This is correction of incomplete input, NOT a forced cloud forecast exception or platform timeout. No real cloud270/300second deadline test was run; existing local fault-injection failure/deadline/retry evidence remains the applicable evidence for those UI branches. Do not mark cloud failure/timeout/retry acceptance complete.

## Cancellation success and negative result

Heavy7players citizen3/medium1/seer1/wolf2, CO1/2seer bothwhite3, CO3medium. While adopted calculation running, editingPlayer4villager changed Main to paused and kept win rates uncomputed. Runtime ownerrequest bnszp-1793099708868-3e7378b7636b stoppedcancelled at11:15:16.712UTC,43463work,7.399422seconds total compute lifetime,peak109.734MiB. Cancelrequests at11:15:08.171 and11:15:16.711 returned200; the latter and ownerstop are nearly coincident, but browseraction-to-stop latency and exact worker identity were not independently captured. Duplicate budgetline under cancelrequest is not a second computation.

Important negative follow-through: cancelling the draft re-enabled calculation; then navigatingTOP disconnected that restarted request. It nevertheless ran to completion: request ld4d7-1793099773688-3b95953ec117,591913work,110.029623seconds,peak610.293MiB,stopcomplete at11:18:04.075UTC. No further heavy retry started. Both known heavy requests have terminal log evidence. Explicit cancellation can work; ordinary disconnect is demonstrably not guaranteed to stop Python cloud CPU. Process-local CalculationJobs cannot guarantee cross-worker cancellation. We did not infer worker identity merely from differing VercelrequestIDs or regions. Native Node-only supportsCancellation was not added to Python.

## Remaining release limits and next decision

- Actual270second application deadline/300second Vercel termination and resulting UI/retry: unverified, deliberately not forced just to consume budget.
- Cross-worker CPU cancellation: no guarantee; requires a separate design decision if mandatory (shared cancellation signal or an execution host with reliable disconnect semantics). Current result-discard protects UI but is not CPUstop.
- Cloud injected recoverable forecast failure/retry and overlapping cold-restore race: not tested here. Local29Python/24JS checks and real local fault-injection browser evidence documented in browser-history-ui-followup-2026-10-27.md.
- No extra deployment authorized or performed after this single Git-triggered deployment. Further infrastructure/access/payment/deploy changes need explicit scope.

Normal18821 was not restarted.121saved journal hashes checked unchanged. Unrelated untracked documents/artifacts retained. UI proof .artifacts/cloud-fixed-preview-20261027.png and cloud-cancel-20261027.png. No performance improvement claimed from these cloud durations.
