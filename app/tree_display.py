from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.tree_state import TreeNode


HeaderTone = Literal["day", "night"]


@dataclass
class TreeLayoutItem:
    row: int
    col: int
    probability_text: str
    result_text: str
    label: str
    tone: HeaderTone
    is_current: bool = False
    node_id: str = ""


@dataclass
class TreeColumnHeader:
    label: str
    tone: HeaderTone


@dataclass
class TreeLayout:
    items: list[TreeLayoutItem]
    column_headers: list[TreeColumnHeader]
    max_col: int
    max_row: int


LABEL_BREAKDOWN = "\u5185\u8a33"
LABEL_EXECUTED = "\u51e6\u5211"
LABEL_BITTEN = "\u8972\u6483"
LABEL_DAY = "\u663c"
LABEL_NIGHT = "\u591c"


def build_tree_layout(root: TreeNode | None, current_node_id: str = "", start_day: int = 1, start_phase_key: str = "day") -> TreeLayout | None:
    if root is None:
        return None

    items: list[TreeLayoutItem] = []
    next_row = 1

    def walk(node: TreeNode, col: int) -> int:
        nonlocal next_row
        current_row = next_row
        items.append(
            TreeLayoutItem(
                row=current_row,
                col=col,
                probability_text=node.probability_text,
                result_text=node.result_text,
                label=node.label,
                tone=_tone_for_col(start_phase_key, col),
                is_current=(node.node_id == current_node_id),
                node_id=node.node_id,
            )
        )

        if not node.children:
            next_row += 1
            return col

        max_col = col
        for child in node.children:
            max_col = max(max_col, walk(child, col + 1))
        return max_col

    max_col = walk(root, 1)
    max_row = max((item.row for item in items), default=1)
    items.sort(key=lambda item: (item.row, item.col))
    column_headers = [_build_column_header(start_day, start_phase_key, col) for col in range(1, max_col + 1)]
    return TreeLayout(items=items, column_headers=column_headers, max_col=max_col, max_row=max_row)


def _tone_for_col(start_phase_key: str, col: int) -> HeaderTone:
    phase_step = (col - 1) // 2
    phase_key = start_phase_key
    for _ in range(phase_step):
        phase_key = "night" if phase_key == "day" else "day"
    return "day" if phase_key == "day" else "night"


def _build_column_header(start_day: int, start_phase_key: str, col: int) -> TreeColumnHeader:
    phase_step = (col - 1) // 2
    phase_key = start_phase_key
    day = start_day
    for _ in range(phase_step):
        if phase_key == "day":
            phase_key = "night"
        else:
            phase_key = "day"
            day += 1

    action_label = LABEL_EXECUTED if phase_key == "day" else LABEL_BITTEN
    phase_label = LABEL_DAY if phase_key == "day" else LABEL_NIGHT
    tone: HeaderTone = "day" if phase_key == "day" else "night"
    if col % 2 == 0:
        return TreeColumnHeader(label=f"{LABEL_BREAKDOWN}({action_label})", tone=tone)
    return TreeColumnHeader(label=f"Day{day}/{phase_label}({action_label})", tone=tone)

