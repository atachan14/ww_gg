# Isolated compact GameTree comparison

Local preview: http://127.0.0.1:18802/

A thin outline and B borderless use the exact same generated six-Board sample.
Item fields are provisional: Board ID, living count, village win value.
Day/phase appears only in column headers. Item click or keyboard activation
selects that representative Board; a shared line shows actual alive/history and
named equivalent members. There are no selectors or nested item controls.

`build_sample.py` uses an isolated Flask test client over the existing actual
GameTree/Closed engine, not the user's saved session. Fixture: citizen3/seer1/
wolf1, all latent, default random-white, MAX daytime/night/fake-report, no self
bite. Edge probabilities are configured choice-group probability multiplied by
conditional physical branch probability, not Board values. Full named member
masses remain in sample.json; display sharing uses only established engine
renaming groups. No solver or main-view changes are part of this comparison.

From the repo root, run the installed Python with `-X utf8` and this builder:

    python -X utf8 dev_previews/compact_tree/build_sample.py
    python -X utf8 -m http.server 18802 --bind 127.0.0.1 --directory dev_previews/compact_tree

The preview is self-contained index.html with no APIs, external assets or
session cookies; the server is independent of the production-view local app.
Only start on an unoccupied owned port. The current dedicated preview PID is
recorded outside version control in .artifacts/compact-tree-server.pid.
