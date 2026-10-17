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
