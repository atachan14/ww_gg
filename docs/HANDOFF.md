# Run, test and release handoff

Read [CURRENT](CURRENT.md) and repository `../AGENTS.md` before changes. This is a navigation guide, not a fresh full-test or runtime certification.

## Workspace and start

Formal workspace on the user's Windows machine: `G:/source/repos/Python/ww_gg`. Start with `../start.cmd`: repository-local Python `.venv`, `-X utf8`, `../dev_previews/run_current_app.py --port18821`. URL `http://127.0.0.1:18821/main`. See [relocation and rollback](repos-migration-2026-10-27.md). Historical PID numbers are not current process identity; inspect listener and command before any restart.

For a fresh environment create a virtualenv using the project's supported Python and install `../requirements.txt` (Flask3.1.2). Do not copy `.env`/credentials from preserved legacy directories. The local runner's ephemeral signing key and a normal restart may reset its browser session; that does not authorize deleting journal files. Stable hosted signing configuration is an environment prerequisite, not material to print in docs.

Structure: `../app.py` HTTP/stream orchestration; `../werewolf/` exact models, navigation, evaluator records and reconstruction; `../templates/` and `../static/` source UI; `../public/static/` hosted asset copies; `../tests/` independent/contract/DOM tests; `../dev_previews/` isolated local launchers. Asset synchronization uses `../build_vercel.py`; do not hand-edit just one copy. This docs-only change does not run builds or restart servers.

## Verification tiers

Use a small exact case first, then affected integration tests. Avoid concurrent CPU-heavy searches. Example PowerShell from repo root:

```powershell
$env:PYTHONPATH='.;tests'
.venv/Scripts/python.exe -X utf8 -m unittest tests.test_model_a_night_oracles
node --test tests/personal_cold_generation.test.cjs tests/calculation_cancellation.test.cjs tests/browser_history.test.cjs tests/input_calculation_option.test.cjs
.venv/Scripts/python.exe -X utf8 -m unittest tests.test_browser_history tests.test_calculation_cancellation
```

Node must be available locally; do not install or change global tools merely to run these examples. `tests` on PYTHONPATH is needed by some old test modules importing sibling fixtures.

Full discovery (`python -m unittest discover -s tests`) includes expensive exact enumeration. Set a justified external per-command bound, preserve final counts/logs and name excluded/interrupted cases. A focused pass is not a full pass. Browser tests require explicit supported browser control; no bypass of approval or hidden credential extraction. Use synthetic Boards in isolated sessions; never upload original saved journals to a Preview.

Independent oracle requirements: exact total and every candidate value, chance/selection probabilities, Q/P and private joint-state fingerprints, representative mapping, zero-weight inspection/manual branches, Current/back/reload/cold restore. Do not fit expectations to current output. [Old failure triage](repository-verification-2026-10-24.md) and [remaining night fixtures](remaining-night-fixture-triage-2026-10-24.md) are dated partial coverage; [898a01a proof](v06-numeric-contract-resolution.md) supersedes the two corpse-target numerical holds. Some broader history/tracking comparisons remain unresolved; do not erase distinctions by normalization without proof.

## Important dated measurements (not promises)

| Date / evidence | Fixture / result | Interpretation |
|---|---|---|
| 2026-10-26 [staged flow](staged-navigation-evaluation-2026-10-26.md) | seven-player public CO fixture, exact89/224; unprofiled85.076813→84.321234s | one pair, not robust large solve improvement; adoption/roles milliseconds do not mean search finished |
| 2026-10-27 [label projection](public-label-projection-performance-2026-10-27.md) | implementation `e2c47e1`; exact full-state label projection comparison | inspect paired CPU/wall evidence in that record, not its high-overhead profile as baseline |
| 2026-10-27 [cloud acceptance](fixed-preview-acceptance-2026-10-27.md) | Preview4dc7246, cancelled43463work,7.399422s lifetime; disconnected run110.029623s complete | no general cancellation-latency or cross-worker guarantee |
| 2026-10-27 [local UI](browser-history-ui-followup-2026-10-27.md) | 24JS +29Python; injected deadline/failure and retry7/15 | local evidence, not actual cloud270/300second failure acceptance |

Read the full source record for strategy, rule, scope, profiler and machine conditions. Never compare different fixture/CPU-load/profile/browser totals as the same benchmark.

## Release gate / operations

v0.6 is not published. Production03e4e31 and Preview4dc7246 differ intentionally. No push, deployment, alias, tag, Release or credential/security change is authorized just by this handoff. A push to the existing Preview branch can automatically deploy and consume Team usage. Check actual branch and deployment state before a retry; uncertain creation is not permission to create another.

Remaining Preview gates: actual platform deadline/failure UI and retry; communication-failure retry (blocked by approval UI, never executed); bounded overlapping private-restore race cloud verification; a decision if guaranteed cross-worker CPU stop is mandatory. Existing local fault injection and deterministic JS races are useful but distinct evidence. No extra infrastructure, DB, shared cancellation service or new paid plan has been adopted. [Earlier hosted decision gate](v06-hosted-tree-decision-gate.md) is historical: its blanket hosted-Tree guard and implied shared-backend prerequisite were superseded by the approved browser-owned prototype, not silently satisfied by a DB.

Protect `.artifacts`, navigation recipes, untracked `docs/previews`, legacy/recovery copies, `.env` and unrelated edits. Never include secrets or real saved Board contents in shared docs. Preserve old conceptual arguments and negative results; archive only with explicit reference repair and provenance. Changes to rules or unsupported strategy semantics need a user decision, not documentation cleanup.
