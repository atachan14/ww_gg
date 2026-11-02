"""Cold timings of the v0.7 core. `--oracle` also runs the independent enumeration."""
import argparse
import json
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]

from wwcore import Board, Cast, Strategy, WorkLimitExceeded, co, column, evaluate, report  # noqa: E402


def claimed_seers_white(cast):
    """PERFORMANCE.md: P1 and P2 claim seer, both report P3 white, P3 claims medium."""
    return Board(cast, (column(co(1, 'seer'), co(2, 'seer'), report(1, 3, 'white'), report(2, 3, 'white'),
                               co(3, 'medium')),))


CASES = {
    'seven_claims': lambda: claimed_seers_white(Cast(villager=3, medium=1, seer=1, wolf=2)),
    'seven_quiet': lambda: Board(Cast(villager=3, medium=1, seer=1, wolf=2)),
    'seven_uniform_filter': lambda: Board(Cast(villager=3, medium=1, seer=1, wolf=2),
                                          claimed_seers_white(Cast(villager=3, medium=1, seer=1, wolf=2)).log,
                                          strategy=Strategy(seer_target=('uniform',))),
    'eight_claims': lambda: claimed_seers_white(Cast(villager=4, medium=1, seer=1, wolf=2)),
    'nine_claims': lambda: claimed_seers_white(Cast(villager=4, medium=1, seer=1, wolf=3)),
    'nine_quiet': lambda: Board(Cast(villager=4, medium=1, seer=1, wolf=3)),
}


def measure(name, memory):
    board = CASES[name]()
    if memory:
        tracemalloc.start()
    start = time.perf_counter()
    result = evaluate(board)
    seconds = time.perf_counter() - start
    peak = tracemalloc.get_traced_memory()[1] if memory else None
    if memory:
        tracemalloc.stop()
    village = result.win_rates['village']
    return {'case': name, 'seconds': round(seconds, 3), 'village': str(village), 'stats': result.stats,
            'peak_mib': round(peak / 2 ** 20, 1) if peak else None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('cases', nargs='+', choices=sorted(CASES))
    parser.add_argument('--oracle', action='store_true')
    parser.add_argument('--memory', action='store_true')
    args = parser.parse_args()
    for name in args.cases:
        if args.oracle:
            from wwcore_oracle import Oracle
            start = time.perf_counter()
            oracle = Oracle(CASES[name]()).evaluate()
            print(json.dumps({'case': name, 'oracle_seconds': round(time.perf_counter() - start, 3),
                              'oracle_village': str(oracle['village'])}), flush=True)
        else:
            try:
                print(json.dumps(measure(name, args.memory)), flush=True)
            except WorkLimitExceeded as error:
                print(json.dumps({'case': name, 'uncomputed': str(error)}), flush=True)


if __name__ == '__main__':
    main()
