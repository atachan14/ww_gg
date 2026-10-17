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
