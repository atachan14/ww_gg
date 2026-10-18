# Role-colour helper review (2026-10-18 UTC)

Decision: stop the tuple-hash experiment at 83cbd93 without adoption. No heavy runs were performed for this review. The production numerical route remains unchanged; `git grep` found no component_key, ComponentReuseForecast or make_component_canonical reference in werewolf/ or app.py. Dedicated18801 was not restarted. Default remains OFF.

## What the measured scope actually does

The detailed current-input trace recorded 113178 calls to exact_renaming.colors, taking 7.267 seconds inside the 52.629-second instrumented solver. This includes marginal lookup/calculation AND per-player claims, alive/target flags, death history, roster membership and tracking flags. It does not establish 7.267 seconds of marginal arithmetic alone. Marginal misses, hits and hypotheses visited were not separately counted. Each call requests the public-law vector and, unless private is the identical object, the private-law vector: between 113178 and 226356 helper requests, with an unknown number of builds.

For each supplied complete normalized joint law, the current helper sums each hypothesis mass into every player/role bit. Hypotheses include complete role tuples, acquisitions, guard histories and wolf attacks. The four role coordinates are wolf/medium/seer/hunter; citizen is implicit. The private law has already been conditioned on the observer's permitted information. The helper must not replace that law with the public law merely because some summaries coincide.

## Existing reuse and invalidation

| Value | Identity / lifetime | Miss or invalidation |
|---|---|---|
| Colour marginal vector | Per-engine dict keyed by (id(law), player_count), retaining law and checking `is` | Different state identity or player count; whole dict cleared before a constructor when size exceeds128 (up to130 entries can briefly exist after two insertions) |
| Source canonical key | Per-engine LRU2048, complete source evidence equality | Any source/context difference; eviction |
| Serialized Board/state | Per-engine LRU128 each, identity plus renaming, strong reference verification | New object/mapping or eviction |
| TrueScanState.public_roles | Lazy value on each immutable state, exact role-tuple mass sums | New state has no derived attribute; noncanonical mutable inputs are uncached |

Conditioning, acquisitions and publication branches create normalized replacement states. Dataclass replacement invokes construction and does not copy the non-field `_public_roles_cache`. Thus changed joint masses do not reuse a previous state's property cache. Metadata-only replacement can lose a reusable derived value, but there is no evidence yet that retaining it would matter. Equal but separately constructed laws currently miss the identity marginal cache. Strong references avoid id-reuse aliases, at the cost of retaining their complete joint laws within the bounded cache.

## Correlation-safe candidate, not implemented

`public_worlds` already sums exact Fraction mass by the COMPLETE role tuple; `TrueScanState.public_roles` caches that derived joint-role distribution. A colour-only helper could expand those grouped role masks instead of every secret-history hypothesis. Linearity gives exactly the same per-player coordinates. This is a candidate for reusing an existing derived value without adding a new large cache. It does not authorize replacing full secret laws, policy evaluation, physical masses or final canonical equality with role marginals. Full state signatures still retain roles, masses, acquisitions, guards, attacks, rosters and observation context.

For H secret hypotheses and R distinct role tuples, a cold grouping costs O(H) dictionary/Fraction work plus O(R * role bits); the current path costs O(H * role bits). If H is close to R, grouping may lose. If public_roles is already warm, expansion may win. Its actual warmth and H/R distribution in the measured input are unknown. Merely expanding cache capacity would retain more complete laws and lacks supporting hit-rate evidence. A same-capacity LRU could avoid clear-all churn, but is likewise unmeasured and not proposed as an immediate production change.

## Stage-end basis

Even removing the entire measured colour scope would save at most about14% of this instrumented solver time; eliminating marginal arithmetic alone saves less. This is an opportunity ceiling, not a predicted speedup. The tuple-hash prototype produced no material end-to-end improvement and added roughly57MB peak RSS. No further large cache is justified. Preserve current behavior and end this optimization stage. If a later CPU slot is explicitly assigned, first compare identical vectors/complete canonical keys on small correlated-history fixtures, then count cache misses, H/R and public_roles warmth on the real input before committing to another timed prototype. No speed claim or adoption follows from this read-only review.