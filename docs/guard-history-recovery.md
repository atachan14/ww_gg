# Local recovery and first shared-history milestone

The recovery repository descends from `79ed2d5`. `bd1f73b` preserves the
370-file verified snapshot and its five changed files. `0fa3e9d` separately
recovers the stopped owner's four later changed files after 36 related tests.
The original working tree is retained and this repository has no remote.

## History ownership and flow

- `Hypothesis` jointly stores role masks, scan acquisitions, exact mass,
  `GuardIntent` records, and `WolfAttack` records. `TrueScanState.rosters`
  validates the original roster for each private record.
- `prepare_public_prior` reconstructs scans and roles from the public game;
  `from_board` starts with empty guard and attack records. It does not replay
  a general guard/attack policy ledger.
- `seed_history` currently reconstructs one special four-alive successful
  night using `guard_prior_roster`. Its general role in this milestone is to
  preserve existing records when a wolf roster already determines the hunter.
- `InformationSetForecast.wolf_policy` conditions the public mixture on the
  initial wolf roster and its attack records. Hunter views separately filter
  role support and merge only the viewer's own guard records. Public day
  decisions use the public law, not either viewer's evidence.
- `guarded_outcomes` appends both actual owner records to the physical branch.
  `GuardContext` keeps the public Board/state separate from that branch.
  `project_private` reweights a ledger to the Board's role prior and retains
  its records. Acquisitions and report likelihood transfer retain owner data.
- Memo/value keys retain guard/attack histories under max policies. Random
  policy scalar keys may marginalize irrelevant records without changing the
  flow payload.

## First milestone

Six alive, two wolves, one hunter, and three citizens; public claims mark
players 1–3 latent and players 4–6 villagers. The public hunter probability
at each latent location is 1/3, while each initial wolf roster determines the
hunter. No player-count or permutation exception was added to the solver.

The shared engine gives village win 5/12: execute a latent wolf with probability
2/3; the following five-player night has value 1/4 + 3/4 * 1/2 = 5/8.
Executing a known villager loses. A separate six-alive night regression starts
with an existing successful guard/attack ledger, checks the wolf's optimal
uniform tie, both appended owner records, preservation of the public mixture's
existing records, unchanged source data, and exact public role-prior ownership.

## Remaining generalization work

The public child state's new hidden-action mixture is not yet computed from
all roster/history-conditioned optimal wolf policies. A fixed row's actual
attack must not be copied into that public mixture. Model A's compatibility
role prior must remain separate from policy-dependent hidden-history weights.
This is an algorithmic dependency, not permission to choose an arbitrary
uniform attack prior for an asymmetric information set.

The first recovery removed the extra ledger deletion introduced specifically
for wolf-deducible hunters. The next milestone below removes two more erasure
paths; private attack replacement in `InformationSetForecast.evaluate` remains
a separate owner-projection issue. General policy-dependent reconstruction of
multiple nights and arbitrary mixed casts remain outside these milestones.
No new game rule or public UI text was added.

## Uncertain hunter with two past successful nights

Start from six players with a known wolf at 1, hunter at 2 with mass 3/4 or
at 3 with mass 1/4, and citizens at 4, 5, and 6. Under the previously selected
random attack strategy, execute 6, block an attack on 4, execute 5, block
another attack on 4, and execute 4. Both hunter worlds can produce those
records with the same uniform guard likelihood. The current Board is night 3
with alive roster (1,2,3), and the current attack strategy is max.

The public history mixture explicitly retains both past `GuardIntent` and
`WolfAttack` records. A wolf roster does not determine the hunter. The common
engine now accepts the complete ledger instead of deleting it because two
unobserved nights occurred. It requires coverage in every hypothesis; empty
and partial ledgers remain pending and are not completed by guesswork.

Biting 2 has village win 1/4 * 1/2 = 1/8. Biting 3 gives 3/4 * 1/2 = 3/8.
Death reaches wolf parity; a block allows the public to execute the known wolf.
The unique max attack is 2. Hunter 2 cannot stop that bite; hunter 3's fixed
guard on 2 wins with probability one. Neither private comparison changes the
public attack policy or Board. The success branch retains prior public records
instead of retiring them, while both physical owner ledgers append night 3.
This milestone adds no population or permutation exception.

## Precise zero-support boundary for a future policy-conditioned mixture

In that same night, max-policy success can occur only in the hunter-3 world.
Its physical success law has probability 1/8 and hunter 3 with probability one.
Model A's public no-death compatibility update keeps hunter 2 at 3/4 and
hunter 3 at 1/4. Hunter 2 cannot guard attack target 2 because self-guard is
forbidden. Therefore no valid guard/attack history from the unique optimal
policy can carry the positive public mass of the hunter-2 world.

Within-world renormalization is valid only when each retained Board role world
has positive compatible policy/history support. At zero support, it cannot
preserve both that world's public mass and physical optimal-policy records.
The present terminal continuation needs no new hidden-action mixture: its next
public execution ends the game. The existing separate public and physical laws
are sufficient, and the regression checks both without behavioral inference.

A nonterminal continuation encountering this boundary needs an explicit
choice before implementation:

1. Keep the public-role compatibility rule and leave zero-support future
   mixtures pending. Generalize only cases with positive per-world support.
2. Specify a counterfactual history law for retained public worlds with zero
   optimal-policy support. Which nonoptimal actions get positive support and
   which exact weights is additional strategy semantics, not a cache choice.

Dropping or downweighting the hunter-2 world using the chosen max policy would
add behavioral inference and contradict the agreed Model A rule. It is not
implemented as a fallback.
