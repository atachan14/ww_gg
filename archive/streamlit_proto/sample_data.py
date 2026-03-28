from __future__ import annotations

from models import BLACK_ROLE_KEYS, PlayerRow, TreeNodeSummary, WHITE_ROLE_KEYS


def build_sample_players() -> list[PlayerRow]:
    return [
        PlayerRow(
            index=1,
            name="player1",
            co_roles=["占"],
            white_breakdown={"seer": 100.0, "medium": 0.0, "hunter": 0.0, "villager": 0.0},
            black_breakdown={"madman": 0.0, "wolf": 0.0},
            selected_white_win_rate=72.0,
            selected_black_win_rate=28.0,
        ),
        PlayerRow(
            index=2,
            name="player2",
            co_roles=["霊"],
            white_breakdown={"seer": 0.0, "medium": 100.0, "hunter": 0.0, "villager": 0.0},
            black_breakdown={"madman": 0.0, "wolf": 0.0},
            selected_white_win_rate=68.0,
            selected_black_win_rate=32.0,
        ),
        PlayerRow(
            index=3,
            name="player3",
            co_roles=[],
            white_breakdown={"seer": 0.0, "medium": 0.0, "hunter": 0.0, "villager": 60.0},
            black_breakdown={"madman": 0.0, "wolf": 40.0},
            selected_white_win_rate=46.7,
            selected_black_win_rate=53.3,
        ),
        PlayerRow(
            index=4,
            name="player4",
            co_roles=[],
            white_breakdown={"seer": 0.0, "medium": 0.0, "hunter": 0.0, "villager": 60.0},
            black_breakdown={"madman": 0.0, "wolf": 40.0},
            selected_white_win_rate=46.7,
            selected_black_win_rate=53.3,
        ),
        PlayerRow(
            index=5,
            name="player5",
            co_roles=[],
            white_breakdown={"seer": 0.0, "medium": 0.0, "hunter": 0.0, "villager": 60.0},
            black_breakdown={"madman": 0.0, "wolf": 40.0},
            selected_white_win_rate=46.7,
            selected_black_win_rate=53.3,
        ),
    ]


def build_sample_tree() -> list[TreeNodeSummary]:
    return [
        TreeNodeSummary(
            node_id="day1",
            label="Day1 昼",
            action_label="player3 を処刑",
            immediate_white_win_rate=20.0,
            total_white_win_rate=46.7,
        ),
        TreeNodeSummary(
            node_id="night1",
            label="Day1 夜",
            action_label="player1 を噛み",
            immediate_white_win_rate=0.0,
            total_white_win_rate=33.0,
        ),
        TreeNodeSummary(
            node_id="day2",
            label="Day2 昼",
            action_label="player4 を処刑",
            immediate_white_win_rate=33.0,
            total_white_win_rate=33.0,
        ),
    ]


def build_table_columns(regulation_roles: dict[str, int]) -> tuple[list[str], list[str]]:
    white_columns = [key for key in WHITE_ROLE_KEYS if regulation_roles.get(key, 0) > 0]
    black_columns = [key for key in BLACK_ROLE_KEYS if regulation_roles.get(key, 0) > 0]
    return white_columns, black_columns

