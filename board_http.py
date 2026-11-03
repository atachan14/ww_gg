"""HTTP of the v0.8 screen: one stateless request per Board, the history stays in the browser."""
from flask import jsonify, render_template, request

from werewolf.calculation_budget import tick
from wwcore import (Board, BoardContradiction, Cast, InvalidBoard, Rules, Strategy, bite, co, column,
                    evaluate, execute, read_board, report)
from wwcore.model import COLOR_NAMES, FAKE_REPORT_STAGES, ROLE_NAMES, SEER_TARGET_STAGES

MAX_BODY = 64 * 1024
MAX_PLAYERS = 9


def fraction_rows(rows):
    return {str(key): {name: str(value) for name, value in row.items()} for key, row in rows.items()}


def event_json(event):
    if event[0] == 'col':
        return {'kind': 'col', 'acts': [
            {'kind': 'co', 'player': act[1], 'role': ROLE_NAMES[act[2]]} if act[0] == 'co' else
            {'kind': 'report', 'player': act[1], 'target': act[2], 'color': COLOR_NAMES[act[3]]}
            for act in event[1]]}
    return {'kind': event[0], 'player': event[1]}


def result_json(result, stage_only=False):
    data = {
        'stage': result.stage,
        'role_rates': fraction_rows(result.role_rates),
        'alive_wolves': {str(count): str(p) for count, p in sorted(result.alive_wolves.items())},
        'win_rates': {name: str(value) for name, value in result.win_rates.items()},
        'action_rates': {str(player): str(value) for player, value in result.action_rates.items()},
        'action_ends': fraction_rows(result.action_ends),
        'branches': [{'event': event_json(event), 'probability': str(p)} for event, p in result.branches],
        'complete': not stage_only,
    }
    if result.children:
        data['children'] = [{'event': event_json(event), 'result': result_json(child)} for event, child in result.children]
    return data


def number(data, key, default=None):
    value = data.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidBoard(f'{key} must be an integer')
    return value


def text_list(data, key, default):
    value = data.get(key, default)
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        raise InvalidBoard(f'{key} must be a list of names')
    return tuple(value)


def flag(data, key, default):
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise InvalidBoard(f'{key} must be true or false')
    return value


def mapping(data, key):
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise InvalidBoard(f'{key} must be an object')
    return value


def parse_event(data):
    if not isinstance(data, dict):
        raise InvalidBoard('An event must be an object')
    kind = data.get('kind')
    if kind == 'col':
        acts = data.get('acts', [])
        if not isinstance(acts, list):
            raise InvalidBoard('acts must be a list')
        parsed = []
        for act in acts:
            if not isinstance(act, dict):
                raise InvalidBoard('An act must be an object')
            if act.get('kind') == 'co' and act.get('role') in ('seer', 'medium'):
                parsed.append(co(number(act, 'player'), act['role']))
            elif act.get('kind') == 'report' and act.get('color') in COLOR_NAMES:
                parsed.append(report(number(act, 'player'), number(act, 'target'), act['color']))
            else:
                raise InvalidBoard('Unknown act')
        return column(*parsed)
    if kind == 'exec':
        return execute(number(data, 'player'))
    if kind == 'bite':
        return bite(number(data, 'player'))
    raise InvalidBoard('Unknown event')


def parse_board(data):
    if not isinstance(data, dict):
        raise InvalidBoard('The request must be an object')
    cast, rules, strategy = mapping(data, 'cast'), mapping(data, 'rules'), mapping(data, 'strategy')
    base = Strategy()
    counts = Cast(number(cast, 'villager', 0), number(cast, 'seer', 0), number(cast, 'medium', 0),
                  number(cast, 'wolf', 1))
    if counts.players > MAX_PLAYERS:
        raise InvalidBoard(f'The cast can have at most {MAX_PLAYERS} players')
    log = data.get('log', [])
    if not isinstance(log, list):
        raise InvalidBoard('log must be a list')
    return Board(
        cast=counts,
        log=tuple(parse_event(event) for event in log),
        rules=Rules(self_bite=flag(rules, 'self_bite', False),
                    first_night=rules.get('first_night', 'random_white')),
        strategy=Strategy(
            wolf_claims=text_list(strategy, 'wolf_claims', base.wolf_claims),
            co_on_saturation=flag(strategy, 'co_on_saturation', base.co_on_saturation),
            co_on_black=flag(strategy, 'co_on_black', base.co_on_black),
            disclose_black=flag(strategy, 'disclose_black', base.disclose_black),
            disclose_all=flag(strategy, 'disclose_all', base.disclose_all),
            seer_target=text_list(strategy, 'seer_target', base.seer_target),
            fake_report=text_list(strategy, 'fake_report', base.fake_report),
            bite=strategy.get('bite', base.bite),
            execution=strategy.get('execution', base.execution)))


def register_core(app):
    @app.get('/')
    def core_page():
        return render_template('core.html', strategy_defaults={
            'seer_target': SEER_TARGET_STAGES, 'fake_report': FAKE_REPORT_STAGES})

    @app.post('/core/board')
    def core_board():
        request.max_content_length = MAX_BODY
        check = tick
        try:
            board = parse_board(request.get_json())
            if request.args.get('scope') == 'read':
                return jsonify(result_json(read_board(board, check=check), stage_only=True))
            return jsonify(result_json(evaluate(board, check=check)))
        except InvalidBoard as error:
            return jsonify(error=str(error), kind='invalid'), 400
        except BoardContradiction as error:
            return jsonify(error=str(error), kind='contradiction'), 422


