from __future__ import annotations

from dataclasses import dataclass

from app.runtime_config import load_runtime_config


ROLE_LABELS = {
    "villager": "\u5e02\u6c11",
    "seer": "\u5360",
    "medium": "\u970a",
    "hunter": "\u72e9",
    "madman": "\u72c2",
    "wolf": "\u72fc",
}

# Top \u753b\u9762\u3067\u4f7f\u3046\u521d\u671f\u5024\u306f\u3053\u3053\u3067\u7ba1\u7406\u3059\u308b
DEFAULT_ROLE_COUNTS = {
    "villager": 2,
    "seer": 0,
    "medium": 0,
    "hunter": 0,
    "wolf": 1,
    "madman": 0,
}

DEFAULT_RULE_VALUES = {
    "rule_wolf_self_bite": "\u7121",
    "rule_wolf_skip_bite": "\u7121",
    "rule_seer_first_result": "\u30e9\u30f3\u30c0\u30e0\u767d",
    "rule_hunter_consecutive_guard": "\u7121",
}

DEFAULT_TACTIC_VALUES = {
    "village_target": "\u671f\u5f85\u52dd\u7387\u6700\u5927\u3092\u9078\u3076",
    "village_fake_claim": "\u8a8d\u3081\u306a\u3044",
    "village_no_counter": "\u6e80\u54e1\u3067\u771f",
    "village_gidra": "\u8a8d\u3081\u306a\u3044",
    "wolf_target": "\u671f\u5f85\u52dd\u7387\u6700\u5927\u3092\u9078\u3076",
    "seer_option": "\u672a\u5b9f\u88c5",
}

DEFAULT_OPEN_STATES = {
    "open_rules_wolf": "1",
    "open_rules_seer": "0",
    "open_rules_hunter": "0",
    "open_tactics_village": "1",
    "open_tactics_wolf": "0",
    "open_tactics_seer": "0",
}

DEFAULT_VIEW_VALUES = {
    "main_white_details": "0",
    "main_black_details": "0",
}

SESSION_SECRET_KEY = load_runtime_config().session_secret_key
SESSION_KEY = "top_config"
TREE_SESSION_KEY = "tree_session"
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
    *DEFAULT_VIEW_VALUES.keys(),
]


@dataclass(frozen=True)
class GameConfig:
    role_counts: dict[str, int]
    rules: dict[str, str]
    tactics: dict[str, str]
    open_states: dict[str, str]
    view_values: dict[str, str]


def parse_game_config(values: dict[str, str] | None = None) -> GameConfig:
    return GameConfig(
        role_counts=parse_role_counts(values),
        rules=parse_selected_values(DEFAULT_RULE_VALUES, values),
        tactics=parse_selected_values(DEFAULT_TACTIC_VALUES, values),
        open_states=parse_selected_values(DEFAULT_OPEN_STATES, values),
        view_values=parse_selected_values(DEFAULT_VIEW_VALUES, values),
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
    return " ".join(parts) if parts else "\u306a\u3057"


def build_regulation_roles(role_counts: dict[str, int]) -> list[tuple[str, str, int]]:
    return [(key, ROLE_LABELS[key], role_counts[key]) for key in REGULATION_ROLE_ORDER]


def total_player_count(role_counts: dict[str, int]) -> int:
    total = sum(role_counts.values())
    return total if total > 0 else 1


def has_ability_roles(role_counts: dict[str, int]) -> bool:
    return any(role_counts.get(key, 0) > 0 for key in ABILITY_ROLE_KEYS)

