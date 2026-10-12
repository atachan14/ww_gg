# Board-owned Log / late-role disclosure / quiet controls checkpoint

Unpublished independent worktree based on production f737dd12091fac85744de32a1931b1f005a25b1c. No future modules copied, no commit/push. Original G working tree untouched.

## Current implementation

The old log used linear history slot indexes and displayed every batch. It had no stable Board/branch ownership and back discarded later batches. The new saved graph has stable Board IDs, parent/children, branch IDs, normalized action/policy edges, local batches and per-node input revision. Same day/night are distinct nodes. Back retains the branch registry; selecting the same transition restores its node/local events, while another transition creates a sibling that cannot inherit sibling events.

BoardLog renders current-node local events only. Table/calculation reduce effective declarations on the selected ancestor path. A child withdrawal is a child event; it does not erase the parent's local events. Confirmed local content changes retire the owner's existing descendant subtree. Old nodes are inactive and disconnected from the current children list; advancing recreates fresh IDs and never reapplies retired child inputs. Unrelated sibling subtrees stay active. Every confirmed content change protects the owner/ancestor/affected-descendant input snapshot in an archive generation, including owner-only changes. No stored numeric cache is reused across inherited input revision changes. Saved v1/legacy records migrate, keeping unknown-order markers.

Drafts and preview responses bind Board ID, confirmed revision and inherited input revision. Old raw drafts are bound once during migration. Cross-Board draft requests reject. Preview does not add history; commit uses the same atomic proposal.

Result acquisition day is separate from the public owner's Board/day/phase. Late seer CO exposes Day1 through the current day; hand-entered past reports condition the posterior at their public slot, validate their acquisition-time roster, and obey truth-side initial normal/random-white/none. Initial-none or black declarations are not blanket input bans: fake reports retain constant likelihood and truth candidates are excluded when inconsistent. Medium rows derive from executions (Day1 --), including manually disclosed earlier results; future medium generation was not changed. Citizen/nonability roles generate no empty result row. Current effective-declaration modeling is retained, without introducing future private-history Pending.

## UI

COなし is --. Closed CO/result selectors have no border/background/shadow, subtle hover, visible keyboard outline, unchanged >=28px hit area; popup options remain white/readable, disabled opacity .6. Update has no shadow and only dirty-enabled uses calm red #a94747; no red Table frame. Footer left controls have quieter border/background/shadow with hover/focus and hit area. Main cast omits zero-count roles; TOP zero-count editing remains. Log tokens use 占い Day1：Player2＝白; no owner/timestamp explanations are added.

## Evidence

200 regression tests pass, including 13 Board ownership/disclosure/generation tests. PC Edge passed same-day phase IDs, sibling isolation, revisit, local-only log, inherited effective Table, Day2 late CO with Day1/2 input, preview/commit equality, cancel/manual revert, keyboard focus, 390px viewport and popup/disabled appearance.
Day3 late CO entered Day1 white2 / Day2 white3 / Day3 black6, live preview and commit both 20/21. This is not 1: the existing model still permits a living fake claimant with an already-dead true seer. Old-day target edits keep former local events; cancellation and cold-cookie restore preserve current Board ownership.

D:/CodexTemp/ww_gg-board-owned-qa-20261012/browser/board-owned-browser-results.json
D:/CodexTemp/ww_gg-board-owned-qa-20261012/browser-day3/board-day3-browser-results.json

## Confirmed descendant policy

Only the owner Board can edit/delete its local LogItem. A later Board changes inherited information by a new local withdraw/change event. Draft preview does not retire or mutate confirmed descendants. Table update and LogItem edit/delete commit retire affected descendants only; no-op, cancellation and validation failure preserve them. Old snapshots remain archived, but are not current-tree nodes or a source for automatic hand-input reapplication. Forward uses the existing transition path to create fresh Boards. New nodes inherit the parent's input version.

The previous needs-review/keep-active proposal is withdrawn. There is no remaining semantic decision. Publication still requires separate approval.

Final generation Edge evidence:
D:/CodexTemp/ww_gg-board-owned-qa-20261012/browser-generation-final/board-generation-browser-results.json
Preview/commit owner value was 2/3; affected children retired only on commit, unrelated sibling node and its black report stayed byte-identical, new forward ID used the new white5 evidence, cold cookie restored active tree and archives, and terminal inherited details were readonly.
