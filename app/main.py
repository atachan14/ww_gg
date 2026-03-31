from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.core.game_tree import build_initial_node_state
from app.persistent_tree import build_stored_tree_record
from app.runtime_config import load_runtime_config
from app.storage import build_tree_storage
from app.settings import (
    REGULATION_ROLE_ORDER,
    SESSION_KEY,
    SESSION_SECRET_KEY,
    TREE_SESSION_KEY,
    parse_game_config,
    parse_role_counts,
    pick_session_values,
)
from app.web.tree_display import build_tree_layout
from app.modes.parallel.tree_state import (
    advance_current_path,
    build_tree,
    create_tree_session,
    deserialize_tree_session,
    find_node,
    fork_current_node_with_claims,
    fork_current_node_with_tactics,
    get_current_node,
    rewind_current_path,
    serialize_tree_session,
    set_current_target,
    set_node_claims,
)
from app.web.view_models import build_main_page_view_model, build_top_page_view_model


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="ww_gg")
runtime_config = load_runtime_config()
app.state.runtime_config = runtime_config
app.state.tree_storage = build_tree_storage(runtime_config)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _get_tree_session(request: Request, values: dict[str, str]):
    role_counts = parse_role_counts(values)
    return deserialize_tree_session(request.session.get(TREE_SESSION_KEY), role_counts)


def _save_tree_record(request: Request, tree_session) -> None:
    config = parse_game_config(request.session.get(SESSION_KEY, {}))
    tree_record = build_stored_tree_record(
        tree_session,
        role_counts=config.role_counts,
        rules=config.rules,
        ui_state=config.view_values,
    )
    request.app.state.tree_storage.save_tree(tree_record)


def _ensure_tree_session(request: Request, values: dict[str, str]):
    tree_session = _get_tree_session(request, values)
    if request.session.get(TREE_SESSION_KEY) is None:
        request.session[TREE_SESSION_KEY] = serialize_tree_session(tree_session)
        _save_tree_record(request, tree_session)
    return tree_session


@app.get("/", response_class=HTMLResponse)
def top_page(request: Request) -> HTMLResponse:
    request.session.pop(TREE_SESSION_KEY, None)
    values = request.session.get(SESSION_KEY, {})
    return templates.TemplateResponse(
        request,
        "top.html",
        {
            "page_title": "ww_gg | Top",
            "top": build_top_page_view_model(values),
        },
    )


@app.post("/main")
async def save_top_config(request: Request) -> RedirectResponse:
    form = await request.form()
    values = {key: str(value) for key, value in form.items()}
    session_values = pick_session_values(values)
    request.session[SESSION_KEY] = session_values
    tree_session = create_tree_session(build_initial_node_state(parse_role_counts(session_values)))
    request.session[TREE_SESSION_KEY] = serialize_tree_session(tree_session)
    _save_tree_record(request, tree_session)
    return RedirectResponse(url="/main", status_code=303)


@app.post("/main/advance")
async def advance_main_node(request: Request) -> RedirectResponse:
    form = await request.form()
    values = request.session.get(SESSION_KEY, {})
    tree_session = _ensure_tree_session(request, values)

    selected_target_raw = str(form.get("selected_target", "")).strip()
    action = str(form.get("action", "advance"))

    current = get_current_node(tree_session)
    source_players = current.node_state.players if current is not None else tree_session.root_state.players
    claims_by_player: dict[int, list[str]] = {}
    for player in source_players:
        claims_by_player[player.index] = [
            role_key
            for role_key in REGULATION_ROLE_ORDER
            if str(form.get(f"co_{player.index}_{role_key}", "")) == "1"
        ]
    set_node_claims(tree_session, tree_session.current_node_id, claims_by_player)

    if current is not None and current.kind == "choice" and selected_target_raw.isdigit():
        set_current_target(tree_session, int(selected_target_raw))

    if action == "advance":
        advance_current_path(tree_session)
    elif action == "back":
        rewind_current_path(tree_session)

    request.session[TREE_SESSION_KEY] = serialize_tree_session(tree_session)
    _save_tree_record(request, tree_session)
    return RedirectResponse(url="/main", status_code=303)


@app.post("/main/jump")
async def jump_main_node(request: Request) -> RedirectResponse:
    form = await request.form()
    values = request.session.get(SESSION_KEY, {})
    tree_session = _ensure_tree_session(request, values)
    node_id = str(form.get("node_id", "")).strip()
    tree_root = build_tree(tree_session)
    if find_node(tree_root, node_id) is not None:
        tree_session.current_node_id = node_id
        request.session[TREE_SESSION_KEY] = serialize_tree_session(tree_session)
        _save_tree_record(request, tree_session)
    return RedirectResponse(url="/main", status_code=303)


@app.post("/session/ui")
async def update_session_ui(request: Request) -> JSONResponse:
    payload = await request.json()
    key = str(payload.get("key", ""))
    value = str(payload.get("value", "0"))
    session_values = dict(request.session.get(SESSION_KEY, {}))
    session_values.update(pick_session_values({key: value}))
    request.session[SESSION_KEY] = session_values
    return JSONResponse({"ok": True})


@app.post("/main/tactics")
async def update_main_tactics(request: Request) -> JSONResponse:
    payload = await request.json()
    key = str(payload.get("key", "")).strip()
    value = str(payload.get("value", "")).strip()
    values = request.session.get(SESSION_KEY, {})
    tree_session = _ensure_tree_session(request, values)
    current = get_current_node(tree_session)
    tactics = current.node_state.tactics.copy() if current is not None else {}
    if key:
        tactics[key] = value
        fork_current_node_with_tactics(tree_session, tactics)
        request.session[TREE_SESSION_KEY] = serialize_tree_session(tree_session)
        _save_tree_record(request, tree_session)
    return JSONResponse({"ok": True})


@app.post("/main/claims")
async def update_main_claims(request: Request) -> JSONResponse:
    payload = await request.json()
    player_index = int(payload.get("player_index", 0))
    role_key = str(payload.get("role_key", "")).strip()
    checked = bool(payload.get("checked", False))
    values = request.session.get(SESSION_KEY, {})
    tree_session = _ensure_tree_session(request, values)
    current = get_current_node(tree_session)
    source_players = current.node_state.players if current is not None else tree_session.root_state.players
    claims_by_player: dict[int, list[str]] = {player.index: player.claim_role_keys.copy() for player in source_players}
    role_keys = claims_by_player.get(player_index, [])
    if checked:
        if role_key and role_key not in role_keys:
            role_keys.append(role_key)
    else:
        role_keys = [current_role for current_role in role_keys if current_role != role_key]
    claims_by_player[player_index] = role_keys
    fork_current_node_with_claims(tree_session, claims_by_player)
    request.session[TREE_SESSION_KEY] = serialize_tree_session(tree_session)
    _save_tree_record(request, tree_session)
    return JSONResponse({"ok": True})


@app.get("/main", response_class=HTMLResponse)
def main_page(
    request: Request,
    white_details: int | None = None,
    black_details: int | None = None,
) -> HTMLResponse:
    values = request.session.get(SESSION_KEY, {})
    config = parse_game_config(values)
    effective_white_details = bool(int(config.view_values.get("main_white_details", "0"))) if white_details is None else bool(white_details)
    effective_black_details = bool(int(config.view_values.get("main_black_details", "0"))) if black_details is None else bool(black_details)
    tree_session = _ensure_tree_session(request, values)
    tree_root = build_tree(tree_session)
    current_node = get_current_node(tree_session)
    current_state = current_node.node_state if current_node is not None else tree_session.root_state
    selected_target = current_node.selected_target if current_node is not None and current_node.kind == "choice" else None
    tree_layout = build_tree_layout(
        tree_root,
        current_node_id=tree_session.current_node_id,
        start_day=tree_session.root_state.day,
        start_phase_key=tree_session.root_state.phase_key,
    )
    return templates.TemplateResponse(
        request,
        "main.html",
        {
            "page_title": "ww_gg | Main",
            "main": build_main_page_view_model(
                values=values,
                node_state=current_state,
                selected_target=selected_target,
                selected_tree_layout=tree_layout,
                show_white_details=effective_white_details,
                show_black_details=effective_black_details,
                query_prefix="",
                can_go_back=(tree_session.current_node_id != tree_session.root_node_id),
                white_alive_count_override=current_node.white_alive_count if current_node is not None else None,
                wolf_alive_count_override=current_node.wolf_alive_count if current_node is not None else None,
                terminal_winner_override=current_node.terminal_winner if current_node is not None else None,
            ),
        },
    )
