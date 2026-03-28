from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_ROLE_ORDER = ["villager", "seer", "medium", "hunter", "madman", "wolf"]

ROLE_LABELS = {
    "villager": "村",
    "seer": "占",
    "medium": "霊",
    "hunter": "狩",
    "madman": "狂",
    "wolf": "狼",
}

WHITE_ROLE_KEYS = ["seer", "medium", "hunter", "villager"]
BLACK_ROLE_KEYS = ["madman", "wolf"]

PHASE_LABELS = {
    "day": "昼",
    "night": "夜",
}


@dataclass
class TreeNodeSummary:
    node_id: str
    label: str
    action_label: str
    immediate_white_win_rate: float
    total_white_win_rate: float

    @property
    def immediate_black_win_rate(self) -> float:
        return 100.0 - self.immediate_white_win_rate

    @property
    def total_black_win_rate(self) -> float:
        return 100.0 - self.total_white_win_rate


@dataclass
class PlayerRow:
    index: int
    name: str
    status: str = "生存"
    co_roles: list[str] = field(default_factory=list)
    white_breakdown: dict[str, float] = field(default_factory=dict)
    black_breakdown: dict[str, float] = field(default_factory=dict)
    selected_white_win_rate: float = 0.0
    selected_black_win_rate: float = 0.0

    @property
    def white_total(self) -> float:
        return sum(self.white_breakdown.values())

    @property
    def black_total(self) -> float:
        return sum(self.black_breakdown.values())

    @property
    def co_display(self) -> str:
        return " / ".join(self.co_roles) if self.co_roles else "-"


@dataclass
class AppState:
    current_screen: str = "top"
    node_day: int = 1
    node_phase: str = "day"
    selected_action_index: int = 1
    regulation_roles: dict[str, int] = field(
        default_factory=lambda: {
            "villager": 3,
            "seer": 1,
            "medium": 1,
            "hunter": 0,
            "madman": 0,
            "wolf": 2,
        }
    )
    rule_options: dict[str, str | bool] = field(
        default_factory=lambda: {
            "wolf_can_self_bite": False,
            "wolf_can_skip_bite": False,
            "seer_first_result": "ランダム白",
            "hunter_consecutive_guard": False,
        }
    )
    strategy_options: dict[str, dict[str, str | bool]] = field(
        default_factory=lambda: {
            "村": {
                "処刑対象": "期待勝率最大を選ぶ",
                "村騙りを認めない": True,
                "対抗が出ない場合は真とみなす": True,
                "ギドラを認める": False,
            },
            "狼": {
                "噛み対象": "期待勝率最大を選ぶ",
            },
            "占": {
                "UIのみ表示": True,
            },
        }
    )
