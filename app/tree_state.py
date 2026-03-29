from __future__ import annotations

from dataclasses import dataclass, field

from app.calculation import evaluate_count_state, get_terminal_winner
from app.game_tree import NodeState, PlayerState, analyze_node_state, deserialize_node_state, serialize_node_state


@dataclass
class TreeNode:
    path: str
    kind: str
    node_state: NodeState
    label: str
    probability_text: str
    result_text: str
    cumulative_probability: float
    terminal_winner: str | None
    white_alive_count: int
    wolf_alive_count: int
    selected_target: int | None = None
    children: list["TreeNode"] = field(default_factory=list)

    @property
    def node_id(self) -> str:
        return self.path


@dataclass
class ForkedNodeState:
    node_id: str
    parent_node_id: str
    kind: str
    node_state: NodeState
    label: str
    cumulative_probability: float
    white_alive_count: int
    wolf_alive_count: int
    selected_target: int | None = None


@dataclass
class TreeSessionState:
    root_state: NodeState
    tree_id: str = "tree-local"
    root_node_id: str = ""
    current_node_id: str = ""
    target_overrides: dict[str, int] = field(default_factory=dict)
    tactic_overrides: dict[str, dict[str, str]] = field(default_factory=dict)
    claim_overrides: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    forked_nodes: dict[str, ForkedNodeState] = field(default_factory=dict)
    fork_counters: dict[str, int] = field(default_factory=dict)

    @property
    def current_path(self) -> str:
        return self.current_node_id

    @current_path.setter
    def current_path(self, value: str) -> None:
        self.current_node_id = value


def create_tree_session(root_state: NodeState) -> TreeSessionState:
    return TreeSessionState(root_state=root_state, root_node_id="", current_node_id="")


def serialize_tree_session(tree_session: TreeSessionState) -> dict[str, object]:
    return {
        "tree_id": tree_session.tree_id,
        "root_node_id": tree_session.root_node_id,
        "current_node_id": tree_session.current_node_id,
        "root_state": serialize_node_state(tree_session.root_state),
        "target_overrides": {key: int(value) for key, value in tree_session.target_overrides.items()},
        "tactic_overrides": {
            str(path): {str(key): str(value) for key, value in values.items()}
            for path, values in tree_session.tactic_overrides.items()
        },
        "claim_overrides": {
            str(path): {str(player_index): [str(role_key) for role_key in role_keys] for player_index, role_keys in values.items()}
            for path, values in tree_session.claim_overrides.items()
        },
        "fork_counters": {str(key): int(value) for key, value in tree_session.fork_counters.items()},
        "forked_nodes": {
            node_id: {
                "node_id": fork.node_id,
                "parent_node_id": fork.parent_node_id,
                "kind": fork.kind,
                "node_state": serialize_node_state(fork.node_state),
                "label": fork.label,
                "cumulative_probability": fork.cumulative_probability,
                "white_alive_count": fork.white_alive_count,
                "wolf_alive_count": fork.wolf_alive_count,
                "selected_target": fork.selected_target,
            }
            for node_id, fork in tree_session.forked_nodes.items()
        },
    }


def deserialize_tree_session(data: dict[str, object] | None, fallback_role_counts: dict[str, int]) -> TreeSessionState:
    root_state = deserialize_node_state((data or {}).get("root_state") if isinstance(data, dict) else None, fallback_role_counts)
    tree_id = str((data or {}).get("tree_id", "tree-local")) if isinstance(data, dict) else "tree-local"
    root_node_id = str((data or {}).get("root_node_id", "")) if isinstance(data, dict) else ""
    current_node_id = str((data or {}).get("current_node_id", (data or {}).get("current_path", ""))) if isinstance(data, dict) else ""

    raw_overrides = dict((data or {}).get("target_overrides", {})) if isinstance(data, dict) else {}
    target_overrides: dict[str, int] = {}
    for key, value in raw_overrides.items():
        try:
            target_overrides[str(key)] = int(value)
        except Exception:
            continue

    raw_tactic_overrides = dict((data or {}).get("tactic_overrides", {})) if isinstance(data, dict) else {}
    tactic_overrides: dict[str, dict[str, str]] = {}
    for path_key, values in raw_tactic_overrides.items():
        if isinstance(values, dict):
            tactic_overrides[str(path_key)] = {str(key): str(value) for key, value in values.items()}

    raw_claim_overrides = dict((data or {}).get("claim_overrides", {})) if isinstance(data, dict) else {}
    claim_overrides: dict[str, dict[str, list[str]]] = {}
    for path_key, values in raw_claim_overrides.items():
        if not isinstance(values, dict):
            continue
        normalized: dict[str, list[str]] = {}
        for player_index, role_keys in values.items():
            if isinstance(role_keys, list):
                normalized[str(player_index)] = [str(role_key) for role_key in role_keys]
        claim_overrides[str(path_key)] = normalized

    raw_fork_counters = dict((data or {}).get("fork_counters", {})) if isinstance(data, dict) else {}
    fork_counters: dict[str, int] = {}
    for key, value in raw_fork_counters.items():
        try:
            fork_counters[str(key)] = int(value)
        except Exception:
            continue

    raw_forked_nodes = dict((data or {}).get("forked_nodes", {})) if isinstance(data, dict) else {}
    forked_nodes: dict[str, ForkedNodeState] = {}
    for node_id, raw_fork in raw_forked_nodes.items():
        if not isinstance(raw_fork, dict):
            continue
        forked_nodes[str(node_id)] = ForkedNodeState(
            node_id=str(raw_fork.get("node_id", node_id)),
            parent_node_id=str(raw_fork.get("parent_node_id", "")),
            kind=str(raw_fork.get("kind", "choice")),
            node_state=deserialize_node_state(raw_fork.get("node_state"), fallback_role_counts),
            label=str(raw_fork.get("label", "-")),
            cumulative_probability=float(raw_fork.get("cumulative_probability", 1.0)),
            white_alive_count=int(raw_fork.get("white_alive_count", 0)),
            wolf_alive_count=int(raw_fork.get("wolf_alive_count", 0)),
            selected_target=(int(raw_fork["selected_target"]) if raw_fork.get("selected_target") is not None else None),
        )

    return TreeSessionState(
        root_state=root_state,
        tree_id=tree_id,
        root_node_id=root_node_id,
        current_node_id=current_node_id,
        target_overrides=target_overrides,
        tactic_overrides=tactic_overrides,
        claim_overrides=claim_overrides,
        forked_nodes=forked_nodes,
        fork_counters=fork_counters,
    )


def build_tree(session: TreeSessionState) -> TreeNode | None:
    root_state = _apply_node_overrides(session.root_state, session.root_node_id, session)
    analysis = analyze_node_state(root_state)
    root_target = _resolve_choice_target(root_state, session.root_node_id, session.target_overrides)
    if root_target is None:
        return None
    return _build_choice_node(
        root_state,
        session.root_node_id,
        root_target,
        1.0,
        analysis.white_alive_count,
        analysis.wolf_alive_count,
        session,
    )


def find_node(root: TreeNode | None, node_id: str) -> TreeNode | None:
    if root is None:
        return None
    if root.node_id == node_id:
        return root
    for child in root.children:
        found = find_node(child, node_id)
        if found is not None:
            return found
    return None


def get_current_node(session: TreeSessionState) -> TreeNode | None:
    tree = build_tree(session)
    if tree is None:
        return None
    return find_node(tree, session.current_node_id) or tree


def set_current_target(session: TreeSessionState, target_index: int) -> None:
    session.target_overrides[session.current_node_id] = target_index


def set_node_tactics(session: TreeSessionState, node_id: str, tactics: dict[str, str]) -> None:
    session.tactic_overrides[node_id] = {str(key): str(value) for key, value in tactics.items()}


def set_node_claims(session: TreeSessionState, node_id: str, claims: dict[int, list[str]]) -> None:
    session.claim_overrides[node_id] = {str(player_index): [str(role_key) for role_key in role_keys] for player_index, role_keys in claims.items()}


def fork_current_node_with_tactics(session: TreeSessionState, tactics: dict[str, str]) -> str | None:
    current = get_current_node(session)
    if current is None:
        return None
    next_state = _clone_node_state(current.node_state)
    next_state.tactics = tactics.copy()
    return _fork_from_current_node(session, current, next_state)


def fork_current_node_with_claims(session: TreeSessionState, claims_by_player: dict[int, list[str]]) -> str | None:
    current = get_current_node(session)
    if current is None:
        return None
    next_state = _clone_node_state(current.node_state)
    for player in next_state.players:
        if player.index in claims_by_player:
            player.claim_role_keys = claims_by_player[player.index].copy()
    return _fork_from_current_node(session, current, next_state)


def advance_current_path(session: TreeSessionState) -> None:
    tree = build_tree(session)
    current = find_node(tree, session.current_node_id) if tree is not None else None
    if current is None:
        return

    if current.kind == "chance":
        if current.children:
            session.current_node_id = current.children[0].node_id
        return

    if current.kind != "choice":
        return

    preferred = next((child for child in current.children if child.terminal_winner is None), None)
    if preferred is None and current.children:
        preferred = current.children[0]
    if preferred is None:
        return

    if preferred.children:
        session.current_node_id = preferred.children[0].node_id
    else:
        session.current_node_id = preferred.node_id


def rewind_current_path(session: TreeSessionState) -> None:
    tree = build_tree(session)
    if tree is None or session.current_node_id == session.root_node_id:
        return

    node_id = session.current_node_id
    while node_id:
        node_id = _parent_path(node_id)
        node = find_node(tree, node_id)
        if node is not None and node.kind == "choice":
            session.current_node_id = node_id
            return
    session.current_node_id = session.root_node_id


def _fork_from_current_node(session: TreeSessionState, current: TreeNode, next_state: NodeState) -> str:
    next_node_id = _next_fork_node_id(session, current.node_id)
    session.forked_nodes[next_node_id] = ForkedNodeState(
        node_id=next_node_id,
        parent_node_id=current.node_id,
        kind=current.kind,
        node_state=next_state,
        label=current.label,
        cumulative_probability=current.cumulative_probability,
        white_alive_count=current.white_alive_count,
        wolf_alive_count=current.wolf_alive_count,
        selected_target=current.selected_target,
    )
    session.current_node_id = next_node_id
    return next_node_id


def _next_fork_node_id(session: TreeSessionState, parent_node_id: str) -> str:
    counter = session.fork_counters.get(parent_node_id, 0) + 1
    session.fork_counters[parent_node_id] = counter
    return f"{parent_node_id}.f{counter}" if parent_node_id else f"f{counter}"


def _build_choice_node(
    node_state: NodeState,
    node_id: str,
    target_index: int,
    cumulative_probability: float,
    white_alive_count: int,
    wolf_alive_count: int,
    session: TreeSessionState,
) -> TreeNode:
    terminal_winner = get_terminal_winner(white_alive_count, wolf_alive_count)
    white_win_rate, black_win_rate = evaluate_count_state(white_alive_count, wolf_alive_count, node_state.phase_key)
    target_player = next((player for player in node_state.players if player.alive and player.index == target_index), None)
    label = target_player.name if target_player is not None else "-"
    node = TreeNode(
        path=node_id,
        kind="choice",
        node_state=node_state,
        label=label,
        probability_text=f"{cumulative_probability * 100:.1f}%",
        result_text=_format_result_text(white_win_rate, black_win_rate, terminal_winner),
        cumulative_probability=cumulative_probability,
        terminal_winner=terminal_winner,
        white_alive_count=white_alive_count,
        wolf_alive_count=wolf_alive_count,
        selected_target=target_index,
        children=[],
    )
    if terminal_winner is None and target_player is not None:
        node.children = _build_outcome_children(
            node_state,
            node_id,
            target_player,
            cumulative_probability,
            white_alive_count,
            wolf_alive_count,
            session,
        )
    _append_forked_children(node, session)
    return node


def _build_outcome_children(
    node_state: NodeState,
    choice_node_id: str,
    target_player: PlayerState,
    cumulative_probability: float,
    white_alive_count: int,
    wolf_alive_count: int,
    session: TreeSessionState,
) -> list[TreeNode]:
    total_alive = max(white_alive_count + wolf_alive_count, 1)
    outcomes: list[tuple[str, float, int, int, NodeState]] = []

    if node_state.phase_key == "day":
        if white_alive_count > 0:
            outcomes.append((
                "villager",
                white_alive_count / total_alive,
                white_alive_count - 1,
                wolf_alive_count,
                _build_public_next_state(node_state, target_player.index, "execution"),
            ))
        if wolf_alive_count > 0:
            outcomes.append((
                "wolf",
                wolf_alive_count / total_alive,
                white_alive_count,
                wolf_alive_count - 1,
                _build_public_next_state(node_state, target_player.index, "execution"),
            ))
    else:
        if white_alive_count > 0:
            outcomes.append((
                "village",
                1.0,
                white_alive_count - 1,
                wolf_alive_count,
                _build_public_next_state(node_state, target_player.index, "bite"),
            ))

    nodes: list[TreeNode] = []
    for index, (outcome_key, probability, next_white_count, next_wolf_count, next_state_base) in enumerate(outcomes):
        if node_state.phase_key == "day":
            next_state_base.phase_key = "night"
        else:
            next_state_base.phase_key = "day"
            next_state_base.day += 1

        child_node_id = _child_path(choice_node_id, index)
        next_state = _apply_node_overrides(next_state_base, child_node_id, session)
        terminal_winner = get_terminal_winner(next_white_count, next_wolf_count)
        white_win_rate, black_win_rate = evaluate_count_state(next_white_count, next_wolf_count, next_state.phase_key)
        node = TreeNode(
            path=child_node_id,
            kind="terminal" if terminal_winner else "chance",
            node_state=next_state,
            label=_outcome_label(outcome_key),
            probability_text=f"{cumulative_probability * probability * 100:.1f}%",
            result_text=_format_result_text(white_win_rate, black_win_rate, terminal_winner),
            cumulative_probability=cumulative_probability * probability,
            terminal_winner=terminal_winner,
            white_alive_count=next_white_count,
            wolf_alive_count=next_wolf_count,
            selected_target=None,
            children=[],
        )
        if terminal_winner is None:
            next_choice_node_id = _child_path(child_node_id, 0)
            next_choice_state = _apply_node_overrides(next_state, next_choice_node_id, session)
            next_target = _resolve_choice_target(next_choice_state, next_choice_node_id, session.target_overrides)
            if next_target is not None:
                next_analysis = analyze_node_state(next_choice_state)
                node.children = [
                    _build_choice_node(
                        next_choice_state,
                        next_choice_node_id,
                        next_target,
                        node.cumulative_probability,
                        next_analysis.white_alive_count,
                        next_analysis.wolf_alive_count,
                        session,
                    )
                ]
        _append_forked_children(node, session)
        nodes.append(node)
    return nodes


def _append_forked_children(node: TreeNode, session: TreeSessionState) -> None:
    forked_children = [fork for fork in session.forked_nodes.values() if fork.parent_node_id == node.node_id]
    if not forked_children:
        return
    for fork in sorted(forked_children, key=lambda item: item.node_id):
        node.children.append(_build_forked_node(fork, session))


def _build_forked_node(fork: ForkedNodeState, session: TreeSessionState) -> TreeNode:
    terminal_winner = get_terminal_winner(fork.white_alive_count, fork.wolf_alive_count)
    white_win_rate, black_win_rate = evaluate_count_state(fork.white_alive_count, fork.wolf_alive_count, fork.node_state.phase_key)
    node = TreeNode(
        path=fork.node_id,
        kind=fork.kind,
        node_state=fork.node_state,
        label=fork.label,
        probability_text=f"{fork.cumulative_probability * 100:.1f}%",
        result_text=_format_result_text(white_win_rate, black_win_rate, terminal_winner),
        cumulative_probability=fork.cumulative_probability,
        terminal_winner=terminal_winner,
        white_alive_count=fork.white_alive_count,
        wolf_alive_count=fork.wolf_alive_count,
        selected_target=fork.selected_target,
        children=[],
    )
    if fork.kind == "choice" and terminal_winner is None and fork.selected_target is not None:
        target_player = next((player for player in fork.node_state.players if player.alive and player.index == fork.selected_target), None)
        if target_player is not None:
            node.children = _build_outcome_children(
                fork.node_state,
                fork.node_id,
                target_player,
                fork.cumulative_probability,
                fork.white_alive_count,
                fork.wolf_alive_count,
                session,
            )
    elif fork.kind == "chance" and terminal_winner is None:
        next_choice_node_id = _child_path(fork.node_id, 0)
        next_choice_state = _apply_node_overrides(fork.node_state, next_choice_node_id, session)
        next_target = _resolve_choice_target(next_choice_state, next_choice_node_id, session.target_overrides)
        if next_target is not None:
            next_analysis = analyze_node_state(next_choice_state)
            node.children = [
                _build_choice_node(
                    next_choice_state,
                    next_choice_node_id,
                    next_target,
                    fork.cumulative_probability,
                    next_analysis.white_alive_count,
                    next_analysis.wolf_alive_count,
                    session,
                )
            ]
    _append_forked_children(node, session)
    return node


def _resolve_choice_target(node_state: NodeState, node_id: str, target_overrides: dict[str, int]) -> int | None:
    override = target_overrides.get(node_id)
    if override is not None and any(player.alive and player.index == override for player in node_state.players):
        if node_state.phase_key == "night":
            target_player = next((player for player in node_state.players if player.index == override), None)
            if target_player is not None and target_player.role_key == "wolf":
                return _pick_strategy_target(node_state)
        return override
    return _pick_strategy_target(node_state)


def _pick_strategy_target(node_state: NodeState) -> int | None:
    candidates = [player for player in node_state.players if player.alive]
    if node_state.phase_key == "night":
        candidates = [player for player in candidates if player.role_key != "wolf"]
    if not candidates:
        return None
    return min(player.index for player in candidates)


def _build_public_next_state(node_state: NodeState, target_index: int, action_type: str) -> NodeState:
    death_label = "\u51e6\u5211" if action_type == "execution" else "\u8972\u6483"
    next_players: list[PlayerState] = []
    for player in node_state.players:
        if player.index == target_index:
            next_players.append(PlayerState(index=player.index, name=player.name, role_key=player.role_key, alive=False, claim_role_keys=player.claim_role_keys.copy(), status=death_label))
        else:
            next_players.append(PlayerState(index=player.index, name=player.name, role_key=player.role_key, alive=player.alive, claim_role_keys=player.claim_role_keys.copy(), status=player.status))
    return NodeState(day=node_state.day, phase_key=node_state.phase_key, players=next_players, tactics=node_state.tactics.copy())


def _apply_node_overrides(node_state: NodeState, node_id: str, session: TreeSessionState) -> NodeState:
    players = [
        PlayerState(
            index=player.index,
            name=player.name,
            role_key=player.role_key,
            alive=player.alive,
            claim_role_keys=player.claim_role_keys.copy(),
            status=player.status,
        )
        for player in node_state.players
    ]
    tactics = node_state.tactics.copy()

    claim_override = session.claim_overrides.get(node_id, {})
    for player in players:
        override_claims = claim_override.get(str(player.index))
        if override_claims is not None:
            player.claim_role_keys = override_claims.copy()

    tactic_override = session.tactic_overrides.get(node_id, {})
    tactics.update(tactic_override)

    return NodeState(day=node_state.day, phase_key=node_state.phase_key, players=players, tactics=tactics)


def _clone_node_state(node_state: NodeState) -> NodeState:
    return NodeState(
        day=node_state.day,
        phase_key=node_state.phase_key,
        players=[
            PlayerState(
                index=player.index,
                name=player.name,
                role_key=player.role_key,
                alive=player.alive,
                claim_role_keys=player.claim_role_keys.copy(),
                status=player.status,
            )
            for player in node_state.players
        ],
        tactics=node_state.tactics.copy(),
    )


def _child_path(parent_node_id: str, child_index: int) -> str:
    return f"{parent_node_id}.{child_index}" if parent_node_id else str(child_index)


def _parent_path(node_id: str) -> str:
    if "." not in node_id:
        return ""
    return node_id.rsplit(".", 1)[0]


def _outcome_label(outcome_key: str) -> str:
    mapping = {
        "villager": "\u5e02\u6c11",
        "wolf": "\u72fc",
        "village": "\u6751",
    }
    return mapping[outcome_key]


def _format_result_text(white_win_rate: float, black_win_rate: float, winner: str | None) -> str:
    if winner == "village":
        return "\u6751\u306e\u52dd\u5229"
    if winner == "wolf":
        return "\u72fc\u306e\u52dd\u5229"
    return f"{white_win_rate:.1f}% / {black_win_rate:.1f}%"
