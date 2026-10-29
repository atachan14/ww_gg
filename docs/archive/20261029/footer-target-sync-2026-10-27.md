# Footer Invalid player: staged target-control synchronization

Baselineproductione2c47e1/recordde0998c. This follow-up changes only UI control synchronization, not evaluation or history/phase selection semantics. No large performance benchmark or private-view expansion is introduced.

## Reproduction and diagnosis

The previous7-player acceptance recorded h1/revision2 after manual Tree storage/reload and same-root Current rebinding. A checked target4 remained disabled, Footer phase-next was enabled, and POST/navigation/phase-next returned400 Invalid player without moving Current.

A much smaller ordinary UI reproduces it without any generated-root or manual-Tree interaction: TOP citizen2/wolf1, defaultMAX; Day1/Main staged calculation completes with1/3, Currenth0/revision0. Target1 is checked, all3target radios remain disabled, Footer is enabled and says処刑:未選択. ClickingDay1night produces Invalid player, retainingh0/revision0. This is a real normal-UI bug, not solely a mismatched verification procedure.

Server roles-only HTML correctly marks targets disabled until action details exist; completed HTML correctly enables legal targets and recommends1. static/board_navigation.js applyValues originally replaces numerical cells only. calculate later copies checked flags and enables advance but does not copy disabled states. Browser FormData excludes the disabled checked radio; get(target)=null and the existing Number(null) produces0. The actual production handler in the JS VM fixture captures {revision:0,target:0,reuse_forward:true}. Browser400 and unchanged Current agree. Browser request body was not separately captured; the JSON evidence is from executing the production handler with the observed successful-controls state.

Independent old-version evidence: git-show1da836a static/app.js, static/board_navigation.js and both templates equal the pre-fixde0998c code (ignoring checkoutCRLF). Running the saved oldJS through the3new behavior cases fails3/3 and logs target0. Thus this predates the publication-label optimization. Original logs .artifacts/footer-target-before.log/footer-target-baseline.log. The first fixture had a syntax typo, corrected before any semantic regression result; that malformed run is not counted as product evidence.

## Small correction

applyValues adopts the remote target-radio and status-choice disabled states without replacing the controls/listeners or overwriting checked/manual choices. Existing status refresh becomes reusable and is called after the final recommendation selection. It updates status button text/aria-pressed and Footer preview; disabled checked radios do not count as a valid selection. Pending/unsupported targets stay disabled; no blanket enabling and no client-side calculation of legality.

An existing adjacent-phase history may legitimately be reused with no new target. The form carries only the already-computed phase_forward metadata; status refresh preserves such automatic forward navigation while an explicit invalid/cleared manual choice cannot silently reuse another branch. The server still validates target types/alive IDs and only accepts target0 when its original reuse-forward logic has an existing branch. No NameMap validation is weakened or fallback target invented.

Source static assets copied to public/static with the existing build_vercel.build workflow. No Python model/solver module is changed, preserving ef24b6d and e2c47e1 optimizations.

## Verification

New6JS behavior cases: pending→complete legal widgets/payload1; manual2preserved against recommendation1; role-only invalid checked targets remain blocked; existing forward needs no target; explicit invalid manual choice cannot reuse another branch; stale completion cannot enable newer-revision controls. All80JS tests pass.

New3HTTP cases check actual staged/roles/completed markup, target0rejection without mutation, validtarget1advance with unchanged exact symmetric value, and existing history reuse without target/new occurrence. Combined staged/phase-footer/navigation/deployment26Python tests pass. No old numerical expectations were edited. The unrelated3model/phase failures and mixed-evaluator-day owner-label expectation from prior milestones were not rerun or fixed here. Full repository/large hunter oracle not rerun.

Real browser after local activation completed on normal http://127.0.0.1:18821/main, implementation 5bd611f, server PID25732. No push/external deployment/saved-data deletion. All data created for this check is ephemeral; old saved journals are preserved.


## Normal browser acceptance

The original three-player citizen2/wolf1 case now completes staged calculation with enabled legal controls and a valid checked target. Selecting visible Player2 and using the Footer advances h0/revision0 to h1/revision1 with exact value1/3 and no Invalid player response.

Five-player citizen4/wolf1 verifies a nonterminal adjacent-phase roundtrip: h0 Day1day (7/15) -> h1/revision1 Day1night (1/3) -> h0/revision2 -> existing h1/revision3, then reload preserves h1/revision3. The cumulative result remains7/15. Existing history is reused rather than a new occurrence created. Source/public/live HTTP bytes match for both changed JS assets. Screenshot: .artifacts/footer-target-normal.jpg.

Browser request bodies were not directly recorded: the exact target0 JSON proof is from the production JS handler executed in the bounded Node fixture against the independently observed disabled-control state. The old normal browser did reproduce HTTP400; the new normal browser completed the operations above.

No further optimization was started. No active tests remain. The prior three mathematical/phase expectation disagreements and evaluator-owner label expectation remain outside this fix and unchanged. No approval blocker, push, external deployment or saved-data deletion.
