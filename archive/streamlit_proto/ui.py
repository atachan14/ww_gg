from __future__ import annotations

import streamlit as st

from models import PHASE_LABELS, ROLE_LABELS, AppState
from sample_data import build_sample_players, build_table_columns
from state import save_app_state


ROLE_SUMMARY_LABELS = {
    "villager": "市民",
    "seer": "占",
    "medium": "霊",
    "hunter": "狩",
    "madman": "狂",
    "wolf": "狼",
}


def render_top_screen(state: AppState) -> None:
    st.title("ww_gg")
    st.caption("人狼ゲームの公開情報から期待勝率を確認する v1 骨組み")

    left_col, right_col = st.columns([1.15, 1.0], gap="medium")

    with left_col:
        st.subheader("レギュレーションキャスト")
        _render_regulation_inputs(state)

        st.subheader("レギュレーションルール")
        _render_rule_tabs(state)

    with right_col:
        st.subheader("戦略オプション")
        _render_strategy_tabs(state)

        st.divider()
        if st.button("Day1 昼へ進む", type="primary", use_container_width=True):
            state.current_screen = "main"
            state.node_day = 1
            state.node_phase = "day"
            save_app_state(state)
            st.rerun()


def render_main_screen(state: AppState) -> None:
    _render_screen_style()

    _render_regulation_head(state)
    _render_day_phase(state)
    _render_win_rate_header()
    selected_index = _render_main_table(state)
    state.selected_action_index = selected_index
    _render_node_foot(state)

    st.subheader("戦略オプション")
    _render_strategy_tabs(state)


def _render_screen_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1080px;
            padding-top: 0.65rem;
            padding-bottom: 0.7rem;
        }
        html, body, [class*="css"] {
            font-size: 12px;
        }
        .stMarkdown p, .stCaption, .stText, .stButton button {
            line-height: 1.0;
        }
        h3 {
            margin-top: 0.04rem;
            margin-bottom: 0.16rem;
        }
        div[data-testid="stHorizontalBlock"] {
            gap: 0 !important;
        }
        div[data-testid="stButton"] {
            margin: 0 !important;
        }
        div[data-testid="stButton"] button {
            padding: 0.1rem 0.18rem;
            min-height: 1.55rem;
            font-size: 0.78rem;
            border-radius: 0;
        }
        div[data-testid="stNumberInput"] input,
        div[data-testid="stTextInput"] input {
            font-size: 0.85rem;
        }
        .ww-dayphase {
            margin: 0.02rem 0 0.12rem 0;
            font-size: 1.02rem;
            font-weight: 700;
            white-space: nowrap;
        }
        .ww-rate-wrap {
            margin: 0.02rem 0 0.35rem 0;
            padding: 0;
        }
        .ww-rate-grid {
            display: grid;
            grid-template-columns: 1fr 28px 1fr;
            align-items: center;
            text-align: center;
            gap: 0;
            max-width: 420px;
            margin: 0 auto;
        }
        .ww-rate-label {
            font-size: 0.88rem;
            color: #555;
            font-weight: 600;
        }
        .ww-rate-value {
            font-size: 1.55rem;
            font-weight: 700;
            line-height: 1.0;
        }
        .ww-rate-slash {
            font-size: 1.0rem;
            color: #666;
            font-weight: 600;
        }
        .ww-table-cell {
            border: 1px solid rgba(49, 51, 63, 0.22);
            padding: 0.12rem 0.2rem;
            min-height: 1.55rem;
            display: flex;
            align-items: center;
            white-space: nowrap;
            overflow: hidden;
        }
        .ww-table-cell.center {
            justify-content: center;
            text-align: center;
        }
        .ww-table-cell.left {
            justify-content: flex-start;
            text-align: left;
        }
        .ww-table-header {
            font-weight: 700;
            background: rgba(49, 51, 63, 0.04);
        }
        .ww-ability-note {
            border: 1px solid rgba(49, 51, 63, 0.22);
            border-top: 0;
            padding: 0.1rem 0.22rem;
            min-height: 1.35rem;
            display: flex;
            align-items: center;
            font-size: 0.74rem;
        }
        .ww-foot-spacer {
            height: 0.18rem;
        }
        .ww-small-button button {
            font-size: 0.7rem !important;
            min-height: 1.35rem !important;
            padding: 0.05rem 0.14rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_regulation_head(state: AppState) -> None:
    summary = _build_regulation_summary(state.regulation_roles)
    left_col, button_col, _ = st.columns([6.0, 1.4, 3.6], gap="small")
    with left_col:
        st.markdown(f"**配役 :** {summary}")
    with button_col:
        st.button("ルールを確認", disabled=True, use_container_width=True)


def _render_day_phase(state: AppState) -> None:
    st.markdown(
        f'<div class="ww-dayphase">Day{state.node_day} / {PHASE_LABELS[state.node_phase]}</div>',
        unsafe_allow_html=True,
    )


def _build_regulation_summary(regulation_roles: dict[str, int]) -> str:
    parts = []
    for key in ["seer", "medium", "villager", "hunter", "madman", "wolf"]:
        count = regulation_roles.get(key, 0)
        if count > 0:
            parts.append(f"{ROLE_SUMMARY_LABELS[key]}{count}")
    return " ".join(parts) if parts else "未設定"


def _render_win_rate_header() -> None:
    st.markdown(
        """
        <div class="ww-rate-wrap">
            <div class="ww-rate-grid">
                <div class="ww-rate-label">白陣営勝率</div>
                <div class="ww-rate-slash">/</div>
                <div class="ww-rate-label">黒陣営勝率</div>
                <div class="ww-rate-value">46.7%</div>
                <div></div>
                <div class="ww-rate-value">53.3%</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_regulation_inputs(state: AppState) -> None:
    role_labels = ["村", "占", "霊", "狩", "狂", "狼"]
    role_keys = ["villager", "seer", "medium", "hunter", "madman", "wolf"]
    cols = st.columns(2)
    for idx, (role_key, role_label) in enumerate(zip(role_keys, role_labels)):
        with cols[idx % 2]:
            state.regulation_roles[role_key] = st.number_input(
                role_label,
                min_value=0,
                max_value=20,
                value=state.regulation_roles.get(role_key, 0),
                key=f"regulation_{role_key}",
            )


def _render_rule_tabs(state: AppState) -> None:
    wolf_tab, seer_tab, hunter_tab = st.tabs(["狼", "占", "狩"])

    with wolf_tab:
        state.rule_options["wolf_can_self_bite"] = st.toggle(
            "狼の自噛",
            value=bool(state.rule_options["wolf_can_self_bite"]),
        )
        state.rule_options["wolf_can_skip_bite"] = st.toggle(
            "狼の無噛",
            value=bool(state.rule_options["wolf_can_skip_bite"]),
        )

    with seer_tab:
        current = str(state.rule_options["seer_first_result"])
        options = ["ランダム白", "有", "無"]
        state.rule_options["seer_first_result"] = st.radio(
            "初日の占い結果",
            options=options,
            index=options.index(current) if current in options else 0,
        )

    with hunter_tab:
        state.rule_options["hunter_consecutive_guard"] = st.toggle(
            "同一対象の連続護衛",
            value=bool(state.rule_options["hunter_consecutive_guard"]),
            disabled=state.regulation_roles.get("hunter", 0) == 0,
        )


def _render_strategy_tabs(state: AppState) -> None:
    tab_labels = ["村", "狼"]
    if state.regulation_roles.get("seer", 0) > 0:
        tab_labels.append("占")

    tabs = st.tabs(tab_labels)
    for label, tab in zip(tab_labels, tabs):
        with tab:
            options = state.strategy_options[label]
            for option_name, option_value in options.items():
                if isinstance(option_value, bool):
                    options[option_name] = st.toggle(
                        option_name,
                        value=option_value,
                        key=f"strategy_{label}_{option_name}",
                    )
                else:
                    st.text_input(
                        option_name,
                        value=str(option_value),
                        disabled=True,
                        key=f"strategy_{label}_{option_name}",
                    )


def _render_main_table(state: AppState) -> int:
    players = build_sample_players()
    white_columns, black_columns = build_table_columns(state.regulation_roles)

    show_white_details = st.session_state.get("show_white_details", False)
    show_black_details = st.session_state.get("show_black_details", False)

    columns_config = [
        ("#", 0.34),
        ("名前", 0.95),
        ("生死", 0.56),
        ("CO", 0.56),
        ("白陣営%", 0.78),
    ]
    if show_white_details:
        columns_config.extend((ROLE_LABELS[key], 0.72) for key in white_columns)
    columns_config.append(("黒陣営%", 0.78))
    if show_black_details:
        columns_config.extend((ROLE_LABELS[key], 0.72) for key in black_columns)
    columns_config.extend(
        [
            ("白勝率", 0.78),
            ("黒勝率", 0.78),
            ("対象", 0.62),
        ]
    )

    _render_table_header(columns_config, show_white_details, show_black_details)

    for player in players:
        _render_player_row(player, columns_config, white_columns, black_columns, state)
        _render_ability_gap_row(player.index, columns_config)

    return state.selected_action_index


def _render_table_header(
    columns_config: list[tuple[str, float]],
    show_white_details: bool,
    show_black_details: bool,
) -> None:
    cols = st.columns([width for _, width in columns_config], gap="small")
    for col, (label, _) in zip(cols, columns_config):
        if label == "白陣営%":
            if col.button("白陣営%", key="toggle_white_columns", use_container_width=True):
                st.session_state["show_white_details"] = not show_white_details
                st.rerun()
        elif label == "黒陣営%":
            if col.button("黒陣営%", key="toggle_black_columns", use_container_width=True):
                st.session_state["show_black_details"] = not show_black_details
                st.rerun()
        else:
            col.markdown(f'<div class="ww-table-cell ww-table-header center">{label}</div>', unsafe_allow_html=True)


def _render_player_row(player, columns_config, white_columns, black_columns, state: AppState) -> None:
    cols = st.columns([width for _, width in columns_config], gap="small")
    col_idx = 0

    _cell(cols[col_idx], str(player.index), center=True)
    col_idx += 1
    _cell(cols[col_idx], player.name, left=True)
    col_idx += 1
    _cell(cols[col_idx], player.status, center=True)
    col_idx += 1
    _cell(cols[col_idx], player.co_display, center=True)
    col_idx += 1
    _cell(cols[col_idx], f"{player.white_total:.1f}%", center=True)
    col_idx += 1

    if st.session_state.get("show_white_details", False):
        for key in white_columns:
            _cell(cols[col_idx], f"{player.white_breakdown.get(key, 0.0):.1f}%", center=True)
            col_idx += 1

    _cell(cols[col_idx], f"{player.black_total:.1f}%", center=True)
    col_idx += 1

    if st.session_state.get("show_black_details", False):
        for key in black_columns:
            _cell(cols[col_idx], f"{player.black_breakdown.get(key, 0.0):.1f}%", center=True)
            col_idx += 1

    _cell(cols[col_idx], f"{player.selected_white_win_rate:.1f}%", center=True)
    col_idx += 1
    _cell(cols[col_idx], f"{player.selected_black_win_rate:.1f}%", center=True)
    col_idx += 1

    is_selected = state.selected_action_index == player.index
    if cols[col_idx].button(
        "選択",
        key=f"select_player_{player.index}",
        type="primary" if is_selected else "secondary",
        use_container_width=True,
    ):
        state.selected_action_index = player.index
        save_app_state(state)
        st.rerun()


def _render_ability_gap_row(player_index: int, columns_config: list[tuple[str, float]]) -> None:
    cols = st.columns([width for _, width in columns_config], gap="small")
    _cell(cols[0], "", center=True)
    is_open = st.session_state.get(f"ability_open_{player_index}", False)
    button_label = "能力 ▲" if is_open else "能力 ▼"
    with cols[1]:
        st.markdown('<div class="ww-small-button">', unsafe_allow_html=True)
        clicked = st.button(button_label, key=f"toggle_ability_{player_index}", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    if clicked:
        st.session_state[f"ability_open_{player_index}"] = not is_open
        st.rerun()

    for idx in range(2, len(cols)):
        if idx == 2 and is_open:
            cols[idx].markdown(
                f'<div class="ww-ability-note">player{player_index} の能力結果入力欄をここに追加予定です。</div>',
                unsafe_allow_html=True,
            )
        else:
            cols[idx].markdown('<div class="ww-table-cell"></div>', unsafe_allow_html=True)


def _render_node_foot(state: AppState) -> None:
    st.markdown('<div class="ww-foot-spacer"></div>', unsafe_allow_html=True)
    left_col, spacer_col, right_col1, right_col2 = st.columns([1.0, 5.6, 1.1, 1.1], gap="small")
    with left_col:
        if st.button("TOP", use_container_width=True):
            state.current_screen = "top"
            save_app_state(state)
            st.rerun()
    with right_col1:
        if state.node_day > 1 or state.node_phase != "day":
            if st.button("戻る", use_container_width=True):
                state.node_day = max(1, state.node_day - 1)
                state.node_phase = "day"
                save_app_state(state)
                st.rerun()
        else:
            st.button("戻る", disabled=True, use_container_width=True)
    with right_col2:
        if st.button("進む", type="primary", use_container_width=True):
            _advance_node(state)
            save_app_state(state)
            st.rerun()


def _cell(column, text: str, center: bool = False, left: bool = False) -> None:
    align = "center" if center or not left else "left"
    column.markdown(f'<div class="ww-table-cell {align}">{text}</div>', unsafe_allow_html=True)


def _advance_node(state: AppState) -> None:
    if state.node_phase == "day":
        state.node_phase = "night"
    else:
        state.node_phase = "day"
        state.node_day += 1
