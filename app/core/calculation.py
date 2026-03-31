from __future__ import annotations

from functools import lru_cache
from typing import Literal


Phase = Literal["day", "night"]
Winner = Literal["village", "wolf"]


def get_terminal_winner(white_count: int, wolf_count: int) -> Winner | None:
    if wolf_count <= 0:
        return "village"
    if white_count <= 0 or white_count <= wolf_count:
        return "wolf"
    return None


@lru_cache(maxsize=None)
def evaluate_count_state(white_count: int, wolf_count: int, phase: Phase) -> tuple[float, float]:
    winner = get_terminal_winner(white_count, wolf_count)
    if winner == "village":
        return 100.0, 0.0
    if winner == "wolf":
        return 0.0, 100.0

    if phase == "night":
        return evaluate_count_state(white_count - 1, wolf_count, "day")

    total_players = white_count + wolf_count
    wolf_hit_rate = wolf_count / total_players
    white_hit_rate = white_count / total_players
    white_after_hit, _ = evaluate_count_state(white_count, wolf_count - 1, "night")
    white_after_miss, _ = evaluate_count_state(white_count - 1, wolf_count, "night")
    white_win_rate = (wolf_hit_rate * white_after_hit) + (white_hit_rate * white_after_miss)
    black_win_rate = 100.0 - white_win_rate
    return round(white_win_rate, 1), round(black_win_rate, 1)
