from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.calculation import evaluate_count_state, get_terminal_winner
from app.game_tree import NodeState, PlayerState


TreeNodeKind = Literal["choice", "chance", "terminal"]
HeaderTone = Literal["day", "night"]


@dataclass
class TreeDisplayNode:
    label: str
    probability_text: str
    result_text: str
    kind: TreeNodeKind
    cumulative_probability: float | None = None
    children: list["TreeDisplayNode"] = field(default_factory=list)


@dataclass
class TreeLayoutItem:
    row: int
    col: int
    probability_text: str
    result_text: str
    label: str
    tone: HeaderTone
    is_current: bool = False


@dataclass
class TreeColumnHeader:
    label: str
    tone: HeaderTone


@dataclass
class TreeLayout:
    items: list[TreeLayoutItem]
    column_headers: list[TreeColumnHeader]
    max_col: int
    max_row: int


LABEL_VILLAGER = "\u5e02\u6c11"
LABEL_WOLF = "\u72fc"
LABEL_VILLAGE = "\u6751"
LABEL_EXECUTED = "\u51e6\u5211"
LABEL_BITTEN = "\u8972\u6483"
LABEL_BREAKDOWN = "\u5185\u8a33"
LABEL_DAY = "\u663c"
LABEL_NIGHT = "\u591c"
LABEL_VILLAGE_WIN = "\u6751\u306e\u52dd\u5229"
LABEL_WOLF_WIN = "\u72fc\u306e\u52dd\u5229"


def build_selected_target_tree(node_state: NodeState, target_index: int) -> TreeDisplayNode | None:
    alive_players = [player for player in node_state.players if player.alive]
    target_player = next((player for player in alive_players if player.index == target_index), None)
    if target_player is None:
        return None

    white_count = sum(1 for player in alive_players if player.role_key != "wolf")
    wolf_count = sum(1 for player in alive_players if player.role_key == "wolf")
    white_win_rate, black_win_rate = evaluate_count_state(white_count, wolf_count, node_state.phase_key)
    root = TreeDisplayNode(
        label=target_player.name,
        probability_text="100.0%",
        result_text=_format_result_text(white_win_rate, black_win_rate, get_terminal_winner(white_count, wolf_count)),
        kind="choice",
        cumulative_probability=1.0,
        children=[],
    )
    root.children = _build_outcome_children(node_state, target_player, white_count, wolf_count, path_probability=1.0)
    return root


def build_tree_layout(root: TreeDisplayNode | None, start_day: int = 1, start_phase_key: str = "day") -> TreeLayout | None:
    if root is None:
        return None

    items: list[TreeLayoutItem] = []
    next_row = 1

    def walk(node: TreeDisplayNode, col: int) -> int:
        nonlocal next_row
        current_row = next_row
        items.append(
            TreeLayoutItem(
                row=current_row,
                col=col,
                probability_text=node.probability_text,
                result_text=node.result_text,
                label=node.label,
                tone=_tone_for_col(start_phase_key, col),
                is_current=(col == 1),
            )
        )

        if not node.children:
            next_row += 1
            return col

        max_col = col
        for child in node.children:
            max_col = max(max_col, walk(child, col + 1))
        return max_col

    max_col = walk(root, 1)
    max_row = max((item.row for item in items), default=1)
    items.sort(key=lambda item: (item.row, item.col))
    column_headers = [_build_column_header(start_day, start_phase_key, col) for col in range(1, max_col + 1)]
    return TreeLayout(items=items, column_headers=column_headers, max_col=max_col, max_row=max_row)


def _build_outcome_children(
    node_state: NodeState,
    target_player: PlayerState,
    white_count: int,
    wolf_count: int,
    path_probability: float,
) -> list[TreeDisplayNode]:
    total_alive = max(white_count + wolf_count, 1)
    if node_state.phase_key == "day":
        outcomes: list[tuple[str, float, int, int]] = []
        if white_count > 0:
            outcomes.append((LABEL_VILLAGER, white_count / total_alive, white_count - 1, wolf_count))
        if wolf_count > 0:
            outcomes.append((LABEL_WOLF, wolf_count / total_alive, white_count, wolf_count - 1))
    else:
        outcomes = []
        if white_count > 0:
            outcomes.append((LABEL_VILLAGE, 1.0, white_count - 1, wolf_count))

    outcome_nodes: list[TreeDisplayNode] = []
    for label, probability, next_white, next_wolf in outcomes:
        next_state = _build_public_next_state(node_state, target_player.index)
        if node_state.phase_key == "day":
            next_state.phase_key = "night"
        else:
            next_state.phase_key = "day"
            next_state.day += 1

        cumulative_probability = path_probability * probability
        winner = get_terminal_winner(next_white, next_wolf)
        next_result = _format_result_text(*evaluate_count_state(next_white, next_wolf, next_state.phase_key), winner)
        node = TreeDisplayNode(
            label=label,
            probability_text=f"{cumulative_probability * 100:.1f}%",
            result_text=next_result,
            kind="terminal" if winner else "chance",
            cumulative_probability=cumulative_probability,
            children=[],
        )
        if winner is None:
            selected_player = _pick_strategy_target(next_state)
            if selected_player is not None:
                node.children = [
                    _build_choice_node(next_state, selected_player, next_white, next_wolf, cumulative_probability)
                ]
        outcome_nodes.append(node)
    return outcome_nodes


def _build_choice_node(
    node_state: NodeState,
    target_player: PlayerState,
    white_count: int,
    wolf_count: int,
    path_probability: float,
) -> TreeDisplayNode:
    white_win_rate, black_win_rate = evaluate_count_state(white_count, wolf_count, node_state.phase_key)
    return TreeDisplayNode(
        label=target_player.name,
        probability_text=f"{path_probability * 100:.1f}%",
        result_text=_format_result_text(white_win_rate, black_win_rate, None),
        kind="choice",
        cumulative_probability=path_probability,
        children=_build_outcome_children(node_state, target_player, white_count, wolf_count, path_probability),
    )


def _pick_strategy_target(node_state: NodeState) -> PlayerState | None:
    candidates = [player for player in node_state.players if player.alive]
    if node_state.phase_key == "night":
        candidates = [player for player in candidates if player.role_key != "wolf"]
    if not candidates:
        return None
    return min(candidates, key=lambda player: player.index)


def _build_public_next_state(node_state: NodeState, target_index: int) -> NodeState:
    next_players: list[PlayerState] = []
    death_label = LABEL_EXECUTED if node_state.phase_key == "day" else LABEL_BITTEN
    for player in node_state.players:
        if player.index == target_index:
            next_players.append(
                PlayerState(
                    index=player.index,
                    name=player.name,
                    role_key=player.role_key,
                    alive=False,
                    co=player.co,
                    status=death_label,
                )
            )
        else:
            next_players.append(
                PlayerState(
                    index=player.index,
                    name=player.name,
                    role_key=player.role_key,
                    alive=player.alive,
                    co=player.co,
                    status=player.status,
                )
            )
    return NodeState(day=node_state.day, phase_key=node_state.phase_key, players=next_players)


def _tone_for_col(start_phase_key: str, col: int) -> HeaderTone:
    phase_step = (col - 1) // 2
    phase_key = start_phase_key
    for _ in range(phase_step):
        phase_key = "night" if phase_key == "day" else "day"
    return "day" if phase_key == "day" else "night"


def _build_column_header(start_day: int, start_phase_key: str, col: int) -> TreeColumnHeader:
    phase_step = (col - 1) // 2
    phase_key = start_phase_key
    day = start_day
    for _ in range(phase_step):
        if phase_key == "day":
            phase_key = "night"
        else:
            phase_key = "day"
            day += 1

    action_label = LABEL_EXECUTED if phase_key == "day" else LABEL_BITTEN
    phase_label = LABEL_DAY if phase_key == "day" else LABEL_NIGHT
    tone: HeaderTone = "day" if phase_key == "day" else "night"

    if col % 2 == 0:
        return TreeColumnHeader(label=f"{LABEL_BREAKDOWN}({action_label})", tone=tone)
    return TreeColumnHeader(label=f"Day{day}/{phase_label}({action_label})", tone=tone)


def _format_result_text(white_win_rate: float, black_win_rate: float, winner: str | None) -> str:
    if winner == "village":
        return LABEL_VILLAGE_WIN
    if winner == "wolf":
        return LABEL_WOLF_WIN
    return f"{white_win_rate:.1f}% / {black_win_rate:.1f}%"
