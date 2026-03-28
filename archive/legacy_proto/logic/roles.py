from enum import Enum

# 陣営と色の定義
class Camp(Enum):
    VILLAGER = "villager"
    WOLF = "wolf"
    MADMAN = "kyojin"

class Color(Enum):
    WHITE = "white"
    BLACK = "black"

# 基底役職テンプレート
class RoleTemplate:
    identifier: str
    char: str
    name: str
    camp: Camp
    seered_color: Color
    mediumed_color: Color
   
# 固有の役職
class Villager(RoleTemplate):
    identifier = "villager"
    char = "素"
    name = "素村"
    camp = Camp.VILLAGER
    seered_color = Color.WHITE
    mediumed_color = Color.WHITE

class Seer(RoleTemplate):
    identifier = "seer"
    char = "占"
    name = "占い師"
    camp = Camp.VILLAGER
    seered_color = Color.WHITE
    mediumed_color = Color.WHITE

class Medium(RoleTemplate):
    identifier = "medium"
    char = "霊"
    name = "霊能者"
    camp = Camp.VILLAGER
    seered_color = Color.WHITE
    mediumed_color = Color.WHITE

class Hunter(RoleTemplate):
    identifier = "hunter"
    char = "狩"
    name = "狩人"
    camp = Camp.VILLAGER
    seered_color = Color.WHITE
    mediumed_color = Color.WHITE

class Wolf(RoleTemplate):
    identifier = "wolf"
    char = "狼"
    name = "人狼"
    camp = Camp.WOLF
    seered_color = Color.BLACK
    mediumed_color = Color.BLACK

class Madman(RoleTemplate):
    identifier = "madman"
    char = "狂"
    name = "狂人"
    camp = Camp.WOLF
    seered_color = Color.WHITE
    mediumed_color = Color.WHITE
