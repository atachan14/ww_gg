# Formal local repository relocation (2026-10-27)

Formal workspace: `G:/source/repos/Python/ww_gg`. Local URL remains `http://127.0.0.1:18821/main`.

Baseline: 182beff (Footer fix 5bd611f; public-label optimization e2c47e1 and forced-death reuse ef24b6d retained). No solver/model changes in relocation.

The pre-existing repos directory must be preserved as a complete sibling backup, including its a8ebced master history, 22 tracked modifications, 1011 untracked files, .env, .venv and local browser artifacts. No old .env credential is imported into the new workspace. The recovery source at C:/Users/user/Documents/Codex/2026-10-14/task/ww_gg-recovery-git remains intact.

All source files except disposable __pycache__ were copied and SHA256-compared before activation. The complete Git directory and untracked artifacts/previews are retained. Navigation evidence journals are copied again after the old server is stopped and compared byte-for-byte; no evaluation cache or guessed state is substituted for saved history.

## Start

Run `start.cmd` from this directory. It uses the local .venv Python 3.12 and the unchanged dev_previews/run_current_app.py on port18821, with the same preview flags and cookie name. The new venv inherits installed system packages; Flask3.1.2 matches requirements.txt. No network package installation or credentials are required. The former 8771 entry was replaced intentionally for the normal local interface.

Ephemeral signed browser sessions reset on normal process restart because the existing runner uses a per-process signing key. Persisted journal files remain; credentials/signing settings were not changed to avoid the reset.

## Rollback without deletion

Identify the current18821 listener and verify its command belongs to this application before stopping only that process. To revert the runtime, start the unchanged recovery source with Python3.12, -X utf8, dev_previews/run_current_app.py --port18821 from its original directory. New journals created after migration must first be copied to a separate backup and reconciled; never overwrite divergent journals blindly.

To restore the original repos folder layout, first stop the identified application, rename the new formal directory to another unique sibling name, then rename the preserved legacy sibling back to ww_gg. Never merge its older code or .env into the latest tree by overwrite. Do not delete either preserved copy as part of rollback.

## Acceptance

Completed normal activation and actual browser verification.


- Full copied-file SHA256 comparison: 36,779 files, 600,954,179 bytes, excluding __pycache__; 310.72seconds including copy and verification. Copied Git passes connectivity-only fsck; baseline HEAD182beff and no tracked source changes except the intentional start.cmd entry.
- Legacy backup: G:/source/repos/Python/ww_gg-legacy-20261027-before-recovery. Its tracked/untracked counts remain22/1011. The complete .env and .venv remain inside that backup. The saved status inventory is .artifacts/repos-legacy-status-20261027.txt. A Git ownership warning after renaming was handled only with command-scoped safe.directory for the exact verified backup path; no global Git/security setting was changed.
- Frozen old-server journals:121, all SHA256-identical after final stopped-server sync; manifest .artifacts/repos-migration-journal-sha256.json. After browser testing there are122 journals; all original121 remain byte-identical. No saved data was deleted.
- All121 saved journals parse as version1. A real saved journal restores at revision1/currenth1 with identical export fingerprint in recovery and formal workspaces (2f80ba6075a0558f2bae5cf4a8cbbcf15fd08b65dcb0e69993ab0a5187306dc8). Direct equality against the older serialized record initially failed in history.rows; the same existing restore/export behavior is present in the recovery source, and no normalization, journal rewrite or product change was introduced to hide it.
- New local venv: Python3.12.10, system-site-packages=true, installed Flask3.1.2. The existing global interpreter provides the pinned dependency; no network installation, credential import, or signing-key change.
- Focused new-path tests:12/12 pass in2.937seconds (navigation_store, navigation_http, phase_footer, staged_target_submission); log .artifacts/repos-migration-tests.log. Full expensive repository suite not rerun for this filesystem/launcher relocation.
- Normal listener PID18648; venv parent PID24368. Windows venv launches the base Python executable as child; the actual listener command points absolutely to G:/source/repos/Python/ww_gg/dev_previews/run_current_app.py --port18821. HTTP200 on the unchanged URL. Source/static/live app.js and board_navigation.js bytes match; optimized source modules also match the recovery source exactly.
- Actual isolated IAB browser: TOP -> five-player citizen4/wolf1 Main -> staged completion46.67%(7/15) -> selectPlayer2 -> Day1night -> Day1day -> existing same Day1night -> reload. Server calculation confirms occurrenceh1/revision3. Tree renders after reload with representative execution [1,(2),3,4,5], current conditional33.33%(1/3), cumulative46.67%(7/15). Browser error log empty; endpoints200 and no Invalid player. Screenshot capture returned Unable to capture screenshot; visual evidence is limited to actual browser DOM snapshots and normal HTTP logs, not an image artifact.
- Logs: .artifacts/repos-normal-server-out.log and repos-normal-server-error.log. No other application/process was stopped. The old listener25732 was identified and stopped; old recovery source remains intact.
- No push, external deployment, permanent deletion, additional optimization or mathematical/policy change. Existing old test disagreements remain outside this migration.
