# Seven-player matching scope experiment

Base: a49b428. Default remains OFF. The proposed Stage 1 changes only the root eligibility pair: (7,1). Recursive grouping still requires at most five survivors. No search-cap increase (120 candidate mappings), policy change, or production UI connection.

## Complete root and recursive guard inventory

| Guard | Heavy seven-player target | Stage 1 |
|---|---|---|
| Explicit opt-in; public view, claims and alive IDs agree | Normal UI does not opt in | Unchanged |
| Root cast pairs 5/1, 6/1, 6/2 | Seven players, two wolves | Proposed 7/1 only; withheld after audit timeout |
| Day 1 daytime, everybody alive, no Board/past history | Matches target | Unchanged |
| Hunter 0, medium 0, seer 1 | Medium 1 | Still fallback |
| Exactly one certain true seer claimant | Two competing seer claimants | Still fallback |
| Claims only seer/latent | Includes medium CO | Still fallback |
| Initial scan rule none in rules and state | Random-white initial result | Still fallback |
| Self bite disabled in rules and policy | Matches target | Unchanged |
| One initial roster matching alive IDs | Must be checked on conditioned target state | Unchanged |
| No acquired secrets, guards or attacks | Initial scan secrets exist | Still fallback |
| Exactly comb(n-1,wolves) distinct role hypotheses | Conditioned joint distribution differs | Still fallback |
| Every hypothesis has equal mass | Public reports condition the joint distribution | Still fallback |
| Day, night and fake-medium report policy random | Configured max policies | Still fallback |
| Seer selector unvisited/uniform | Must preserve configured selector | Unchanged |
| Recursive public entry, observer None, trace None | Personal/opaque observer outside proof | Unchanged |
| Recursive survivors <=5 | Seven-player root reaches <=5 after day/night deaths | Unchanged |
| Recursive no hunter, one initial seer | GJ can prevent death | Unchanged |
| Recursive fake-seer uniform or noncontradictory/uniform | Must preserve configured policy | Unchanged |
| Full board/public/private/past/physical canonical key, <=120 mappings | Proof may exceed cap | Unique fallback, never merge unproved |
| Transported root public relation signature equal | Multiple reports can split symmetry | Unchanged |

## Ordered gaps toward the actual target

1. Seven-player root with one wolf and all other proven conditions fixed (attempted; withheld after audit timeout).
2. Seven-player/two-wolf cast and six-survivor recursive boundary are separate proposed stages, each requiring complete distribution, branch, Table and terminal-value audit plus bounded cost-inclusive measurement.
3. Medium role and public medium claim require the same full-state proof; do not supply invented reporting laws.
4. Competing seer CO and random-white initial secret histories require conditioned joint-support evidence, including nonuniform masses and publication history.
5. Max policies require transported complete legal action score vectors, actor information and tie distributions; never optimize per hidden world before expectation. Personal scope and hunter/GJ remain fallback until their own certificates and transitions are proved.

Seven-player eligibility alone therefore does not make the heavy target active. No default-on or practical heavy-target speed claim follows from this experiment.

## Stage 1 result: eligibility change withheld

The temporary (7,1) gate completed uncompressed and grouped calculations with identical complete Tables and terminal value 19/35. Uncompressed: 17.0865s, 42,397 action expansions, peak working set 283,258,880 bytes. Grouped: 12.9946s, 25,357 action expansions, peak working set 184,930,304 bytes. These are exploratory single measurements, not a three-pair performance claim; a short test process overlapped part of the first run.

However the independent all-member terminal audit exhausted the existing 20-second budget (19.9871s) and returned pending. It did not establish complete branch-by-branch terminal equivalence. The root eligibility change was therefore reverted before commit; seven-player roots remain fallback. No six-survivor or two-wolf expansion was attempted. This is a bounded audit-cost blocker, not an authorization denial or a mathematical counterexample. Preserve the proof requirement rather than silently raising budgets or claiming the heavy target works.

Reproduction: measure_seven.py temporarily enables (7,1) in memory in each isolated child, never changes the runtime gate, and stops on the first pending result. Recorded raw results: seven-stage1-results.json. The successful boundary tests verify the retained fallback.

## Finite audit follow-up

The parent explicitly authorized up to 300 seconds for the missing audit. Inspection found the independent ungrouped oracle already retains its own value/action/acquisition caches across all batches. No member was skipped, no marginal-only shortcut was added, and no solver/cache algorithm was changed. The previous 20-second stop was an insufficient validation budget, not a structural impossibility.

The first extended run completed 2,280 audited batches and 5,880 original continuations in 34.319s (439,869,440-byte peak working set). Its post-run saved-Table comparison failed in the harness because raw Fraction objects were compared directly with serialized fraction strings. The audit assertions themselves had completed. The corrected harness normalizes JSON before comparison and saves the result before asserting, so future failures retain evidence. This correction required one bounded verification repeat, rather than treating that serialization mismatch as a solver difference. Both runs retain ten-second progress records.

The proof covers complete transported board, public and private joint state, physical board, history, role marginals, legal targets, exact incoming branch mass, every original member terminal value, and the weighted representative value. The previously saved uncompressed full Table is reused, avoiding a fresh baseline run.

### Completed certificate and retained scope

The corrected run completed in 34.614 seconds (34.630 seconds including source/monitor setup), 2,280 audited batches, 5,880 original continuations, 5,640 representatives, zero unproved branches. Peak working set: 440,061,952 bytes. Independent oracle: 20,160 solve calls, 42,240 uncached action expansions, 13,682 cached values. The audit's own caches are independent of the compressed solver. All transport and terminal assertions passed.

The repeat retained a second serialization issue: dataclass Values/HorizonValues were stringified instead of asdict. Because the complete result had already been saved, these exact repr strings were decoded using a whitelist AST (only Values, HorizonValues and integer Fraction calls), and every Table field plus final value matched the stored baseline. No third solve was performed. Future runs use the original benchmark's dataclass-aware serializer. This was solely a record-format correction; no numeric tolerance or changed expected result was used.

The (7,1) root gate is now retained as explicit opt-in, while recursive survivors remain <=5. Seven/two-wolf, medium, competing CO, initial-result histories, nonuniform conditioned joint laws, max policies, personal scopes and hunter/GJ remain fallback. The actual heavy target is still unsupported by this optimization. Default remains OFF.

## Three different costs and a sufficient Player comparison contract

1. Development audit: the independent ungrouped oracle expands every original member to terminal and checks transport, branch mass and weighted value. The 34.614-second run is this test cost; runtime default has audit=False.
2. Runtime grouping certificate: canonical_key transports the complete continuation payload, then also checks the root public relation signature. The unaudited seven/one-wolf run spent 3.074 seconds in the canonical-key timer; its total solve took 12.995 seconds. The timer stops before PublicRelations.signature, so it is not a complete breakdown of every comparison cost. Total worker wall time includes comparison work.
3. Player-derived comparison input: PublicRelations.from_view reads CO/received claims and makes the public relation signature. Source/view preparation occurs before the run's solve timer; the whole-worker wall time includes it. No isolated cost measurement was claimed. Current PlayerData equality alone is not a sufficient continuation equivalence contract.

A sufficient signature must preserve joint role distribution and weights; secret-acquisition/publication/guard/attack histories and their correlations; public and actor-visible conditioning; physical branch support and mass; legal moves, configured rules and policies; fixed IDs/targets and observer scope. Equal per-player role rates or displayed Table rows do not preserve these facts (the cycle-versus-two-triangles joint counterexample remains tested).

A future design could expose a dedicated immutable comparison contract: each player contributes only its local role/claim/history/target relation fields, while a Board-owned immutable joint-law reference plus rule/policy/scope references and an exact renaming map supply shared context. Never duplicate the joint law into every PlayerData. Equality of the complete contract can serve as a sufficient runtime certificate, avoiding a second heavy terminal audit in normal evaluation. The development audit remains a finite acceptance test for changes to that contract. This is a design proposal only; no PlayerData/schema rewrite was authorized or performed here.

### Next boundary relevance

For the current seven-player daytime root without hunter/GJ, a nonterminal day execution and night attack each remove one survivor before morning grouping: 7 -> 6 -> 5 (or terminal). Therefore raising the morning-grouping survivor cap from five to six would not enable additional continuations for either seven-player fixture. It would address a different reachable scope (for example eight-player roots, or a separately proved GJ transition), not the user's seven-player target under current guards. Do not spend a separate benchmark stage claiming that cap increase advances this target.

## Stage 2: seven players, two wolves

Separately changed only the root cast pair to (7,2), keeping every other root guard and the <=5-survivor recursive boundary. Initial 20-second baseline was pending; the next finite stage shared a total 300-second ceiling across baseline, grouped evaluation and independent audit. All three completed (including worker wall overhead, 157.461 seconds total).

| Mode | Solve seconds | Final value | Action expansions | Peak working set bytes |
|---|---:|---|---:|---:|
| Ungrouped | 37.710 | 8/35 | 81,697 | 552,091,648 |
| Grouped, audit OFF | 30.850 | 8/35 | 49,357 | 360,026,112 |
| Grouped, development audit ON | 78.360 | 8/35 | 49,357 plus oracle | 879,337,472 |

Every complete Table field matched exactly. All 4,620 audit batches passed, 12,180 original continuations -> 11,580 representatives, zero unproved branches. The audit uses the same independent full transport/terminal checks as stage 1. The unaudited canonical-key timer was 7.995 seconds, included within the grouped total; no separate Player-signature cost claim. These are single finite comparisons, not repeated performance estimates. No new mathematical/cache algorithm or cap increase was introduced.

Retained current cast pairs: (5,1), (6,1), (6,2), (7,1), (7,2). Default OFF; other conditions unchanged. The user's actual seven-player target still falls back because of medium, competing CO/reports, initial random-white secret history/conditioned joint distribution, and max policies. No further role/history/policy guard was relaxed. Evidence: probe_seven_two.py, seven-two-probe.json; the short pending record is seven-two-short-pending.json.

## Implemented comparison contract (no scope expansion)

matching_comparison.py now owns PublicRelations, ComparisonContext and ComparisonCertificate. The engine creates one frozen context holding existing immutable Rules/Strategy and a frozen public relation snapshot. certify(payload) reads the existing immutable ContinuationInputs references: public Board, public joint state, complete past, private joint state, observer and physical Board. It delegates to the unchanged exact canonical serializer and unchanged 120-mapping cap, then adds the unchanged public relation signature. The key is byte-for-byte/tuple-for-tuple the prior grouping condition; no marginal shortcut, schema or policy change was introduced.

Only certificate.key is used to group. ComparisonContext deliberately has identity equality, preventing accidental use of context or PlayerData equality as a proof. Original shared joint states remain shared by reference; there is no per-player joint-law copy, global certificate cache or cross-revision reuse. Board edits/corrections/withdrawals/recalculation produce new immutable payloads/contexts, while old snapshots remain valid only for their original inputs. Existing report-correction and retained-old-view tests still pass. This extraction does not eliminate canonical-key construction cost and makes no speed claim. A later cache/index improvement would require separate evidence.

Audit separation remains explicit: certify never calls a solver. Independent original-member solves and transport/mass/terminal assertions stay in group_inputs(audit=True), with a separate oracle created only when requested. Existing development audits on five/six-player complete Tables exercise the new contract without rerunning the completed seven-player numerical benchmark. New tests hold public rows fixed while changing private joint weights, physical branch mass, past publication, rules or policy: all yield different keys. Opaque observer and over-cap search still return no certificate and take unique fallback.

Timing: after this extraction proof_seconds encloses the entire certify call, including the public relation signature. Earlier recorded canonical-only timer numbers retain their historical definition; they must not be compared as an isolated speed regression. Full solve/whole-worker wall timings remain total costs. Normal runtime continues to default audit=False and matching OFF.

## Stage 3: positive nonuniform masses on complete prepared joint support

Selected exactly one remaining condition: remove uniform role-mass restriction. This is smaller than medium/multiple-CO/initial-scan support because it changes no role inventory, observations, reporting law, secret acquisition ledger, actor policy or transition. The exact comparison key already includes every joint hypothesis and exact mass, so uniformity is unnecessary for its transport proof. Keep complete support size, one unique hypothesis per role allocation, positive exact normalized masses (TrueScanState/Hypothesis invariants), and explicit Board/public-joint agreement. All other root guards and the <=5-survivor boundary remain unchanged. No unknown/zero-support history is fabricated or filled.

Fixture generation multiplies the complete existing role law by a positive synthetic likelihood then uses existing exact normalize and Board projection. These are prepared-prior acceptance fixtures, not a newly defined game observation, CO/report strategy, saved input or prior-reconstruction rule. They demonstrate weighted joint-law handling only. They do not establish general conditioning on initial secret/public report history, which remains outside this gate. The real heavy seven-player target still has other blocking guards.

Small acceptance: 5/1 point-biased likelihood gives exact 7/15 and complete Table equality, 4 independent audited batches. 6/2 cycle likelihood gives every latent player's wolf marginal 2/5, while adjacent wolf pairs have mass 2/15 and nonadjacent pairs 1/15. Its terminal value is 1/12, complete Table equality, all 60 audited batches passed (240 original continuations -> 220 representatives). The input joint distribution remains complete and nonindependent. Pre-extension requested grouping was inactive; after extension only the mass restriction differs. Before/after raw evidence: weighted-before.json and weighted-after.json. Audit run times 0.108s and 2.876s are validation costs, not speed comparisons against unaudited runs.

The full ComparisonCertificate is not a simple Player signature derived solely from public local conditions. It still serializes complete joint/private/physical laws under candidate mappings, plus public relations. Its construction cost remains. No approximation or claim that comparison became free follows from the contract extraction or this mass extension. Normal runtime still avoids independent old/new terminal audit; development audit is explicitly enabled only for acceptance.

### Seven-player acceptance and runtime cost

7/1 point-biased complete joint law: ungrouped baseline completed in 20.297s; independent grouped audit in 42.252s; stage whole-worker wall time 68.832s (shared 300-second ceiling). Both full Tables and final 19/35 matched. All 2,640 batches / 6,720 original continuations passed; 6,540 representatives, zero unproved branches. Audit peak working set 489,189,376 bytes. Exact incoming physical branch mass, transported joint/private history and every original terminal value are checked by the unchanged independent oracle. Original public mass, within-world secret conditioning and branch mass are not interchanged.

A separate unaudited 6/2 cycle-joint run completed in 1.483s with 0.0925s spent constructing complete comparison certificates, 240 -> 220 continuations, 2,806 -> 2,606 action expansions against the archived ungrouped baseline. Audit batches=0. Peak working set 43,315,200 bytes. The archived baseline solve was 1.558s: these are individual measurements (not a repeated statistical speed claim). Independent audit of the same case cost 2.876s and is not on the normal runtime path. Evidence: weighted-runtime.json; seven progress JSONL and weighted-seven-results.json preserve progress and complete outputs.

Final relevant regression: 40 tests passed in 23.623s, including complete Tables/branch audits, exact renaming, hidden-joint counterexamples, view corrections/withdrawals, row builders and HELP. Default OFF and all role/history/policy guards are unchanged. No production input format or prior-reconstruction semantics were expanded: this extension consumes valid already prepared positive full-support weighted laws only. General conditioned secret/public-history support remains a separate next stage.

## Stage 4: one actual first-day public white from a known true seer

The next logical condition is an observed initial-result ledger, tested through real /start and /table-publish requests, BoardData.roles(), and prepare_evaluation(). No custom prior weights are injected. With initial_seer=random_white, one certain true seer and one day-1 white report to another living player, replay removes role allocations in which that target is wolf. prepare_evaluation returns the existing prior route with exact Hypothesis Acquisition and SeerReport records. We consume those outputs without changing reconstruction or report likelihood semantics.

The extension is deliberately one complete observation case, rather than blanket removal of individual ledger guards. Sufficient entry conditions: day 1 daytime, all alive, no physical death/action history; exactly one certain true seer; no medium/hunter; only seer/latent CO; random day/night/fake-medium and existing scan selectors; exactly one initial white published on day 1 at slot 0; tracked seer matches that actor, observed_prefix=1; every hypothesis has exactly the matching initial Acquisition and no guard/attack records; unique role allocations count comb(n-2,wolves); public Board joint equals prepared joint. Active public relation metadata must match the report. The empty-initial-ledger scope remains unchanged. Missing, extra, stale, later or unmatched ledgers and different initial rules fail closed. No support is filled or resurrected.

This removes candidate worlds rather than merely reweighting complete unconditional support: 5/1 has 4 -> 3 allocations; 6/2 has 10 -> 6; 7/2 has 15 -> 10. The white target is nonwolf in every surviving allocation, while secret acquisition and public publication are distinct retained records. Model A public role weights, within-world secret histories and physical branch masses retain their existing meanings; target-choice frequency is not introduced as a new public role weight.

Reference comparison before extension: actual input fixtures 5/1 and 6/2 requested grouping but remained inactive, with final values 7/15 and 1/12. Full original Tables are saved in initial-white-before.json. The acceptance unit uses these references, then a new actual-input 7/2 baseline plus independent grouped audit, under a shared 300-second/four-million-work ceiling. It checks complete Tables, joint support and records, legal-target transport, exact branch mass, every original terminal value and weighted representatives. Progress and process memory are recorded every ten seconds. No normal runtime oracle or default ON is added.

### Actual-input acceptance completed

Shared validation unit completed in 63.558 seconds, below the 300-second ceiling. Exact complete Tables and final values match in all cases:

| Cast | Independent audit seconds | Audit batches | Final value |
|---|---:|---:|---|
| 5/1 | 0.062 | 3 | 7/15 |
| 6/2 | 1.221 | 36 | 1/12 |
| 7/2 | 42.047 | 2,840 | 8/35 |

The 7/2 ungrouped actual-input baseline took 20.081s. Audit process peak working set at final checkpoint: 474,832,896 bytes (includes preparation/baseline/monitor and validation; not a per-request isolated allocation). The 7/2 grouped audit checked 5,790 original continuations -> 5,510 representatives, zero unproved branches. Certificate construction total was 5.070s within the audited run; it remains real runtime work, not a simple free Player signature. No unaudited speed improvement is claimed from audit-versus-baseline timings.

Relevant suite: 58 tests passed in 25.917s, including real input-path publication, correction 3 -> 4, withdrawal, retained-old-view, public-prior cached/uncached equality, stale/multiple ledger/max fallbacks, exact renaming, complete Tables and full-disclosure observed semantics. The added real competing-CO check is run separately after the suite; it must remain fallback. No counterexample to the exact full-state grouping certificate was observed. No new mathematical specification was needed; existing input/replay semantics are unchanged. Current supported initial-ledger cases are empty/none and this one known-true initial public white only. Default OFF; multiple CO, medium/hunter, additional/later/hidden reports and max stay outside this extension.

Final competing-CO/correction/withdrawal plus HELP follow-up: 5 tests passed in 1.055s.
