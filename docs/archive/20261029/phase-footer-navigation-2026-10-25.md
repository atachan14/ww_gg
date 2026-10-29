# Branch-aware phase Footer navigation

Footer Help was conditioned on the responding Flask endpoint: the initial/main page hid it, while navigation/preview HTML replacement reintroduced it. The shared Footer include now contains no link; Help remains in the site header/pages. BoardOverview targets the document top and any outer scroll owner, preserving internal Table/Tree pan. BoardInfo/GameTree anchors and other Footer information remain.

## Exact navigation rules

Use navigational occurrences, not interned solver-state identity, global recency or `_forward` pointers:
- Previous: walk actual ancestors past all same-phase updates, selecting the nearest occurrence in the immediately previous phase. This naturally returns its final ancestral update, or its start if no update lies on that path. Day1-day updates have no previous-phase button: settings return and Day1-night only.
- Next: traverse only descendants of the current occurrence in its own phase and the immediately next phase. Prefer next-phase update occurrences; choose the last-created one by validated append order. If none, choose the last-created reachable start Board. Never select a sibling outside the current ancestry branch. From a shared ancestor where multiple branches are genuinely reachable, last-created applies within that reachable set. Do not traverse through a later phase and then select globally.
- Looking up targets never creates a future. If a next phase already exists, Footer moves to it without adding an occurrence. If absent, the existing explicit execution/attack action can create it. An explicit manual target change still requests a new action branch rather than blindly reusing a stored forward; this preserves existing action intent. Existing automatic morning publication is applied by its established generator as needed during explicit advancement, not by target lookup.

Footer uses `phase-back/phase-next`. Immediate `navigation/back/forward` API compatibility is retained for other callers. Parent/forward metadata is retained and new phase-specific fields drive the ordinary persistent Footer. Source values, Q/P, policies, mappings, manual0 weights and solver transitions are untouched.

## Verification

112 Python tests passed16.390s;63 JS tests passed0.280s. New tests cover A→A2→night with newer parallelB, multi-update next phase, competing reachable branches versus unrelated siblings, start fallback, absent future/no materialization, same-phase update buttons, exact source roundtrip and cold restore. Existing navigation/game tests retain their numerical/settled-mass assertions. One initial new Day2 fixture used contradictory CO evidence and was corrected to a legal CO withdrawal retaining its old report; expectations about targets/occurrence counts were not weakened.

Real isolated Edge + normal ownership flags passed actual Footer form clicks (verified phase-* network operations), partial HTML replacement, ancestry versus newerB, next latest update, unchanged occurrence count on reuse, reload/back, Help absent in Footer and present in header, document-top scroll and unchanged Tree horizontal pan. Desktop1440 and narrow390 screenshots inspected. No console exceptions or failed assets. Artifacts `.artifacts/phase-footer-{focused,regressions,js,browser}.log`, `phase-footer-{desktop,mobile}.png`. Existing build synchronized public assets. No unrelated fixture normalization, external publication or saved-data deletion. Normal18821 activation follows the verified commit.
