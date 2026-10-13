"""Board-owned public night observations, separate from choosing a wolf action.

The first implementation supports a single observed night death. Missing, empty,
and multiple-death observations stay distinct; unsupported observations may be
recorded, but may not be advanced with a fabricated transition probability.
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


def unsupported_reason(observation):
    if observation is None:
        return '夜明けの死体が未入力です。'
    if not observation['deaths']:
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
    reason = unsupported_reason(observation)
    if reason:
        raise ValueError(reason)
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
    if step['observation'] != OBSERVATION or step.get('deaths') != [step['target']]:
        raise ValueError('夜明けの保存履歴が不正です。')
    return observe(progress, {'deaths': step['deaths']}, rules, Strategy(**step['policy']))
