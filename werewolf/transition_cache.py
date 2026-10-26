"""Eligibility for a calculation-owned pure Board-transition memo."""
from dataclasses import fields
from fractions import Fraction
from .exact import Board,Rules,Strategy,PublicEvent,MediumReport,_immutable_complete_roles

_BOARD_FIELDS=('player_count','alive','wolf_count','day','phase','history','belief','initial_medium_count','claims','role_belief','initial_seer_count','initial_hunter_count','world_belief','medium_opportunities','reports','report_resolved','guard_prior_roster')
_KNOWN=(tuple(f.name for f in fields(Board))==_BOARD_FIELDS and
        tuple(f.name for f in fields(PublicEvent))==('day','phase','target') and
        tuple(f.name for f in fields(MediumReport))==('day','reporter','target','color'))


def cacheable_transition(b,rules,strategy):
    # Exact frozen records only; mutable/subclass compatibility still computes.
    if not _KNOWN or type(b)is not Board or type(rules)is not Rules or type(strategy)is not Strategy:return False
    if any(type(getattr(b,k))is not tuple for k in ('alive','history','belief','claims','role_belief','world_belief','medium_opportunities','reports','report_resolved')):return False
    if type(b.phase)is not str or any(type(c)is not str for c in b.claims):return False
    if any(type(e)is not PublicEvent or type(e.day)is not int or type(e.phase)is not str or type(e.target)is not int for e in b.history):return False
    if any(type(r)is not MediumReport or any(type(v)is not int for v in (r.day,r.reporter,r.target)) or type(r.color)is not str for r in b.reports):return False
    if any(type(row)is not tuple or type(row[-1])is not Fraction for row in (*b.belief,*b.role_belief)):return False
    if any(type(row)is not tuple or any(type(v)is not int for v in row) for row in (*b.medium_opportunities,*b.report_resolved)):return False
    if not _immutable_complete_roles(b.worlds):return False
    for value in (*vars(rules).values(),*vars(strategy).values()):
        if type(value) in (bool,str):continue
        if type(value)is tuple and all(type(v)is str for v in value):continue
        return False
    return True
