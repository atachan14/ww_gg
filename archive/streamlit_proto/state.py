from __future__ import annotations

import streamlit as st

from models import AppState


APP_STATE_KEY = "app_state"


def ensure_app_state() -> AppState:
    if APP_STATE_KEY not in st.session_state:
        st.session_state[APP_STATE_KEY] = AppState()
    return st.session_state[APP_STATE_KEY]


def save_app_state(state: AppState) -> None:
    st.session_state[APP_STATE_KEY] = state

