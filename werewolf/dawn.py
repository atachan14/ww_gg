"""Board-owned public night observations, separate from choosing a wolf action.

A single corpse and an empty observation with a public-known single guardian
are supported. Missing, empty and multiple-death observations stay distinct;
unsupported observations never advance with a fabricated probability.
"""
from copy import deepcopy

from .exact import Progress, Strategy, advance

FLOW = 'public-dawn-v1'
OBSERVATION = 'night-deaths-v1'


def enabled(game):
    return game.get('board_flow') == FLOW


def validate_observation(value, alive):
    if value is None:
        return None
    if (type(value) is not dict or set(value) != {'deaths'}
            or type(value['deaths']) is not list
            or any(type(p) is not int or p not in alive for p in value['deaths'])
            or len(set(value['deaths'])) != len(value['deaths'])):
        raise ValueError('死体は現在生存しているプレイヤーから指定してください。')
    return {'deaths': sorted(value['deaths'])}


def unsupported_reason(observation,board=None,rules=None):
    if observation is None:
        return '夜明けの死体が未入力です。'
    from .guard_model import live_guard_mass
    if not observation['deaths'] and not (board is not None and rules is not None and board.initial_hunter_count==1 and live_guard_mass(board) and rules.allow_repeat_guard):
        return '死体なしの進行は未対応です。'
    if len(observation['deaths']) > 1:
        return '複数死体の進行は未対応です。'
    return None


def current_observation(game):
    log = game['public_log']
    return log['board_graph']['nodes'][log['board_id']].get('system_observation')


def record_observation(game, observation):
    from .board_owned_log import commit_owned_change
    result = deepcopy(game)
    graph = result['public_log']['board_graph']
    owner = graph['current']
    node = graph['nodes'][owner]
    if node['phase'] != 'dawn':
        raise ValueError('死体報告は夜明けBoardで行ってください。')
    if node.get('system_observation') != observation:
        node['system_observation'] = deepcopy(observation)
        node['revision'] += 1
        node['input_revision'] += 1
    return commit_owned_change(game, result)


def observe(progress, observation, rules, strategy):
    if progress.finished or progress.board.phase != 'night':
        raise ValueError('夜明けに到達していません。')
    observation = validate_observation(observation, progress.board.alive)
    reason = unsupported_reason(observation,progress.board,rules)
    if reason:
        raise ValueError(reason)
    if not observation['deaths']:
        from dataclasses import replace
        from .exact import BoardOutcome
        from fractions import Fraction
        from .guard_model import condition_guard_observation
        board=replace(condition_guard_observation(progress.board,(),rules),day=progress.board.day+1,phase='day')
        from .guard_history_prior import role_exchangeable
        before=progress.board
        first=not any(not any(e.phase=='night' and e.day==night for e in before.history) for night in range(1,before.day))
        if first and not rules.allow_self_bite and len(before.alive)==4 and before.initial_hunter_count==1 and set(before.wolf_count_distribution)=={1} and not before.initial_medium_count and not before.initial_seer_count and (strategy.night=='random' or role_exchangeable(before)):
            board=replace(board,guard_prior_roster=(before.day,before.alive))
        return Progress(board,progress.settled_village,progress.settled_wolf,progress.board,
                        (BoardOutcome(Fraction(1),board),))
    target = observation['deaths'][0]
    from .phase_updates import condition_night_corpse, observed_night_strategy
    try:
        board = condition_night_corpse(progress.board, target, rules)
    except ValueError:
        raise ValueError('この死体報告とルールに整合する配役がありません。')
    conditioned = Progress(board, progress.settled_village, progress.settled_wolf,
                           progress.last_board, progress.last_outcomes)
    return advance(conditioned, target, rules, observed_night_strategy(rules, strategy))



def advance_step(progress, step, rules):
    if 'observation' not in step:
        if 'deaths' in step:
            raise ValueError('死体履歴の種別がありません。')
        return advance(progress, step['target'], rules, Strategy(**step['policy']))
    if step['observation'] != OBSERVATION or step.get('deaths') != ([] if step['target'] is None else [step['target']]):
        raise ValueError('夜明けの保存履歴が不正です。')
    return observe(progress, {'deaths': step['deaths']}, rules, Strategy(**step['policy']))
