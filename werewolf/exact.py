"""Public Board calculations for 1–9 players, wolves, medium disclosures and ability-free seers/hunters, using exact fractions."""

from .calculation_budget import tick
from dataclasses import dataclass, replace
from fractions import Fraction
from functools import lru_cache
from itertools import combinations, product
from math import comb
from typing import Literal

Phase = Literal["day", "night"]
Winner = Literal["village", "wolf"]


@dataclass(frozen=True)
class Rules:
    allow_self_bite: bool = False
    initial_seer: str = "random_white"
    allow_repeat_guard: bool = True

    def __post_init__(self):
        if self.initial_seer not in ("normal","random_white","none"):
            raise ValueError("初日占いはあり・ランダム白・なしから選んでください。")
        if type(self.allow_repeat_guard) is not bool:
            raise ValueError("Repeated guard permission must be a boolean")
        if type(self.allow_self_bite) is not bool:
            raise ValueError("Self-bite permission must be a boolean")


@dataclass(frozen=True)
class Strategy:
    day: str = "max"
    night: str = "max"
    include_self_bite: bool = False
    fake_reports: str = "max"
    disclosure_common: str = "all"
    seer_disclosure: str = "inherit"
    medium_disclosure: str = "inherit"
    seer_position: tuple[str,...] = ("unvisited","uniform")
    fake_seer_policy: tuple[str,...] = ("noncontradictory","uniform")
    guard_position: tuple[str,...] = ("uniform",)

    def __post_init__(self):
        if self.disclosure_common not in ('none','all') or self.seer_disclosure not in ('inherit','none','all') or self.medium_disclosure not in ('inherit','none','all'):raise ValueError('Choose none/all disclosure or inherit')
        if isinstance(self.guard_position,list):object.__setattr__(self,'guard_position',tuple(self.guard_position))
        if self.guard_position!=('uniform',):raise ValueError('Only uniform ordered guard-position items are supported')
        if isinstance(self.seer_position,list):object.__setattr__(self,'seer_position',tuple(self.seer_position))
        if self.seer_position!=('unvisited','uniform'):raise ValueError('Only unvisited then uniform scan position is supported')
        if isinstance(self.fake_seer_policy,list):object.__setattr__(self,'fake_seer_policy',tuple(self.fake_seer_policy))
        if self.fake_seer_policy not in (('uniform',),('noncontradictory','uniform')):raise ValueError('Choose noncontradictory then uniform, or uniform alone for fake seer reports')
        if self.day not in ("max", "random") or self.night not in ("max", "random"):
            raise ValueError("Choose max or random")
        if self.fake_reports not in ("max","random"):
            raise ValueError("Choose max or random for fake reports")
        if type(self.include_self_bite) is not bool:
            raise ValueError("Self-bite inclusion must be a boolean")

    def disclosure_for(self, role):
        if role not in ('seer','medium'):return 'none'
        local=getattr(self,role+'_disclosure')
        return self.disclosure_common if local=='inherit' else local


def validate_strategy(rules: Rules, strategy: Strategy):
    if strategy.include_self_bite and not rules.allow_self_bite:
        raise ValueError("The game rule does not permit self-bite")


ROLES = ('villager', 'medium', 'seer', 'hunter', 'wolf')
VILLAGE_ROLES = ROLES[:-1]
ROLE_LABELS = {'villager':'市民','medium':'霊能','seer':'占い師（能力なし）','hunter':'狩人','wolf':'狼','latent':'潜伏'}


@dataclass(frozen=True)
class ClaimPolicy:
    villager: str | tuple[str, ...] | list[str] = 'filled'
    medium: str | tuple[str, ...] | list[str] = 'filled'
    wolf: str = 'none'
    seer: str | tuple[str, ...] | list[str] = 'filled'
    hunter: str | tuple[str, ...] | list[str] = 'filled'

    def __post_init__(self):
        if any(not self.valid_conditions(getattr(self, role)) for role in VILLAGE_ROLES) or self.wolf != 'none':
            raise ValueError("Invalid CO calculation condition")
        for role in VILLAGE_ROLES:
            if isinstance(getattr(self, role), list):
                object.__setattr__(self, role, tuple(getattr(self, role)))

    @staticmethod
    def valid_conditions(value):
        return (value in ('none', 'counter', 'filled') if isinstance(value, str) else
                isinstance(value, (tuple, list)) and all(v in ('counter', 'filled') for v in value) and len(set(value)) == len(value))

    def conditions(self, role):
        value = getattr(self, role)
        return (() if value == 'none' else (value,)) if isinstance(value, str) else tuple(value)


def default_bluff_roles(present):
    # Role settings, shared by both models; not a special case in inference.
    return {r: tuple(c for c in ROLES if c in present) if r=='wolf' else () for r in ROLES}


def compatible_claim(mask_w, mask_m, player, claim, bluff_roles=None):
    role = 'wolf' if mask_w & (1 << (player - 1)) else 'medium' if mask_m & (1 << (player - 1)) else 'villager'
    settings = default_bluff_roles(ROLES) if bluff_roles is None else bluff_roles
    return claim == 'latent' or role == claim or claim in settings.get(role, ())


def world_masks(board, world):
    w,m,seer,hunter,_=world
    return {'wolf':w,'medium':m,'seer':seer,'hunter':hunter,
            'villager':((1<<board.player_count)-1) ^ (w|m|seer|hunter)}


def actual_role(board, world, player):
    bit=1<<(player-1)
    return next(role for role,mask in world_masks(board,world).items() if mask&bit)


def replace_worlds(board, worlds, **changes):
    projection={}
    for w,m,seer,hunter,q in worlds:
        projection[w,m]=projection.get((w,m),Fraction(0))+q
    return replace(board, belief=(), role_belief=tuple((w,m,q) for (w,m),q in sorted(projection.items())),
                   world_belief=tuple(worlds) if board.initial_seer_count or board.initial_hunter_count else (), **changes)


def condition_claims(board, claims, policy=ClaimPolicy(), bluff_roles=None):
    if not isinstance(claims, tuple) or len(claims)!=board.player_count or any(c not in (*ROLES,'latent') for c in claims):
        raise ValueError('CO must identify one allowed role per player')
    counts=board.initial_role_counts
    present={r for world in board.worlds for r,mask in world_masks(board,world).items() if mask}|{'latent'}
    if any(c not in present for c in claims):
        raise ValueError('配役にない役職へのCOは指定できません。')
    settings=default_bluff_roles(present) if bluff_roles is None else bluff_roles
    entries=[]
    for world in board.worlds:
        masks=world_masks(board,world)
        if any(c!='latent' and c!=actual_role(board,world,i) and c not in settings.get(actual_role(board,world,i),())
               for i,c in enumerate(claims,1)):
            continue
        allowed=True
        for role in VILLAGE_ROLES:
            modes=policy.conditions(role);capacity=masks[role].bit_count();claim_count=claims.count(role)
            trigger=('counter' in modes and claim_count>0) or ('filled' in modes and capacity>0 and claim_count>=capacity)
            if trigger and any(masks[role]&(1<<(i-1)) and claims[i-1]!=role for i in board.alive):
                allowed=False;break
        if allowed:entries.append(world)
    mass=sum((world[-1] for world in entries),Fraction(0))
    if not mass:raise ValueError('COと配役・騙り・CCO条件が両立せず矛盾しています。CO人数と計算条件を確認してください。')
    return replace_worlds(board,tuple((*world[:-1],world[-1]/mass) for world in entries),wolf_count=None,claims=claims)


def available_medium_opportunities(board):
    # CO before execution; reporter must survive the intervening night.
    return tuple(o for o in board.medium_opportunities if o[0]<=board.day and
                 not any(e.target==o[1] and (e.day<o[0]) for e in board.history))


def condition_reports(board, reports):
    if not isinstance(reports,tuple) or any(not isinstance(report,MediumReport) for report in reports):raise ValueError('Invalid report collection')
    keys=[(r.day,r.reporter,r.target) for r in reports]
    if len(set(keys))!=len(keys) or not set(keys)<=set(available_medium_opportunities(board)):
        raise ValueError('申告者・処刑対象・公開日が報告機会と一致しません。CO前や翌朝死亡した人の結果は入力できません。')
    entries=[]
    for world in board.worlds:
        w,m,_,_,q=world
        if all(not m&(1<<(r.reporter-1)) or (bool(w&(1<<(r.target-1)))==(r.color=='black')) for r in reports):
            entries.append(world)
    mass=sum((world[-1] for world in entries),Fraction(0))
    if not mass:raise ValueError('霊能申告と公開盤面が矛盾し、合法な候補がありません。')
    return replace_worlds(board,tuple((*world[:-1],world[-1]/mass) for world in entries),reports=reports)


def group_initial_board(board, claims, policy=ClaimPolicy(), bluff_roles=None):
    """Equal legal joint bluff-role placements, then equal legal completions.

    This is an initial snapshot interpretation, never a transition updater.
    """
    if board.history or board.alive != tuple(range(1, board.player_count+1)) or board.phase != 'day' or board.day != 1:
        raise ValueError('COグループの初期配分は初日昼だけで定義します。')
    present = {r for r,n in board.initial_role_counts.items() if n}
    settings=default_bluff_roles(present) if bluff_roles is None else bluff_roles
    if set(settings)-set(ROLES) or any(set(options)-present for options in settings.values()):
        raise ValueError('Unknown bluff-role setting')
    filtered=condition_claims(board,claims,policy,settings)
    faker_roles=tuple(r for r in ROLES if any(c!=r and c in present for c in settings.get(r,())))
    groups={}
    for world in filtered.worlds:
        masks=world_masks(filtered,world)
        key=tuple(masks[r] for r in faker_roles)
        groups.setdefault(key,[]).append(world[:-1])
    entries=tuple((*world,Fraction(1,len(groups)*len(configs))) for configs in groups.values() for world in configs)
    return replace_worlds(filtered,entries)


def co_group_compositions(board):
    groups=[]
    roles=('villager','medium')+tuple(r for r in ('seer','hunter') if board.initial_role_counts[r])+('wolf',)
    for claim in (*ROLES,'latent'):
        ids=tuple(i for i in board.alive if board.claims[i-1]==claim)
        if not ids:continue
        bit=sum(1<<(i-1) for i in ids);counts={}
        for world in board.worlds:
            masks=world_masks(board,world);key=tuple((masks[r]&bit).bit_count() for r in roles)
            counts[key]=counts.get(key,Fraction(0))+world[-1]
        groups.append(dict(claim=claim,ids=ids,roles=roles,visible_roles=tuple(r for r in roles if board.initial_role_counts[r]>0),compositions=tuple((*key,q) for key,q in sorted(counts.items()))))
    return groups


@dataclass(frozen=True)
class PublicEvent:
    day: int
    phase: Phase
    target: int


@dataclass(frozen=True)
class MediumReport:
    day: int
    reporter: int
    target: int
    color: str

    def __post_init__(self):
        if type(self.day) is not int or self.day<2 or type(self.reporter) is not int or type(self.target) is not int or self.color not in ('white','black'):
            raise ValueError('Invalid medium report')


@lru_cache(maxsize=256)
def _validated_complete_roles(player_count,mediums,seers,hunters,worlds):
    """Pure validation/projection of exact immutable complete role laws only.

    Public facts, histories, counts of surviving wolves and guard provenance
    remain validated by Board. No policy, observer or hidden-history inputs
    are inferred here. Mutable/subclass compatibility inputs never enter.
    """
    seen=set();projection={}
    for world in worlds:
        w,m,seer,hunter,q=world
        if any(not 0<=mask<1<<player_count for mask in world[:-1]):raise ValueError('Invalid role masks')
        if any(x&y for j,x in enumerate(world[:-1]) for y in world[j+1:-1]):raise ValueError('Role masks must not overlap')
        if (m.bit_count(),seer.bit_count(),hunter.bit_count())!=(mediums,seers,hunters):raise ValueError('Role counts disagree')
        if world[:-1] in seen or q<=0:raise ValueError('Invalid complete role mass')
        seen.add(world[:-1]);projection[w,m]=projection.get((w,m),Fraction(0))+q
    if sum((x[-1] for x in worlds),Fraction(0))!=1:raise ValueError('Complete role mass must conserve one')
    role=tuple((w,m,q) for (w,m),q in sorted(projection.items()))
    marginal={}
    for w,m,q in role:marginal[w]=marginal.get(w,Fraction(0))+q
    return role,tuple(sorted(marginal.items()))


def _immutable_complete_roles(worlds):
    return (type(worlds)is tuple and all(type(row)is tuple and len(row)==5 and
            all(type(mask)is int for mask in row[:4]) and type(row[-1])is Fraction for row in worlds))


@dataclass(frozen=True)
class Board:
    """Public history and count constraints; no player has an assigned true role."""

    player_count: int
    alive: tuple[int, ...]
    wolf_count: int | None = 1
    day: int = 1
    phase: Phase = "day"
    history: tuple[PublicEvent, ...] = ()

    belief: tuple[tuple[int, Fraction], ...] = ()
    initial_medium_count: int = 0
    claims: tuple[str, ...] = ()
    role_belief: tuple[tuple[int, int, Fraction], ...] = ()
    initial_seer_count: int = 0
    initial_hunter_count: int = 0
    world_belief: tuple[tuple[int, int, int, int, Fraction], ...] = ()
    medium_opportunities: tuple[tuple[int, int, int], ...] = ()
    reports: tuple[MediumReport, ...] = ()
    report_resolved: tuple[tuple[int,int,int], ...] = ()
    guard_prior_roster: tuple | None = None

    def __post_init__(self):
        if type(self.player_count) is not int or not 1 <= self.player_count <= 9:
            raise ValueError("Supports 1–9 players")
        if not isinstance(self.alive, tuple) or len(set(self.alive)) != len(self.alive):
            raise ValueError("Alive IDs must be a distinct tuple")
        if any(type(player) is not int or not 1 <= player <= self.player_count for player in self.alive):
            raise ValueError("Unknown player")
        if self.wolf_count is not None and (type(self.wolf_count) is not int or not 0 <= self.wolf_count <= len(self.alive)):
            raise ValueError("Invalid public wolf-count constraint")
        if type(self.day) is not int or self.day < 1 or self.phase not in ("day", "night"):
            raise ValueError("Invalid Day/Phase")
        if self.guard_prior_roster is not None:
            seed=self.guard_prior_roster
            if (self.initial_hunter_count!=1 or type(seed)is not tuple or len(seed)!=2 or type(seed[0])is not int or not 1<=seed[0]<self.day
                    or type(seed[1])is not tuple or len(seed[1])!=4
                    or any(type(p)is not int or not 1<=p<=self.player_count for p in seed[1]) or len(set(seed[1]))!=len(seed[1])):
                raise ValueError('Invalid public guard-history provenance')
        if not isinstance(self.history, tuple) or any(not isinstance(event, PublicEvent) for event in self.history):
            raise ValueError("Invalid public history")
        dead = tuple(event.target for event in self.history)
        if len(set(dead)) != len(dead) or set(dead) != set(range(1, self.player_count + 1)) - set(self.alive):
            raise ValueError("History and alive players must agree")

        if type(self.initial_medium_count) is not int or not 0 <= self.initial_medium_count <= self.player_count:
            raise ValueError("Invalid medium count")
        if not self.claims:
            object.__setattr__(self, 'claims', ('latent',) * self.player_count)
        if len(self.claims) != self.player_count or any(c not in (*ROLES, 'latent') for c in self.claims):
            raise ValueError("Invalid public CO")
        for count in (self.initial_seer_count,self.initial_hunter_count):
            if type(count) is not int or not 0<=count<=self.player_count:
                raise ValueError('Invalid ability-free role count')
        validated_worlds=False
        if self.world_belief:
            if _immutable_complete_roles(self.world_belief):
                # Bound retention by both entry count and law length. Large
                # exact laws use the identical pure validation without caching.
                project=(_validated_complete_roles if len(self.world_belief)<=64
                         else _validated_complete_roles.__wrapped__)
                role,belief=project(self.player_count,self.initial_medium_count,
                    self.initial_seer_count,self.initial_hunter_count,self.world_belief)
                object.__setattr__(self,'role_belief',role)
                object.__setattr__(self,'belief',belief)
                validated_worlds=True
            else:
                seen=set();projection={}
                for world in self.world_belief:
                    if not isinstance(world,tuple) or len(world)!=5:raise ValueError('Invalid complete role distribution')
                    w,m,seer,hunter,q=world
                    if any(type(mask) is not int or not 0<=mask<1<<self.player_count for mask in world[:-1]):raise ValueError('Invalid role masks')
                    if any(x&y for j,x in enumerate(world[:-1]) for y in world[j+1:-1]):raise ValueError('Role masks must not overlap')
                    if (m.bit_count(),seer.bit_count(),hunter.bit_count())!=(self.initial_medium_count,self.initial_seer_count,self.initial_hunter_count):raise ValueError('Role counts disagree')
                    if world[:-1] in seen or not isinstance(q,Fraction) or q<=0:raise ValueError('Invalid complete role mass')
                    seen.add(world[:-1]);projection[w,m]=projection.get((w,m),Fraction(0))+q
                if sum((x[-1] for x in self.world_belief),Fraction(0))!=1:raise ValueError('Complete role mass must conserve one')
                object.__setattr__(self,'role_belief',tuple((w,m,q) for (w,m),q in sorted(projection.items())))
            if self.guard_prior_roster is not None:
                night,roster=self.guard_prior_roster
                before=set(range(1,self.player_count+1))-{e.target for e in self.history if e.day<night or e.day==night and e.phase=='day'}
                mask=sum(1<<(p-1) for p in roster)
                if set(roster)!=before or self.initial_hunter_count!=1 or any((w[0]&mask).bit_count()!=1 or not w[3]&mask for w in self.world_belief):
                    raise ValueError('Public guard-history provenance conflicts with role/history facts')
        elif self.initial_seer_count or self.initial_hunter_count:
            raise ValueError('Extra roles require complete role distribution')
        if self.role_belief and not validated_worlds:
            if (len({(w, m) for w, m, _ in self.role_belief}) != len(self.role_belief)
                    or any(type(w) is not int or type(m) is not int or w < 0 or m < 0
                           or w >= 1 << self.player_count or m >= 1 << self.player_count
                           or w & m or m.bit_count() != self.initial_medium_count
                           or not isinstance(q, Fraction) or q <= 0 for w, m, q in self.role_belief)
                    or sum((q for _, _, q in self.role_belief), Fraction(0)) != 1):
                raise ValueError("Use an exact joint wolf/medium distribution")
            marginal = {}
            for wolf, _, q in self.role_belief:
                marginal[wolf] = marginal.get(wolf, Fraction(0)) + q
            object.__setattr__(self, 'belief', tuple(sorted(marginal.items())))
        if not self.belief:
            if self.wolf_count is None:
                raise ValueError("A mixed count needs an exact belief")
            masks = [sum(1 << (i - 1) for i in ids) for ids in combinations(self.alive, self.wolf_count)]
            # Compatibility for direct one-wolf terminal Board construction.
            if self.wolf_count == 0 and self.history:
                masks = [1 << (self.history[-1].target - 1)]
            object.__setattr__(self, 'belief', tuple((mask, Fraction(1, len(masks))) for mask in masks))
        if not validated_worlds and (len({m for m, _ in self.belief}) != len(self.belief)
                or any(type(m) is not int or not 0 <= m < 1 << self.player_count
                       or not isinstance(q, Fraction) or q <= 0 for m, q in self.belief)
                or sum((q for _, q in self.belief), Fraction(0)) != 1):
            raise ValueError("Belief must be a normalized exact joint distribution")
        if not self.role_belief:
            joint = []
            for wolf, q in self.belief:
                available = tuple(i for i in range(self.player_count) if not wolf & (1 << i))
                if self.initial_medium_count > len(available):
                    raise ValueError("Role counts exceed player count")
                medium_sets = tuple(combinations(available, self.initial_medium_count))
                joint.extend((wolf, sum(1 << i for i in ids), q / len(medium_sets)) for ids in medium_sets)
            object.__setattr__(self, 'role_belief', tuple(joint))
        counts = self.wolf_count_distribution
        exact = next(iter(counts)) if len(counts) == 1 else None
        if self.wolf_count is not None and self.wolf_count != exact:
            raise ValueError("Count and joint distribution disagree")
        object.__setattr__(self, 'wolf_count', exact)

    @property
    def alive_mask(self):
        return sum(1 << (i - 1) for i in self.alive)

    @property
    def wolf_count_distribution(self) -> dict[int, Fraction]:
        cached=getattr(self,'_wolf_counts_cache',None)
        if cached is not None and cached[0] is self.alive and cached[1] is self.belief:
            return dict(cached[2])
        result = {}
        alive_mask=self.alive_mask
        for mask, weight in self.belief:
            count = (mask & alive_mask).bit_count()
            result[count] = result.get(count, Fraction(0)) + weight
        items=tuple(sorted(result.items()))
        # Derived exact sum only; frozen canonical inputs and a fresh dict for
        # every caller. Mutable compatibility inputs remain uncached.
        if (type(self.alive)is tuple and type(self.belief)is tuple and
                all(type(pair)is tuple and type(pair[0])is int and type(pair[1])is Fraction
                    for pair in self.belief)):
            object.__setattr__(self,'_wolf_counts_cache',(self.alive,self.belief,items))
        return dict(items)

    @property
    def villagers(self) -> int | None:
        return None if self.wolf_count is None else len(self.alive) - self.wolf_count

    @property
    def winner(self) -> Winner | None:
        winners = {winner_for(len(self.alive), w) for w in self.wolf_count_distribution}
        return next(iter(winners)) if len(winners) == 1 else None

    def wolf_probability(self, player: int) -> Fraction:
        if type(player) is not int or not 1 <= player <= self.player_count:
            raise ValueError("Unknown player")
        return sum((q for mask, q in self.belief if mask & (1 << (player - 1))), Fraction(0))

    @property
    def worlds(self):
        return self.world_belief or tuple((w,m,0,0,q) for w,m,q in self.role_belief)

    @property
    def initial_role_counts(self):
        # Wolf count includes dead positions and is fixed across complete worlds.
        wolves=self.worlds[0][0].bit_count()
        return {'wolf':wolves,'medium':self.initial_medium_count,'seer':self.initial_seer_count,
                'hunter':self.initial_hunter_count,
                'villager':self.player_count-wolves-self.initial_medium_count-self.initial_seer_count-self.initial_hunter_count}

    def role_probability(self, player: int, role: str) -> Fraction:
        if type(player) is not int or not 1<=player<=self.player_count or role not in ROLES:raise ValueError('Unknown player or role')
        bit=1<<(player-1)
        if role=='wolf':return self.wolf_probability(player)
        if role=='medium':return sum((q for w,m,q in self.role_belief if m&bit),Fraction(0))
        if role in ('seer','hunter'):
            index=2 if role=='seer' else 3
            return sum((world[-1] for world in self.worlds if world[index]&bit),Fraction(0))
        return sum((q for w,m,seer,hunter,q in self.worlds if not (w|m|seer|hunter)&bit),Fraction(0))

    def joint_wolf_probability(self, players: tuple[int, ...]) -> Fraction:
        if any(type(i) is not int or not 1 <= i <= self.player_count for i in players):
            raise ValueError("Unknown player")
        required = sum(1 << (i - 1) for i in set(players))
        return sum((q for mask, q in self.belief if mask & required == required), Fraction(0))


def winner_for(n: int, wolves: int) -> Winner | None:
    return "village" if wolves == 0 else "wolf" if wolves >= n - wolves else None


def initial_board(player_count: int = 5, wolf_count: int = 1, medium_count: int = 0, seer_count: int = 0, hunter_count: int = 0, *, experimental_cast: bool = False) -> Board:
    if type(player_count) is not int or not 1 <= player_count <= 9:
        raise ValueError("Choose 1–9 players")
    if type(experimental_cast)is not bool:raise ValueError("Explicit experimental cast flag required")
    if type(wolf_count) is not int or not (0 <= wolf_count <= player_count if experimental_cast or player_count <= 2 else 1 <= wolf_count <= (player_count - 1) // 2):
        raise ValueError("Choose wolves fewer than villagers")
    if type(medium_count) is not int or not 0 <= medium_count <= player_count - wolf_count:
        raise ValueError("Choose medium count within the village camp")
    if any(type(c) is not int or c<0 for c in (seer_count,hunter_count)) or medium_count+seer_count+hunter_count>player_count-wolf_count:
        raise ValueError('Choose role counts within the village camp')
    worlds=[]
    if seer_count or hunter_count:
        ids=tuple(range(player_count))
        def mask(positions):return sum(1<<i for i in positions)
        for ws in combinations(ids,wolf_count):
            rest=tuple(i for i in ids if i not in ws)
            for ms in combinations(rest,medium_count):
                rest_s=tuple(i for i in rest if i not in ms)
                for ss in combinations(rest_s,seer_count):
                    rest_h=tuple(i for i in rest_s if i not in ss)
                    for hs in combinations(rest_h,hunter_count):worlds.append((mask(ws),mask(ms),mask(ss),mask(hs)))
        worlds=tuple((*world,Fraction(1,len(worlds))) for world in worlds)
    return Board(player_count,tuple(range(1,player_count+1)),wolf_count,initial_medium_count=medium_count,
                 initial_seer_count=seer_count,initial_hunter_count=hunter_count,world_belief=tuple(worlds))


@dataclass(frozen=True)
class BoardOutcome:
    probability: Fraction
    board: Board


def legal_targets(board: Board, rules: Rules, strategy: Strategy) -> tuple[int, ...]:
    validate_strategy(rules, strategy)
    if board.winner:
        return ()
    if board.phase == 'day' or strategy.include_self_bite:
        return board.alive
    alive_mask = board.alive_mask
    counts = set(board.wolf_count_distribution)
    return tuple(i for i in board.alive if
                 {(w & alive_mask).bit_count() for w, _ in board.belief if not w & (1 << (i - 1))} == counts)


def forced_action_worlds(board, target, rules, strategy):
    """Target intervention: exclude self-bite worlds within each live count.

    Preserve the count prior, distinct from conditioning an observed corpse.
    Callers use legal_targets first; missing support is never silently dropped.
    """
    if board.phase != 'night' or strategy.include_self_bite:return board.worlds
    bit=1<<(target-1);alive_mask=board.alive_mask
    count_weights=board.wolf_count_distribution;normalizers={}
    for mask,q in board.belief:
        if not mask&bit:
            w=(mask&alive_mask).bit_count()
            normalizers[w]=normalizers.get(w,Fraction())+q
    if set(normalizers)!=set(count_weights):
        raise ValueError('Target cannot be legally bitten in every count hypothesis')
    return tuple((*world[:-1],world[-1]*count_weights[(world[0]&alive_mask).bit_count()]/
                  normalizers[(world[0]&alive_mask).bit_count()])
                 for world in board.worlds if not world[0]&bit)


def action_outcomes(board: Board, target: int, rules: Rules, strategy: Strategy) -> tuple[BoardOutcome, ...]:
    validate_strategy(rules, strategy)
    if board.winner is not None:
        raise ValueError("A terminal Board cannot advance")
    if type(target) is not int or target not in legal_targets(board, rules, strategy):
        raise ValueError("Choose a living player")
    alive = tuple(player for player in board.alive if player != target)
    bit = 1 << (target - 1)
    groups = {}
    alive_mask = board.alive_mask
    for mask, medium, seer, hunter, q in forced_action_worlds(board,target,rules,strategy):
        w = (mask & (alive_mask ^ bit)).bit_count()
        winner = winner_for(len(alive), w)
        groups.setdefault(winner, []).append((mask, medium, seer, hunter, q))
    event = PublicEvent(board.day, board.phase, target)
    outcomes = []
    for winner in ('village', 'wolf', None):
        entries = groups.get(winner)
        if not entries:
            continue
        mass = sum((world[-1] for world in entries), Fraction(0))
        phase = board.phase if winner else ('night' if board.phase == 'day' else 'day')
        day = board.day + int(not winner and board.phase == 'night')
        child = Board(board.player_count, alive, None, day, phase, board.history + (event,),
                      initial_medium_count=board.initial_medium_count, claims=board.claims,
                      medium_opportunities=board.medium_opportunities+tuple((board.day+1,i,target) for i in alive if board.phase=='day' and board.claims[i-1]=='medium'),
                      reports=board.reports,report_resolved=board.report_resolved,
                      initial_seer_count=board.initial_seer_count,initial_hunter_count=board.initial_hunter_count,
                      guard_prior_roster=board.guard_prior_roster,
                      world_belief=tuple((w,m,seer,hunter,q/mass) for w,m,seer,hunter,q in entries) if board.world_belief else (),
                      role_belief=tuple((w,m,q/mass) for w,m,_,_,q in entries) if not board.world_belief else ())
        outcomes.append(BoardOutcome(mass, child))
    return tuple(outcomes)


@dataclass(frozen=True)
class Action:
    target: int
    outcomes: tuple["Chance", ...]


@dataclass(frozen=True)
class Chance:
    probability: Fraction
    child: "TreeNode"


@dataclass(frozen=True)
class ReportTreeAction:
    fake_colors: tuple[tuple[int,str], ...]
    outcomes: tuple[Chance, ...]


@dataclass(frozen=True)
class TreeNode:
    """Lazy view of every exact action/chance branch; histories are never pruned."""
    board: Board
    rules: Rules = Rules()
    strategy: Strategy = Strategy()
    pending_disclosure: bool = False

    @property
    def disclosures(self):
        if not self.pending_disclosure or self.strategy.disclosure_for('medium')=='none':return ()
        if self.strategy.fake_reports=='random':
            outcomes=random_report_outcomes(self.board)
            return (ReportTreeAction((),tuple(Chance(o.probability,TreeNode(o.board,self.rules,self.strategy)) for o in outcomes)),) if outcomes else ()
        return tuple(ReportTreeAction(a.fake_colors,tuple(Chance(o.probability,TreeNode(o.board,self.rules,self.strategy)) for o in a.outcomes)) for a in report_actions(self.board))

    @property
    def actions(self) -> tuple[Action, ...]:
        if self.board.winner or self.disclosures:
            return ()
        return tuple(Action(target, tuple(Chance(o.probability, TreeNode(o.board,self.rules,self.strategy,pending_disclosure=self.board.phase=='night'))
                     for o in action_outcomes(self.board, target, self.rules, self.strategy)))
                     for target in legal_targets(self.board, self.rules, self.strategy))


def build_tree(board: Board, rules: Rules, strategy: Strategy) -> TreeNode:
    validate_strategy(rules, strategy)
    return TreeNode(board, rules, strategy)


@dataclass(frozen=True)
class Values:
    village_win: Fraction
    wolf_win: Fraction

    def __post_init__(self):
        if not isinstance(self.village_win, Fraction) or not isinstance(self.wolf_win, Fraction):
            raise ValueError("Use exact Fractions")
        if self.village_win < 0 or self.wolf_win < 0 or self.village_win + self.wolf_win != 1:
            raise ValueError("Win probabilities must conserve one")


def aggregate_values(phase: Phase, candidates: tuple[Values, ...], strategy: Strategy) -> Values:
    """A public Board aggregation, without selecting or weighting maximum ties."""
    if not candidates or phase not in ("day", "night"):
        raise ValueError("A valid phase and action candidates are required")
    mode = strategy.day if phase == "day" else strategy.night
    if mode == "random":
        village = sum((value.village_win for value in candidates), Fraction(0)) / len(candidates)
    elif phase == "day":
        village = max(value.village_win for value in candidates)
    else:
        village = 1 - max(value.wolf_win for value in candidates)
    return Values(village, 1 - village)


def marginal_state(board):
    result = {}
    for mask, q in board.belief:
        compact = sum(1 << j for j, i in enumerate(board.alive) if mask & (1 << (i - 1)))
        result[compact] = result.get(compact, Fraction(0)) + q
    return tuple(sorted(result.items()))


@lru_cache(maxsize=4096)
def solve(n, phase, belief, strategy):
    """Backward induction on exact public states, sharing equivalent histories.

    Exchangeable survivors have identical action subtrees up to relabeling.
    Their count distribution is a sufficient statistic for future values,
    but full correlated location beliefs remain on displayed Boards.
    """
    tick(len(belief))
    counts = {}
    for mask, q in belief:
        w = mask.bit_count()
        counts[w] = counts.get(w, Fraction(0)) + q
    winners = {winner_for(n, w) for w in counts}
    if len(winners) == 1 and None not in winners:
        return Values(Fraction(int('village' in winners)), Fraction(int('wolf' in winners)))
    symmetric = all(q == counts[m.bit_count()] / comb(n, m.bit_count()) for m, q in belief)
    symmetric &= len(belief) == sum(comb(n, w) for w in counts)
    if symmetric:
        candidates = (symmetric_action(n, phase, tuple(sorted(counts.items())), strategy),) * n
    else:
        # General joint beliefs: one public optimization after all candidates.
        board = Board(max(3, n), tuple(range(1, n + 1)), None, phase=phase, belief=belief)
        candidates = tuple(value_for_action(board, i, Rules(strategy.include_self_bite), strategy)
                           for i in legal_targets(board, Rules(strategy.include_self_bite), strategy))
    return aggregate_values(phase, candidates, strategy)


@lru_cache(maxsize=4096)
def symmetric_action(n, phase, counts, strategy):
    tick(len(counts))
    village, continuing = Fraction(0), {}
    for w, mass in counts:
        hits = ((w - 1, Fraction(w, n)), (w, Fraction(n - w, n))) if phase == 'day' or strategy.include_self_bite else ((w, Fraction(1)),)
        for remaining, probability in hits:
            if not probability:
                continue
            q = mass * probability
            winner = winner_for(n - 1, remaining)
            if winner == 'village':
                village += q
            elif winner is None:
                continuing[remaining] = continuing.get(remaining, Fraction(0)) + q
    mass = sum(continuing.values(), Fraction(0))
    if mass:
        belief = tuple(sorted((sum(1 << i for i in ids), q / mass / comb(n - 1, w))
                       for w, q in continuing.items() for ids in combinations(range(n - 1), w)))
        village += mass * solve(n - 1, 'night' if phase == 'day' else 'day', belief, strategy).village_win
    return Values(village, 1 - village)


@dataclass(frozen=True)
class ReportAction:
    # One public contingent instruction per possibly fake CO position.
    fake_colors: tuple[tuple[int, str], ...]
    outcomes: tuple[BoardOutcome, ...]


def report_actions(board):
    if board.winner:return ()
    supplied={(r.day,r.reporter,r.target) for r in board.reports}
    opportunities=tuple(o for o in available_medium_opportunities(board)
                        if o[0]==board.day and o not in board.report_resolved and o not in supplied)
    if not opportunities:return ()
    possible_fakes=tuple(sorted({o[1] for o in opportunities if board.wolf_probability(o[1])>0}))
    actions=[]
    for colors in product(('white','black'),repeat=len(possible_fakes)):
        instructions=dict(zip(possible_fakes,colors));groups={}
        for world in board.worlds:
            w,m,_,_,q=world
            reports=tuple(MediumReport(day,reporter,target,
                         ('black' if w&(1<<(target-1)) else 'white') if m&(1<<(reporter-1)) else instructions[reporter])
                         for day,reporter,target in opportunities)
            groups.setdefault(reports,[]).append(world)
        outcomes=[]
        for reports,entries in sorted(groups.items(),key=lambda item:tuple(r.color for r in item[0])):
            mass=sum((world[-1] for world in entries),Fraction(0))
            child=replace_worlds(board,tuple((*world[:-1],world[-1]/mass) for world in entries),
                                 reports=board.reports+reports,report_resolved=board.report_resolved+opportunities)
            outcomes.append(BoardOutcome(mass,child))
        actions.append(ReportAction(tuple(zip(possible_fakes,colors)),tuple(outcomes)))
    return tuple(actions)


def joint_value(board, rules, strategy, reveal_now=False):
    from .reports import public_value
    village=public_value(board,strategy,reveal_now)
    return Values(village,1-village)


def random_report_outcomes(board):
    actions=report_actions(board)
    if not actions:return ()
    return merge_report_outcomes(BoardOutcome(outcome.probability/len(actions),outcome.board)
                                 for action in actions for outcome in action.outcomes)


def merge_report_outcomes(outcomes):
    """Merge weighted instructions from one morning by their public vector.

    Recompute the live wolf count after merging; a representative instruction
    may have a narrower count support than the resulting public observation.
    """
    groups={}
    for outcome in outcomes:
        key=outcome.board.reports
        child,entries=groups.setdefault(key,(outcome.board,{}))
        for world in outcome.board.worlds:
            entries[world[:-1]]=entries.get(world[:-1],Fraction(0))+outcome.probability*world[-1]
    results=[]
    for child,entries in groups.values():
        mass=sum(entries.values(),Fraction(0))
        # Equal public vectors can merge different fake instructions with
        # different live-count supports; infer the count from the merged law.
        results.append(BoardOutcome(mass,replace_worlds(child,tuple((*world,q/mass) for world,q in sorted(entries.items())),wolf_count=None)))
    return tuple(results)


def has_future_medium(board, reveal_now=False):
    return bool(board.initial_medium_count and (any(board.claims[i-1]=='medium' for i in board.alive) or
                any(o[1] in board.alive and o[0]==board.day+(0 if reveal_now else 1 if board.phase=='night' else -1)
                    for o in board.medium_opportunities)))


def value_for_action(board, target, rules, strategy):
    tick(len(board.worlds))
    village=sum((o.probability*(joint_value(o.board,rules,strategy,reveal_now=board.phase=='night').village_win
                 if strategy.disclosure_for('medium')=='all' and has_future_medium(o.board,reveal_now=board.phase=='night') else
                 solve(len(o.board.alive),o.board.phase,marginal_state(o.board),strategy).village_win)
                 for o in action_outcomes(board,target,rules,strategy)),Fraction(0))
    return Values(village,1-village)


@dataclass
class Evaluation:
    strategy: Strategy

    def board_value(self, node: TreeNode) -> Values:
        tick(len(node.board.worlds))
        return joint_value(node.board,node.rules,self.strategy,reveal_now=node.pending_disclosure) if self.strategy.disclosure_for('medium')=='all' and has_future_medium(node.board,node.pending_disclosure) else solve(len(node.board.alive),node.board.phase,marginal_state(node.board),self.strategy)

    def action_value(self, node: TreeNode, target: int) -> Values:
        return value_for_action(node.board, target, node.rules, self.strategy)


def evaluate_tree(root: TreeNode, strategy: Strategy) -> Evaluation:
    validate_strategy(root.rules, strategy)
    result = Evaluation(strategy)
    result.board_value(root)  # Complete terminal-to-root evaluation before rendering.
    return result


@dataclass(frozen=True)
class Progress:
    board: Board | None
    settled_village: Fraction = Fraction(0)
    settled_wolf: Fraction = Fraction(0)
    last_board: Board | None = None
    last_outcomes: tuple[BoardOutcome, ...] = ()
    guard_state: object = None  # Public joint night prior; never an owner-conditioned law.

    def __post_init__(self):
        if any(not isinstance(value, Fraction) or value < 0 for value in (self.settled_village, self.settled_wolf)):
            raise ValueError("Settled mass must be exact and nonnegative")
        settled = self.settled_village + self.settled_wolf
        if settled > 1 or (self.board is None and settled != 1) or (self.board is not None and settled >= 1):
            raise ValueError("Resolved and ongoing probabilities must conserve one")
        if self.board is not None and self.board.winner is not None:
            raise ValueError("Only a continuing Board can be active")

    @classmethod
    def initial(cls, board: Board) -> "Progress":
        """Apply the ordinary winner rule before any public action."""
        if board.winner is None:
            return cls(board)
        village = Fraction(int(board.winner == "village"))
        return cls(None, village, 1 - village, board, (BoardOutcome(Fraction(1), board),))

    @property
    def active_mass(self) -> Fraction:
        return 1 - self.settled_village - self.settled_wolf

    @property
    def finished(self) -> bool:
        return self.board is None

    def total_values(self, continuation: Values | None = None) -> Values:
        if self.board is not None and continuation is None:
            raise ValueError("A continuing Board needs its evaluated value")
        village = self.settled_village + (self.active_mass * continuation.village_win if continuation else 0)
        return Values(village, 1 - village)


def advance(progress: Progress, target: int, rules: Rules, strategy: Strategy) -> Progress:
    if progress.finished:
        raise ValueError("The analysis has finished")
    outcomes = action_outcomes(progress.board, target, rules, strategy)
    village, wolf = progress.settled_village, progress.settled_wolf
    continuing = []
    for outcome in outcomes:
        if outcome.board.winner == "village":
            village += progress.active_mass * outcome.probability
        elif outcome.board.winner == "wolf":
            wolf += progress.active_mass * outcome.probability
        else:
            continuing.append(outcome.board)
    if len(continuing) > 1:
        raise ValueError("Continuing hypotheses must be merged into one public Board")
    return Progress(continuing[0] if continuing else None, village, wolf, progress.board, outcomes)
