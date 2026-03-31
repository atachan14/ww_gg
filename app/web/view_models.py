from __future__ import annotations

from dataclasses import dataclass, field

from app.core.calculation import evaluate_count_state, get_terminal_winner
from app.core.game_tree import HIDDEN_CO_LABEL, NodeState, build_co_label, analyze_node_state
from app.settings import (
    BLACK_ROLE_ORDER,
    DEFAULT_ROLE_COUNTS,
    REGULATION_ROLE_ORDER,
    ROLE_LABELS,
    WHITE_ROLE_ORDER,
    build_regulation_cast,
    build_regulation_roles,
    has_ability_roles,
    is_group_expanded,
    parse_game_config,
)
from app.web.tree_display import TreeLayout


@dataclass
class PlayerRow:
    index: int
    name: str
    status: str
    status_tone: str
    co: str
    claim_role_keys: list[str]
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
    white_detail_columns: list[tuple[str, str]]
    black_detail_columns: list[tuple[str, str]]
    co_role_options: list[tuple[str, str]]
    tactics_groups: list[OptionGroup]
    query_prefix: str
    target_action_label: str
    can_go_back: bool


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
LABEL_BITE_TARGET = "\u8972\u6483\u5bfe\u8c61"
LABEL_DENY = "\u8a8d\u3081\u306a\u3044"
LABEL_ASSUME_TRUE = "\u771f\u3068\u307f\u306a\u3059"
LABEL_NO_COUNTER_STRICT = "\u5168\u3066\u771f"
LABEL_NO_COUNTER_FILLED = "\u6e80\u54e1\u3067\u771f"
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
                OptionItem("village_no_counter", "\u5bfe\u6297\u306a\u3057", LABEL_NO_COUNTER_FILLED, [LABEL_NO_COUNTER_STRICT, LABEL_NO_COUNTER_FILLED]),
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


def _build_claim_probabilities(node_state: NodeState, role_counts: dict[str, int], no_counter_mode: str) -> dict[int, dict[str, float]]:
    alive_players = [player for player in node_state.players if player.alive]
    probabilities = {player.index: {key: 0.0 for key in REGULATION_ROLE_ORDER} for player in alive_players}
    reserved_black = {player.index: 0.0 for player in alive_players}
    hidden_players = [player for player in alive_players if not player.claim_role_keys]
    total_black_count = sum(role_counts.get(role_key, 0) for role_key in BLACK_ROLE_ORDER)
    alive_count = max(len(alive_players), 1)

    def distribute_hidden(role_key: str, total_amount: float) -> None:
        if total_amount <= 0 or not hidden_players:
            return
        share = total_amount / len(hidden_players)
        for player in hidden_players:
            probabilities[player.index][role_key] += share

    for role_key in WHITE_ROLE_ORDER:
        role_count = float(role_counts.get(role_key, 0))
        if role_count <= 0:
            continue

        claimers = [player for player in alive_players if role_key in player.claim_role_keys]
        if not claimers:
            distribute_hidden(role_key, role_count)
            continue

        claimant_count = len(claimers)
        if claimant_count > role_count:
            real_share = role_count / claimant_count
            for player in claimers:
                probabilities[player.index][role_key] += real_share
                reserved_black[player.index] += max(0.0, 1.0 - real_share)
            continue

        if claimant_count < role_count and no_counter_mode == LABEL_NO_COUNTER_FILLED:
            claim_real_share = max(0.0, 1.0 - (total_black_count / alive_count))
            for player in claimers:
                probabilities[player.index][role_key] += claim_real_share
                reserved_black[player.index] += max(0.0, 1.0 - claim_real_share)
            distribute_hidden(role_key, max(0.0, role_count - (claimant_count * claim_real_share)))
            continue

        for player in claimers:
            probabilities[player.index][role_key] += 1.0
        distribute_hidden(role_key, max(0.0, role_count - claimant_count))

    black_total = float(total_black_count)
    if black_total <= 0:
        return probabilities

    reserved_total = sum(reserved_black.values())
    for player in alive_players:
        if reserved_black[player.index] <= 0:
            continue
        for role_key in BLACK_ROLE_ORDER:
            probabilities[player.index][role_key] += reserved_black[player.index] * role_counts.get(role_key, 0) / black_total

    remaining_black_total = max(0.0, black_total - reserved_total)
    if remaining_black_total <= 0:
        return probabilities

    capacities: dict[int, float] = {}
    total_capacity = 0.0
    for player in alive_players:
        used = sum(probabilities[player.index].values())
        capacity = max(0.0, 1.0 - used)
        capacities[player.index] = capacity
        total_capacity += capacity

    if total_capacity <= 0:
        return probabilities

    for role_key in BLACK_ROLE_ORDER:
        role_count = float(role_counts.get(role_key, 0))
        role_remaining = max(0.0, role_count - sum(probabilities[player.index][role_key] for player in alive_players))
        if role_remaining <= 0:
            continue
        for player in alive_players:
            probabilities[player.index][role_key] += role_remaining * capacities[player.index] / total_capacity

    return probabilities


def _build_player_rows(node_state: NodeState, role_counts: dict[str, int], village_no_counter_mode: str, white_alive_count: int | None = None, wolf_alive_count: int | None = None) -> list[PlayerRow]:
    analysis = analyze_node_state(node_state)
    white_alive_count = analysis.white_alive_count if white_alive_count is None else white_alive_count
    wolf_alive_count = analysis.wolf_alive_count if wolf_alive_count is None else wolf_alive_count
    claim_probabilities = _build_claim_probabilities(node_state, role_counts, village_no_counter_mode)
    players: list[PlayerRow] = []
    white_win_rate, black_win_rate = evaluate_count_state(white_alive_count, wolf_alive_count, node_state.phase_key)

    for player in node_state.players:
        role_probs = claim_probabilities.get(player.index, {key: 0.0 for key in REGULATION_ROLE_ORDER})
        white_breakdown = {key: role_probs.get(key, 0.0) * 100 for key in WHITE_ROLE_ORDER}
        black_breakdown = {key: role_probs.get(key, 0.0) * 100 for key in BLACK_ROLE_ORDER}
        players.append(
            PlayerRow(
                index=player.index,
                name=player.name,
                status=player.status,
                status_tone="execution" if player.status == LABEL_EXECUTION else ("bite" if player.status == LABEL_BITE else ""),
                co=build_co_label(player.claim_role_keys),
                claim_role_keys=player.claim_role_keys.copy(),
                white_total=sum(white_breakdown.values()),
                black_total=sum(black_breakdown.values()),
                white_win_rate=round(white_win_rate, 1),
                black_win_rate=round(black_win_rate, 1),
                white_breakdown=white_breakdown,
                black_breakdown=black_breakdown,
            )
        )
    return players


def build_top_page_view_model(values: dict[str, str] | None = None) -> TopPageViewModel:
    config = parse_game_config(values)
    return TopPageViewModel(
        regulation_roles=build_regulation_roles(config.role_counts),
        default_role_counts=DEFAULT_ROLE_COUNTS.copy(),
        tactics_groups=[],
        rule_groups=build_rule_groups(values),
    )


def build_main_page_view_model(
    values: dict[str, str] | None = None,
    node_state: NodeState | None = None,
    selected_target: int | None = None,
    show_white_details: bool = False,
    show_black_details: bool = False,
    query_prefix: str = "",
    selected_tree_layout: TreeLayout | None = None,
    can_go_back: bool = False,
    white_alive_count_override: int | None = None,
    wolf_alive_count_override: int | None = None,
    terminal_winner_override: str | None = None,
) -> MainPageViewModel:
    config = parse_game_config(values)
    if node_state is None:
        node_state = NodeState(day=1, phase_key="day", players=[])
    analysis = analyze_node_state(node_state)
    white_alive_count = analysis.white_alive_count if white_alive_count_override is None else white_alive_count_override
    wolf_alive_count = analysis.wolf_alive_count if wolf_alive_count_override is None else wolf_alive_count_override
    terminal_winner = get_terminal_winner(white_alive_count, wolf_alive_count) if terminal_winner_override is None else terminal_winner_override
    white_win_rate, black_win_rate = evaluate_count_state(white_alive_count, wolf_alive_count, node_state.phase_key)
    tactic_values = node_state.tactics.copy()
    players = _build_player_rows(node_state, config.role_counts, tactic_values.get("village_no_counter", LABEL_NO_COUNTER_FILLED), white_alive_count=white_alive_count, wolf_alive_count=wolf_alive_count)
    white_detail_columns = [(key, ROLE_LABELS[key]) for key in WHITE_ROLE_ORDER if config.role_counts.get(key, 0) > 0]
    black_detail_columns = [(key, ROLE_LABELS[key]) for key in BLACK_ROLE_ORDER if config.role_counts.get(key, 0) > 0]
    co_role_options = [(key, ROLE_LABELS[key]) for key in REGULATION_ROLE_ORDER if config.role_counts.get(key, 0) > 0]

    return MainPageViewModel(
        day=node_state.day,
        phase=LABEL_DAY if node_state.phase_key == "day" else LABEL_NIGHT,
        regulation_cast=build_regulation_cast(config.role_counts),
        white_win_rate=white_win_rate,
        black_win_rate=black_win_rate,
        terminal_winner=terminal_winner,
        selected_target=selected_target,
        players=players,
        selected_tree_layout=selected_tree_layout,
        show_white_details=show_white_details,
        show_black_details=show_black_details,
        show_ability_rows=has_ability_roles(config.role_counts),
        white_detail_columns=white_detail_columns,
        black_detail_columns=black_detail_columns,
        co_role_options=co_role_options,
        tactics_groups=build_tactics_groups({**(values or {}), **tactic_values}),
        query_prefix=query_prefix,
        target_action_label=LABEL_EXECUTION if node_state.phase_key == "day" else LABEL_BITE,
        can_go_back=can_go_back,
    )
