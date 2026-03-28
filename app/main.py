from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.game_tree import advance_node_state, build_initial_node_state, deserialize_node_state, serialize_node_state
from app.settings import (
    NODE_SESSION_KEY,
    SELECTED_TARGET_SESSION_KEY,
    SESSION_KEY,
    SESSION_SECRET_KEY,
    parse_role_counts,
    pick_session_values,
)
from app.view_models import build_main_page_view_model, build_top_page_view_model


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="ww_gg")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _get_node_state(request: Request, values: dict[str, str]) -> object:
    role_counts = parse_role_counts(values)
    return deserialize_node_state(request.session.get(NODE_SESSION_KEY), role_counts)


@app.get("/", response_class=HTMLResponse)
def top_page(request: Request) -> HTMLResponse:
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
    request.session[NODE_SESSION_KEY] = serialize_node_state(build_initial_node_state(parse_role_counts(session_values)))
    request.session[SELECTED_TARGET_SESSION_KEY] = ""
    return RedirectResponse(url="/main", status_code=303)


@app.post("/main/advance")
async def advance_main_node(request: Request) -> RedirectResponse:
    form = await request.form()
    values = request.session.get(SESSION_KEY, {})
    node_state = _get_node_state(request, values)
    selected_target_raw = str(form.get("selected_target", "")).strip()
    action = str(form.get("action", "advance"))
    request.session[SELECTED_TARGET_SESSION_KEY] = selected_target_raw

    if action == "advance" and selected_target_raw.isdigit():
        next_state = advance_node_state(node_state, int(selected_target_raw))
        request.session[NODE_SESSION_KEY] = serialize_node_state(next_state)
        request.session[SELECTED_TARGET_SESSION_KEY] = ""
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


@app.get("/main", response_class=HTMLResponse)
def main_page(
    request: Request,
    white_details: int = 0,
    black_details: int = 0,
) -> HTMLResponse:
    values = request.session.get(SESSION_KEY, {})
    node_state = _get_node_state(request, values)
    selected_raw = str(request.session.get(SELECTED_TARGET_SESSION_KEY, "")).strip()
    selected_target = int(selected_raw) if selected_raw.isdigit() else None
    return templates.TemplateResponse(
        request,
        "main.html",
        {
            "page_title": "ww_gg | Main",
            "main": build_main_page_view_model(
                values=values,
                node_state=node_state,
                selected_target=selected_target,
                show_white_details=bool(white_details),
                show_black_details=bool(black_details),
                query_prefix="",
            ),
        },
    )
