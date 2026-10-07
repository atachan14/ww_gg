from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

from app.core.calculation import evaluate_count_state, get_terminal_winner
from app.settings import DEFAULT_TACTIC_VALUES

PhaseKey = Literal["day", "night"]
ActionType = Literal["execution", "bite"]

WHITE_ROLE_KEYS = {"villager", "seer", "medium", "hunter"}
DEATH_LABELS = {
    "execution": "\u51e6\u5211",
    "bite": "\u8972\u6483",
}
ROLE_LABELS = {
    "villager": "\u5e02\u6c11",
    "seer": "\u5360",
    "medium": "\u970a",
    "hunter": "\u72e9",
    "madman": "\u72c2",
    "wolf": "\u72fc",
}
HIDDEN_CO_LABEL = "\u6f5c\u4f0f"


@dataclass
class PlayerState:
    index: int
    name: str
    role_key: str
    alive: bool = True
    claim_role_keys: list[str] = field(default_factory=list)
    status: str = "\u751f\u5b58"


@dataclass
class NodeState:
    day: int
    phase_key: PhaseKey
    players: list[PlayerState] = field(default_factory=list)
    tactics: dict[str, str] = field(default_factory=lambda: DEFAULT_TACTIC_VALUES.copy())


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
        players.append(PlayerState(index=index, name=f"player{index}", role_key=role_key))

    return NodeState(day=1, phase_key="day", players=players, tactics=DEFAULT_TACTIC_VALUES.copy())


def serialize_node_state(node_state: NodeState) -> dict[str, object]:
    return {
        "day": node_state.day,
        "phase_key": node_state.phase_key,
        "players": [asdict(player) for player in node_state.players],
        "tactics": dict(node_state.tactics),
    }


def deserialize_node_state(data: dict[str, object] | None, fallback_role_counts: dict[str, int]) -> NodeState:
    if not data:
        return build_initial_node_state(fallback_role_counts)

    try:
        day = int(data.get("day", 1))
        phase_key = str(data.get("phase_key", "day"))
        raw_players = list(data.get("players", []))
        raw_tactics = dict(data.get("tactics", {}))
    except Exception:
        return build_initial_node_state(fallback_role_counts)

    players: list[PlayerState] = []
    for raw_player in raw_players:
        if not isinstance(raw_player, dict):
            continue
        try:
            raw_claims = raw_player.get("claim_role_keys", [])
            claim_role_keys = [str(value) for value in raw_claims] if isinstance(raw_claims, list) else []
            players.append(
                PlayerState(
                    index=int(raw_player.get("index", 0)),
                    name=str(raw_player.get("name", "player")),
                    role_key=str(raw_player.get("role_key", "villager")),
                    alive=bool(raw_player.get("alive", True)),
                    claim_role_keys=claim_role_keys,
                    status=str(raw_player.get("status", "\u751f\u5b58")),
                )
            )
        except Exception:
            continue

    if not players:
        return build_initial_node_state(fallback_role_counts)
    tactics = DEFAULT_TACTIC_VALUES.copy()
    for key, value in raw_tactics.items():
        tactics[str(key)] = str(value)
    return NodeState(day=day, phase_key="night" if phase_key == "night" else "day", players=players, tactics=tactics)


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
                        claim_role_keys=current.claim_role_keys.copy(),
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
                        claim_role_keys=current.claim_role_keys.copy(),
                        status=current.status,
                    )
                )

        if node_state.phase_key == "day":
            next_state = NodeState(day=node_state.day, phase_key="night", players=next_players, tactics=node_state.tactics.copy())
        else:
            next_state = NodeState(day=node_state.day + 1, phase_key="day", players=next_players, tactics=node_state.tactics.copy())

        branches.append(Branch(action_type=action_type, target_index=player.index, label=f"{DEATH_LABELS[action_type]}: {player.name}", next_state=next_state))

    return branches


def advance_node_state(node_state: NodeState, target_index: int) -> NodeState:
    for branch in generate_branches(node_state):
        if branch.target_index == target_index:
            return branch.next_state
    return node_state


def build_co_label(claim_role_keys: list[str]) -> str:
    if not claim_role_keys:
        return HIDDEN_CO_LABEL
    return "/".join(ROLE_LABELS.get(role_key, role_key) for role_key in claim_role_keys)
