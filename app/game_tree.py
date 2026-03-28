from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

from app.calculation import evaluate_count_state, get_terminal_winner

PhaseKey = Literal["day", "night"]
ActionType = Literal["execution", "bite"]

WHITE_ROLE_KEYS = {"villager", "seer", "medium", "hunter"}
BLACK_DETAIL_ROLE_KEYS = {"madman", "wolf"}
CO_LABELS = {
    "seer": "?",
    "medium": "?",
}
DEATH_LABELS = {
    "execution": "??",
    "bite": "??",
}


@dataclass
class PlayerState:
    index: int
    name: str
    role_key: str
    alive: bool = True
    co: str = "-"
    status: str = "??"


@dataclass
class NodeState:
    day: int
    phase_key: PhaseKey
    players: list[PlayerState] = field(default_factory=list)


@dataclass
class Branch:
    action_type: ActionType
    target_index: int
    label: str
    next_state: NodeState


@dataclass
class NodeAnalysis:
    white_win_rate: float
    black_win_rate: float
    terminal_winner: str | None
    white_alive_count: int
    wolf_alive_count: int
    alive_player_count: int


def build_initial_node_state(role_counts: dict[str, int]) -> NodeState:
    players: list[PlayerState] = []
    role_order = ["seer", "medium", "hunter", "villager", "wolf", "madman"]
    role_keys: list[str] = []
    for role_key in role_order:
        role_keys.extend([role_key] * role_counts.get(role_key, 0))

    for index, role_key in enumerate(role_keys, start=1):
        players.append(
            PlayerState(
                index=index,
                name=f"player{index}",
                role_key=role_key,
                co=CO_LABELS.get(role_key, "-"),
            )
        )

    return NodeState(day=1, phase_key="day", players=players)


def serialize_node_state(node_state: NodeState) -> dict[str, object]:
    return {
        "day": node_state.day,
        "phase_key": node_state.phase_key,
        "players": [asdict(player) for player in node_state.players],
    }


def deserialize_node_state(data: dict[str, object] | None, fallback_role_counts: dict[str, int]) -> NodeState:
    if not data:
        return build_initial_node_state(fallback_role_counts)

    try:
        day = int(data.get("day", 1))
        phase_key = str(data.get("phase_key", "day"))
        raw_players = list(data.get("players", []))
    except Exception:
        return build_initial_node_state(fallback_role_counts)

    players: list[PlayerState] = []
    for raw_player in raw_players:
        if not isinstance(raw_player, dict):
            continue
        try:
            players.append(
                PlayerState(
                    index=int(raw_player.get("index", 0)),
                    name=str(raw_player.get("name", "player")),
                    role_key=str(raw_player.get("role_key", "villager")),
                    alive=bool(raw_player.get("alive", True)),
                    co=str(raw_player.get("co", "-")),
                    status=str(raw_player.get("status", "??")),
                )
            )
        except Exception:
            continue

    if not players:
        return build_initial_node_state(fallback_role_counts)
    return NodeState(day=day, phase_key="night" if phase_key == "night" else "day", players=players)


def analyze_node_state(node_state: NodeState) -> NodeAnalysis:
    alive_players = [player for player in node_state.players if player.alive]
    white_alive_count = sum(1 for player in alive_players if player.role_key in WHITE_ROLE_KEYS)
    wolf_alive_count = sum(1 for player in alive_players if player.role_key == "wolf")
    terminal_winner = get_terminal_winner(white_alive_count, wolf_alive_count)
    white_win_rate, black_win_rate = evaluate_count_state(white_alive_count, wolf_alive_count, node_state.phase_key)
    return NodeAnalysis(
        white_win_rate=white_win_rate,
        black_win_rate=black_win_rate,
        terminal_winner=terminal_winner,
        white_alive_count=white_alive_count,
        wolf_alive_count=wolf_alive_count,
        alive_player_count=len(alive_players),
    )


def generate_branches(node_state: NodeState) -> list[Branch]:
    action_type: ActionType = "execution" if node_state.phase_key == "day" else "bite"
    branches: list[Branch] = []

    for player in node_state.players:
        if not player.alive:
            continue
        if action_type == "bite" and player.role_key == "wolf":
            continue

        next_players: list[PlayerState] = []
        for current in node_state.players:
            if current.index == player.index:
                next_players.append(
                    PlayerState(
                        index=current.index,
                        name=current.name,
                        role_key=current.role_key,
                        alive=False,
                        co=current.co,
                        status=DEATH_LABELS[action_type],
                    )
                )
            else:
                next_players.append(
                    PlayerState(
                        index=current.index,
                        name=current.name,
                        role_key=current.role_key,
                        alive=current.alive,
                        co=current.co,
                        status=current.status,
                    )
                )

        if node_state.phase_key == "day":
            next_state = NodeState(day=node_state.day, phase_key="night", players=next_players)
        else:
            next_state = NodeState(day=node_state.day + 1, phase_key="day", players=next_players)

        branches.append(
            Branch(
                action_type=action_type,
                target_index=player.index,
                label=f"{DEATH_LABELS[action_type]}: {player.name}",
                next_state=next_state,
            )
        )

    return branches


def advance_node_state(node_state: NodeState, target_index: int) -> NodeState:
    for branch in generate_branches(node_state):
        if branch.target_index == target_index:
            return branch.next_state
    return node_state
