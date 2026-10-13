"""Single-hunter physical effect; no selection policies, beliefs or UI.

Caller supplies one complete role world, a fixed attack and one nonself guard.
The original first-night wrapper remains available for stage1 callers.
"""
from dataclasses import dataclass
from .exact import ROLES
from .action_flow import NightFrame


@dataclass(frozen=True)
class GuardIntent:
    night: int
    actor: int
    target: int


@dataclass(frozen=True)
class DeathCause:
    player: int
    cause: str


@dataclass(frozen=True)
class GuardResolution:
    deaths: tuple[DeathCause,...]
    survivors: tuple[int,...]
    prevented_attack: bool


def resolve_first_guard(roles,alive,intent,attack,other_deaths=()):
    if not isinstance(intent,GuardIntent) or type(intent.night) is not int or intent.night!=1:
        raise ValueError("Only the first night is supported")
    return resolve_guard(roles,alive,intent,attack,other_deaths)


def resolve_guard(roles,alive,intent,attack,other_deaths=()):
    """Cancel only the explicitly supplied wolf-attack death on a guard match.

    Other causes survive even when they kill the guarded person or guardian.
    All intents are fixed before simultaneous deaths; never choose an action.
    """
    if type(roles) is not tuple or not roles or any(role not in ROLES for role in roles):
        raise ValueError('Complete immutable role world required')
    if (type(alive) is not tuple or not alive or
            any(type(p) is not int or not 1<=p<=len(roles) for p in alive) or len(set(alive))!=len(alive)):
        raise ValueError('Valid immutable predeath roster required')
    if roles.count('hunter')!=1 or not isinstance(intent,GuardIntent):
        raise ValueError('Exactly one confirmed hunter required')
    if type(intent.night) is not int or intent.night<1:
        raise ValueError("Positive night required")
    if (type(intent.actor) is not int or intent.actor not in alive or
            roles[intent.actor-1]!='hunter'):
        raise ValueError('Guardian must be the living confirmed hunter')
    if type(intent.target) is not int or intent.target not in alive or intent.target==intent.actor:
        raise ValueError('Only a living nonself guard target is supported')
    if type(attack) is not int or attack not in alive or not any(roles[p-1]=='wolf' for p in alive):
        raise ValueError('A living wolf and valid fixed attack target are required')
    if type(other_deaths) is not tuple:
        raise ValueError('Immutable other-cause deaths required')
    for death in other_deaths:
        if (not isinstance(death,DeathCause) or type(death.player) is not int or death.player not in alive or
                type(death.cause) is not str or not death.cause.strip() or death.cause=='wolf_attack'):
            raise ValueError('Other deaths must identify a separate nonempty cause')
    prevented=intent.target==attack
    deaths=other_deaths if prevented else (DeathCause(attack,'wolf_attack'),)+other_deaths
    dead={death.player for death in deaths}
    return GuardResolution(deaths,tuple(p for p in alive if p not in dead),prevented)


def resolve_guard_frame(frame,roles,other_deaths=()):
    """Opt-in adapter for NightFrame.after; not installed in production policy.

    Returns physical facts only. No public GJ/phase/terminal transition is made.
    """
    if (not isinstance(frame,NightFrame) or getattr(frame.board,'phase',None)!='night' or
            type(getattr(frame.board,'day',None)) is not int or frame.board.day!=1):
        raise ValueError('First-night frame required')
    if type(roles) is not tuple or getattr(frame.board,'player_count',len(roles))!=len(roles):
        raise ValueError('Role world must cover every frame player')
    return resolve_first_guard(roles,getattr(frame.board,'alive',None),frame.after,frame.target,other_deaths)
