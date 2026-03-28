from __future__ import annotations

import streamlit as st

from state import ensure_app_state
from ui import render_main_screen, render_top_screen


st.set_page_config(
    page_title="ww_gg",
    page_icon="W",
    layout="wide",
)


def main() -> None:
    state = ensure_app_state()

    if state.current_screen == "top":
        render_top_screen(state)
    else:
        render_main_screen(state)


if __name__ == "__main__":
    main()
