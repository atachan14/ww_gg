from __future__ import annotations

from dataclasses import dataclass, field

from app.game_tree import NodeState, analyze_node_state
from app.settings import (
    BLACK_ROLE_ORDER,
    DEFAULT_ROLE_COUNTS,
    ROLE_LABELS,
    WHITE_ROLE_ORDER,
    build_regulation_cast,
    build_regulation_roles,
    has_ability_roles,
    is_group_expanded,
    parse_game_config,
)
from app.tree_display import TreeLayout, build_selected_target_tree, build_tree_layout


@dataclass
class PlayerRow:
    index: int
    name: str
    status: str
    status_tone: str
    co: str
    white_total: float
    black_total: float
    white_win_rate: float
    black_win_rate: float
    white_breakdown: dict[str, float] = field(default_factory=dict)
    black_breakdown: dict[str, float] = field(default_factory=dict)


@dataclass
class OptionItem:
    key: str
    label: str
    selected: str
    choices: list[str]


@dataclass
class OptionGroup:
    key: str
    title: str
    items: list[OptionItem]
    expanded: bool = False


@dataclass
class MainPageViewModel:
    day: int
    phase: str
    regulation_cast: str
    white_win_rate: float
    black_win_rate: float
    terminal_winner: str | None
    selected_target: int | None
    players: list[PlayerRow]
    selected_tree_layout: TreeLayout | None
    show_white_details: bool
    show_black_details: bool
    show_ability_rows: bool
    white_detail_columns: list[str]
    black_detail_columns: list[str]
    tactics_groups: list[OptionGroup]
    query_prefix: str
    target_action_label: str


@dataclass
class TopPageViewModel:
    regulation_roles: list[tuple[str, str, int]]
    default_role_counts: dict[str, int]
    tactics_groups: list[OptionGroup]
    rule_groups: list[OptionGroup]


LABEL_VILLAGE = "\u6751"
LABEL_WOLF = "\u72fc"
LABEL_SEER = "\u5360"
LABEL_HUNTER = "\u72e9"
LABEL_EXECUTION_TARGET = "\u51e6\u5211\u5bfe\u8c61"
LABEL_BITE_TARGET = "\u5674\u307f\u5bfe\u8c61"
LABEL_DENY = "\u8a8d\u3081\u306a\u3044"
LABEL_ASSUME_TRUE = "\u771f\u3068\u307f\u306a\u3059"
LABEL_EXPECTED_MAX = "\u671f\u5f85\u52dd\u7387\u6700\u5927\u3092\u9078\u3076"
LABEL_UNIMPLEMENTED = "\u672a\u5b9f\u88c5"
LABEL_NONE = "\u7121"
LABEL_RANDOM_WHITE = "\u30e9\u30f3\u30c0\u30e0\u767d"
LABEL_DAY = "\u663c"
LABEL_NIGHT = "\u591c"
LABEL_EXECUTION = "\u51e6\u5211"
LABEL_BITE = "\u8972\u6483"


def _filter_tactics_groups(groups: list[OptionGroup], role_counts: dict[str, int]) -> list[OptionGroup]:
    has_white_camp = any(role_counts.get(key, 0) > 0 for key in ["villager", "seer", "medium", "hunter"])
    has_black_camp = any(role_counts.get(key, 0) > 0 for key in ["wolf", "madman"])
    has_seer = role_counts.get("seer", 0) > 0

    visible_keys: list[str] = []
    if has_white_camp:
        visible_keys.append("village")
    if has_black_camp:
        visible_keys.append("wolf")
    if has_seer:
        visible_keys.append("seer")

    return [group for group in groups if group.key in visible_keys]


def _filter_rule_groups(groups: list[OptionGroup], role_counts: dict[str, int]) -> list[OptionGroup]:
    visible_keys: list[str] = []
    if role_counts.get("wolf", 0) > 0 or role_counts.get("madman", 0) > 0:
        visible_keys.append("wolf")
    if role_counts.get("seer", 0) > 0:
        visible_keys.append("seer")
    if role_counts.get("hunter", 0) > 0:
        visible_keys.append("hunter")

    return [group for group in groups if group.key in visible_keys]


def build_tactics_groups(values: dict[str, str] | None = None) -> list[OptionGroup]:
    config = parse_game_config(values)
    groups = [
        OptionGroup(
            key="village",
            title=LABEL_VILLAGE,
            items=[
                OptionItem("village_target", LABEL_EXECUTION_TARGET, LABEL_EXPECTED_MAX, [LABEL_EXPECTED_MAX]),
                OptionItem("village_fake_claim", "\u6751\u9a19\u308a", LABEL_DENY, [LABEL_DENY]),
                OptionItem("village_no_counter", "\u5bfe\u6297\u306a\u3057", LABEL_ASSUME_TRUE, [LABEL_ASSUME_TRUE]),
                OptionItem("village_gidra", "\u30ae\u30c9\u30e9", LABEL_DENY, [LABEL_DENY]),
            ],
        ),
        OptionGroup(
            key="wolf",
            title=LABEL_WOLF,
            items=[
                OptionItem("wolf_target", LABEL_BITE_TARGET, LABEL_EXPECTED_MAX, [LABEL_EXPECTED_MAX]),
            ],
        ),
        OptionGroup(
            key="seer",
            title=LABEL_SEER,
            items=[
                OptionItem("seer_option", "\u5360\u306e\u6226\u7565\u30aa\u30d7\u30b7\u30e7\u30f3", LABEL_UNIMPLEMENTED, [LABEL_UNIMPLEMENTED]),
            ],
        ),
    ]
    for group in groups:
        group.expanded = is_group_expanded(config.open_states, "tactics", group.key, default=(group.key == "village"))
        for item in group.items:
            item.selected = config.tactics.get(item.key, item.selected)
    return _filter_tactics_groups(groups, config.role_counts)


def build_rule_groups(values: dict[str, str] | None = None) -> list[OptionGroup]:
    config = parse_game_config(values)
    groups = [
        OptionGroup(
            key="wolf",
            title=LABEL_WOLF,
            items=[
                OptionItem("rule_wolf_self_bite", "\u72fc\u306e\u81ea\u5674", LABEL_NONE, [LABEL_NONE]),
                OptionItem("rule_wolf_skip_bite", "\u72fc\u306e\u7121\u5674", LABEL_NONE, [LABEL_NONE]),
            ],
        ),
        OptionGroup(
            key="seer",
            title=LABEL_SEER,
            items=[
                OptionItem("rule_seer_first_result", "\u521d\u65e5\u306e\u5360\u3044\u7d50\u679c", LABEL_RANDOM_WHITE, [LABEL_RANDOM_WHITE]),
            ],
        ),
        OptionGroup(
            key="hunter",
            title=LABEL_HUNTER,
            items=[
                OptionItem("rule_hunter_consecutive_guard", "\u540c\u4e00\u5bfe\u8c61\u306e\u9023\u7d9a\u8b77\u885b", LABEL_NONE, [LABEL_NONE]),
            ],
        ),
    ]
    for group in groups:
        group.expanded = is_group_expanded(config.open_states, "rules", group.key, default=(group.key == "wolf"))
        for item in group.items:
            item.selected = config.rules.get(item.key, item.selected)
    return _filter_rule_groups(groups, config.role_counts)


def _build_player_rows(node_state: NodeState) -> list[PlayerRow]:
    analysis = analyze_node_state(node_state)
    total_alive = max(analysis.alive_player_count, 1)
    role_counts_alive = {
        key: sum(1 for player in node_state.players if player.alive and player.role_key == key)
        for key in ["seer", "medium", "hunter", "villager", "madman", "wolf"]
    }
    players: list[PlayerRow] = []

    for player in node_state.players:
        if player.alive and player.role_key in {"seer", "medium"}:
            white_total = 100.0
            black_total = 0.0
        elif player.alive:
            white_total = round((analysis.white_alive_count / total_alive) * 100, 1)
            black_total = round((analysis.wolf_alive_count / total_alive) * 100, 1)
        else:
            white_total = 0.0
            black_total = 0.0

        players.append(
            PlayerRow(
                index=player.index,
                name=player.name,
                status=player.status,
                status_tone="execution" if player.status == LABEL_EXECUTION else ("bite" if player.status == LABEL_BITE else ""),
                co=player.co,
                white_total=white_total,
                black_total=black_total,
                white_win_rate=analysis.white_win_rate,
                black_win_rate=analysis.black_win_rate,
                white_breakdown={
                    "seer": 100.0 if player.alive and player.role_key == "seer" else 0.0,
                    "medium": 100.0 if player.alive and player.role_key == "medium" else 0.0,
                    "hunter": round((role_counts_alive["hunter"] / total_alive) * 100, 1) if player.alive else 0.0,
                    "villager": round((role_counts_alive["villager"] / total_alive) * 100, 1) if player.alive else 0.0,
                },
                black_breakdown={
                    "madman": round((role_counts_alive["madman"] / total_alive) * 100, 1) if player.alive else 0.0,
                    "wolf": round((role_counts_alive["wolf"] / total_alive) * 100, 1) if player.alive else 0.0,
                },
            )
        )
    return players


def build_top_page_view_model(values: dict[str, str] | None = None) -> TopPageViewModel:
    config = parse_game_config(values)
    return TopPageViewModel(
        regulation_roles=build_regulation_roles(config.role_counts),
        default_role_counts=DEFAULT_ROLE_COUNTS.copy(),
        tactics_groups=build_tactics_groups(values),
        rule_groups=build_rule_groups(values),
    )


def build_main_page_view_model(
    values: dict[str, str] | None = None,
    node_state: NodeState | None = None,
    selected_target: int | None = None,
    show_white_details: bool = False,
    show_black_details: bool = False,
    query_prefix: str = "",
) -> MainPageViewModel:
    config = parse_game_config(values)
    if node_state is None:
        node_state = NodeState(day=1, phase_key="day", players=[])
    analysis = analyze_node_state(node_state)
    players = _build_player_rows(node_state)
    selected_tree_layout = build_tree_layout(build_selected_target_tree(node_state, selected_target), start_day=node_state.day, start_phase_key=node_state.phase_key) if selected_target else None

    white_detail_columns = [ROLE_LABELS[key] for key in WHITE_ROLE_ORDER if config.role_counts.get(key, 0) > 0]
    black_detail_columns = [ROLE_LABELS[key] for key in BLACK_ROLE_ORDER if config.role_counts.get(key, 0) > 0]

    return MainPageViewModel(
        day=node_state.day,
        phase=LABEL_DAY if node_state.phase_key == "day" else LABEL_NIGHT,
        regulation_cast=build_regulation_cast(config.role_counts),
        white_win_rate=analysis.white_win_rate,
        black_win_rate=analysis.black_win_rate,
        terminal_winner=analysis.terminal_winner,
        selected_target=selected_target,
        players=players,
        selected_tree_layout=selected_tree_layout,
        show_white_details=show_white_details,
        show_black_details=show_black_details,
        show_ability_rows=has_ability_roles(config.role_counts),
        white_detail_columns=white_detail_columns,
        black_detail_columns=black_detail_columns,
        tactics_groups=build_tactics_groups(values),
        query_prefix=query_prefix,
        target_action_label=LABEL_EXECUTION if node_state.phase_key == "day" else LABEL_BITE,
    )
