from logic.roles import *
from dataclasses import dataclass
from __future__ import annotations
from enum import Enum


class Phase(Enum):
    MORNING = "morning"
    NIGHT = "night"

### topで決めて固定 ###


@dataclass
class RuleData():
    can_continuous_guard_possible: bool = True
    cant_no_vite: bool = True
    tie_vote_is_wolfwin: bool  = True


@dataclass
class RegulationData():
    roles: dict[RoleTemplate:int]
    rules: RuleData


### day毎に作成 ###


@dataclass
class PlayerData():
    index: int
    name: str
    is_alive: bool
    coming_out: RoleTemplate
    role_possibility: dict[RoleTemplate:float]
    killed_next_phasedata: PhaseData


@dataclass
class PhaseData():
    day: int
    phase: Phase
    villager_win_per: float
    player_list: list[PlayerData]
    tactics: TacticsData


@dataclass
class TacticsData():
    disable_villager_deception: bool = True      # 村騙りを禁止
    allow_no_opposition_claim: bool = True       # 対抗なしならそのまま採用
