# Default-off input calculation preference

Display adds only checkbox「入力中に計算を進める」through shared TOP/Main settings. No checked attribute: fresh or inaccessible browser storage defaultsOff. Uses origin-local browser preference `ww_gg.input-calculation`, parallel to existing probability/role display preferences; no game/session schema change. Explanation is Help > 操作説明 > 表示, `/help/operations/display` in the existing Help bookshelf.

Off neither schedules the180ms timer nor sends automatic `/table-preview` requests. Toggling cancels timer/controller, advances the existing generation guard and retains the exact draft. Dirty values are shown as未計算, not committed results; ordinary committed Board/Tree calculations are not disabled by this preference. On uses existing180ms debounce/latest-request cancellation. No input controls are reconstructed on a toggle. Update uses the unchanged validated save/Board insertion and evaluation path regardless of preference, and accepted saves are not canceled as previews.

## Proven cancellation adapter defect repaired

Persistent Table requests use an NDJSON Accept header but return JSON. The prior cancellation registration only bound the request thread when the header was nonstreaming, so the persistent adapter did not observe its event. Bind the same event before dispatch for either representation; actual streaming workers still bind it independently. Added regression: a plain JSON adapter requested with streaming Accept must terminate and release its worker. No mathematical/history/policy change.

## Verification

Final83 Python tests pass11.951s (option controls/Help, TOP/Main, Log, seer rules, cancellation/streams, immutable sharing/hash, budgets and deployment asset parity). All62 JS tests pass0.335s, including preference fresh/default/unavailable storage, persistence, idempotent binding and existing cancellation/write-preservation tests. Public assets synchronized by the existing build.

Isolated real Edge + persistent local HTTP server,5-player citizen3/seer1/wolf1:
- Off sends no preview after edits; On respects debounce; repeated On/Off cancels the queued timer.
- Running preview cancellation reaches the actual backend event; held-loop test releases in6ms. This is a deterministic cancellation integration check, not a new real-solver latency benchmark.
- Draft, selection and focused result control preserved.
- A deliberately ignored AbortSignal forces a late valid reply: generation guard prevents stale installation afterOff.
- Injected save503 preserves input for retry; Update worksOff andOn. All47 displayed exact fraction values equal after the same public update in both modes.
- Preference persists through Board replacement/reload. Help path and selected bookshelf item verified; desktop1440 and narrow390 screenshots inspected. No runtime exceptions; final worker registry empty.

Evidence `.artifacts/input-option-browser.log`, `input-option-final.log`, `input-option-js-final.log`, `input-option-{desktop,mobile}.png`. The test-only delay/error routes exist only in the ephemeral verification script, never the production app. Initial browser test exposed the adapter defect above; the corrected final test passes. Known unrelated old tests/semantics remain untouched. No external deployment or saved-data deletion. Normal18821 activation and final smoke follow the local verified commit.
