# Normal UI with exact generated Current

Run from the repository root:

    python -X utf8 dev_previews/run_current_app.py

Open http://127.0.0.1:18803/ . On TOP set citizens3, seers1, wolves1,
mediums0, hunters0; keep other defaults. This is the normal app, with local
GameTree enabled. It uses a separate cookie name to preserve the original
18801 session. Do not start over an occupied port.

Click a one-line item to inspect/expand. Its right arrow navigates that exact
physical Board into the normal Current views. Refresh/back/forward retain the
exact cursor. Generated Current snapshots retain their source recipe and are
read-only; root arrow returns to the unchanged editable saved Board.

The server PID/logs are recorded in .artifacts/current-app-server.* outside Git.
