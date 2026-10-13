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

Other history-loss points still requiring separate work are the multiple
unobserved-night reset in `seed_history`, the terminal-next-execution public
ledger retirement in `guarded_outcomes`, and private attack replacement in
`InformationSetForecast.evaluate`. The new recovery removes the extra ledger
deletion introduced specifically for wolf-deducible hunters. General multiple
night histories, hunters still uncertain to wolves, and arbitrary mixed casts
remain outside this milestone. No new game rule or public UI text was added.
