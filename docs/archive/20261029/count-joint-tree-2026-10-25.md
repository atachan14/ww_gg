# Count descriptor after physical convergence

## Reproduction and cause

Seven players, citizen3/medium1/seer1/wolf2; random-white first scan; MAX day/night/fake reports, cutoff enabled. Manual simultaneous inputs: players1/2 claim seer and both report player3 white; player3 claims medium. Execute4. The saved navigation journal was read and restored separately before any normal-server restart. Its identifying public-log IDs were removed from the committed fixture.

Before this fix, expanding h1~3 fails in EvaluationGraph._public_mixture -> public_convergence.mix -> evaluation_branch.physical_board -> Board.__post_init__. The first physical component has an exact live-wolf count, while the weighted mixture law can have multiple live counts. Replacing the law inherited that component's scalar count and validation correctly rejected it. Scalar evaluation had already completed; this is retained-record public projection, not evidence that every displayed Tree carrier was already constructed.

## Fix and mathematical contract

When physical_board must construct a carrier from an explicitly supplied law, derive its live-wolf count from that law (wolf_count=None constructor input). This is a derived descriptor, not an independently retained constraint on a different law. Keep all role/history/acquisition atoms and exact weights unchanged; keep public Q and its history untouched. The existing no-rebuild identity fast path remains. All Board validation remains, including rejection of a genuinely inconsistent explicit scalar and law. No tracking closure or history normalization was introduced.

The regression independently reproduces the old constructor rejection, then compares the complete mixed atom law, exact role marginal, live-count mass, component-order invariance and unchanged source/public Q. It covers no abilities, seer, and seer+medium, with unequal weights. The sanitized real journal regression expands the previously failing branch and night Current, verifies the immutable navigation export and every retained physical law.

## Verification

- Existing related public convergence and API plus physical branch tests:15 passed.
- New saved-journal regression:1 passed,54.619s cold process.
- Direct saved-journal replay: restore42.500s; h1~0 0.297s; previously failing h1~3 4.625s; h2~0 0.140s. Backend only, not a rendering benchmark.
- Affected projection run:13 passed,1 failed. Existing test_recorded_public_projection.RecordedPublicProjectionTests.test_tree_arrival_updates_and_cold_Current_use_evaluated_records expects owner evaluator but receives mixed-evaluator-day. Re-executing the same test with the pre-fix physical_board implementation reproduces the identical mismatch; left unchanged.
- Isolated Edge browser: actual start -> simultaneous public inputs -> h1~0/h1~3 HTTP expansion -> execute4/current night -> h2~0 HTTP expansion -> Main reload passed, no JS exceptions. Public input88.223s (full MAX evaluation), failing expansion4.437s, night Tree0.183s. These include browser request latency; not a speed improvement claim. Main screenshot checked at `.artifacts/count-joint-tree-desktop.png`.
- Normal18821 restarted only after preserving/replaying the original saved journal. New server PID476, Main HTTP200. Isolated Edge profile on the normal URL repeated the same actual public-input/current flow: input86.374s; h1~0 0.295s; formerly failing h1~3 4.467s; night Current0.117s; h2~0 0.172s; Main reload0.180s. All HTTP requests succeeded; JS exceptions empty. Scrolled to and visually checked the expanded Tree screenshot `.artifacts/count-joint-tree-normal.png` (2CO update, execution4 group, night Board, medium black/white, seer and attack branches). This is bounded branch acceptance, not an exhaustive full-Tree/browser test. Saved journals were not deleted; no push or external deployment.

No complete repository-suite claim; unrelated unresolved legacy comparisons remain outside this fix.
