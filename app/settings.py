from __future__ import annotations

from dataclasses import dataclass


ROLE_LABELS = {
    "villager": "??",
    "seer": "?",
    "medium": "?",
    "hunter": "?",
    "madman": "?",
    "wolf": "?",
}

# Top ????????????????????????
DEFAULT_ROLE_COUNTS = {
    "villager": 2,
    "seer": 0,
    "medium": 0,
    "hunter": 0,
    "wolf": 1,
    "madman": 0,
}

DEFAULT_RULE_VALUES = {
    "rule_wolf_self_bite": "?",
    "rule_wolf_skip_bite": "?",
    "rule_seer_first_result": "?????",
    "rule_hunter_consecutive_guard": "?",
}

DEFAULT_TACTIC_VALUES = {
    "village_target": "?????????",
    "village_fake_claim": "????",
    "village_no_counter": "?????",
    "village_gidra": "????",
    "wolf_target": "?????????",
    "seer_option": "???",
}

DEFAULT_OPEN_STATES = {
    "open_rules_wolf": "1",
    "open_rules_seer": "0",
    "open_rules_hunter": "0",
    "open_tactics_village": "1",
    "open_tactics_wolf": "0",
    "open_tactics_seer": "0",
}

SESSION_SECRET_KEY = "ww_gg-dev-session-key"
SESSION_KEY = "top_config"
NODE_SESSION_KEY = "main_node"
SELECTED_TARGET_SESSION_KEY = "main_selected_target"

WHITE_ROLE_ORDER = ["seer", "medium", "hunter", "villager"]
BLACK_ROLE_ORDER = ["madman", "wolf"]
REGULATION_ROLE_ORDER = ["villager", "seer", "medium", "hunter", "wolf", "madman"]
ABILITY_ROLE_KEYS = ["seer", "medium", "hunter"]
SESSION_VALUE_KEYS = [
    *(f"role_{key}" for key in DEFAULT_ROLE_COUNTS),
    *DEFAULT_RULE_VALUES.keys(),
    *DEFAULT_TACTIC_VALUES.keys(),
    *DEFAULT_OPEN_STATES.keys(),
]


@dataclass(frozen=True)
class GameConfig:
    role_counts: dict[str, int]
    rules: dict[str, str]
    tactics: dict[str, str]
    open_states: dict[str, str]


def parse_game_config(values: dict[str, str] | None = None) -> GameConfig:
    return GameConfig(
        role_counts=parse_role_counts(values),
        rules=parse_selected_values(DEFAULT_RULE_VALUES, values),
        tactics=parse_selected_values(DEFAULT_TACTIC_VALUES, values),
        open_states=parse_selected_values(DEFAULT_OPEN_STATES, values),
    )


def parse_role_counts(values: dict[str, str] | None = None) -> dict[str, int]:
    counts = DEFAULT_ROLE_COUNTS.copy()
    if not values:
        return counts

    for key in counts:
        raw = values.get(f"role_{key}")
        if raw is None:
            continue
        try:
            counts[key] = max(0, int(raw))
        except ValueError:
            continue
    return counts


def parse_selected_values(defaults: dict[str, str], values: dict[str, str] | None = None) -> dict[str, str]:
    selected = defaults.copy()
    if not values:
        return selected

    for key, default_value in defaults.items():
        selected[key] = values.get(key, default_value)
    return selected


def pick_session_values(values: dict[str, str]) -> dict[str, str]:
    return {key: values[key] for key in SESSION_VALUE_KEYS if key in values}


def build_open_state_key(scope: str, group_key: str) -> str:
    return f"open_{scope}_{group_key}"


def is_group_expanded(open_states: dict[str, str], scope: str, group_key: str, default: bool = False) -> bool:
    stored = open_states.get(build_open_state_key(scope, group_key))
    if stored is None:
        return default
    return stored == "1"


def build_regulation_cast(role_counts: dict[str, int]) -> str:
    parts = []
    for key in ["seer", "medium", "villager", "hunter", "wolf", "madman"]:
        count = role_counts.get(key, 0)
        if count > 0:
            parts.append(f"{ROLE_LABELS[key]}{count}")
    return " ".join(parts) if parts else "???"


def build_regulation_roles(role_counts: dict[str, int]) -> list[tuple[str, str, int]]:
    return [(key, ROLE_LABELS[key], role_counts[key]) for key in REGULATION_ROLE_ORDER]


def total_player_count(role_counts: dict[str, int]) -> int:
    total = sum(role_counts.values())
    return total if total > 0 else 1


def has_ability_roles(role_counts: dict[str, int]) -> bool:
    return any(role_counts.get(key, 0) > 0 for key in ABILITY_ROLE_KEYS)
