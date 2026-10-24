# Three input calculation display modes

Supersedes the checkbox behavior in `input-calculation-option-2026-10-25.md`.

## Contract and preference migration

Compact shared TOP/Main display control:「入力中に計算を進める」with Off / 役職率まで / 全て. Unset or unavailable storage defaults `roles`. Existing origin-local `ww_gg.input-calculation` is reused: explicit legacy `false` migrates to `off`, explicit legacy `true` to `all`; migrated values are persisted. The old checkbox wrote only on changes, so its untouched default has no key and now adopts roles. Existing `off/roles/all` choices remain unchanged. No account/session/game-input schema or authentication change.

Off creates no preview timer or request. Roles andAll retain180ms debounce, scoped cooperative cancellation and generation guards. Mode changes preserve draft/selection/focus. Saves are still independent accepted writes. Each request freezes its `preview_mode` before awaiting a response. All-to-roles cancels obsolete full work, and late full responses cannot install after a newer roles frame.

## Server boundary

`/table-preview` validates explicit `roles/all`; omitted mode retainsAll for compatibility. Invalid/Off request modes are rejected before role work. Persistent navigation forks the same public/physical joint state, applies existing evidence conditioning, then renders roles_only/future_deferred and returns without forecast/action-value/Tree construction. Ordinary JSON andNDJSON paths do the same; NDJSON role-only emits a single terminal complete response and never continues a hidden full search. No new marginal-only replacement state is invented; complete role/private-history correlations remain owned by the existing nodes. Role-only frames show未計算 in overview and candidate win cells with no stale numeric fraction attributes. Committed Boards still show their computed values.

Update uses unchanged validation/commit/full calculation in every mode, even if a caller includes a role preview mode. It never treats a role frame as a completed value table.

Explanation exists only at Help > 操作説明 > 表示 (`/help/operations/display`), including remaining role-history preparation cost and preference migration. Main adds only the compact control.

## Final evidence

87 Python tests passed14.760s;63 JS tests passed0.343s. Focused roles tests cover ordinary and persistent JSON/stream adapters, named and anonymous-owned roots, Day2 delayed disclosures, exact role-rate equality withAll, all-mode Update equality and invalid-mode early rejection. During roles calls, forecast methods and future solve/Tree expansion are replaced with failures; those calls do not occur. LaterAll/Update still calculate normally, so a pending role frame does not poison value caches.

Isolated Edge + persistent server with normal anonymous-ownership flag verified: fresh role default; legacy migration and persistence; Off no traffic; debounce and repeated mode switches; actual cooperative All-to-roles/roles-to-Off stop; a deliberately delayed completedAll reply cannot overwrite newer roles; draft/selection/focus retained; failed save retains input; exact47 displayed fractions equal after Update in all3 modes; Current/back/reload; Help and desktop1440/narrow390 visuals. Held-loop cancellation observation8ms is an integration check, not a general real-solver latency claim. No runtime exceptions, only roles/all preview requests, final registry empty. Artifacts `.artifacts/three-mode-{focused-final,browser-final,regressions-final,js-final}.log` and input-option desktop/mobile screenshots. Public assets synchronized through existing build.

Known unrelated failures/unsupported policies and numerical semantics unchanged. No remote push/deployment or saved-data deletion. Local activation and live smoke follow the verified commit.
