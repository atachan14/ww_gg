"""TOP setup drafts and independent sample presets; never mutate a running Board."""
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
import re
from .exact import Rules

COUNT_KEYS = ("citizens", "mediums", "seers", "hunters", "wolves")
CAST_PRESETS = {
    "five_sample": {"label": "サンプル②", "values": dict(citizens=4, mediums=0, seers=0, hunters=0, wolves=1)},
    "seer_sample": {"label": "サンプル⓷", "values": dict(citizens=2, mediums=0, seers=1, hunters=0, wolves=2)},
}
RULE_PRESETS = {"sample": {"label": "サンプル", "values": {"allow_self_bite": False}}}


def setup_count(value):
    """Normalize a finite integer count; malformed values never become defaults."""
    if not isinstance(value, str) or len(value) > 64 or not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", value):
        raise ValueError("配役の人数は0〜9の整数で指定してください。")
    try:
        number = Decimal(value)
        if not number.is_finite() or number != number.to_integral_value() or not 0 <= number <= 9:
            raise ValueError
        return int(number)
    except (InvalidOperation, ValueError):
        raise ValueError("配役の人数は0〜9の整数で指定してください。") from None


def complete_rules(values):
    """Rules owns schema defaults. Add versioned legacy migration here if needed.

    Missing supported fields use Rules defaults; unknown or invalid values still
    fail. Presets are expanded here, never used to rewrite a saved Game.
    """
    return Rules(**values)


def preset_data():
    return {"cast": CAST_PRESETS, "rules": {
        key: {"label": preset["label"], "values": asdict(complete_rules(preset["values"]))}
        for key, preset in RULE_PRESETS.items()}}


@dataclass(frozen=True)
class GameConfig:
    citizens: int
    mediums: int
    seers: int
    hunters: int
    wolves: int
    rules: Rules

    @classmethod
    def default(cls):
        return cls(**CAST_PRESETS["five_sample"]["values"], rules=complete_rules(RULE_PRESETS["sample"]["values"]))

    @classmethod
    def from_game(cls, state):
        counts = {key: state.get(key, 1 if key == "wolves" else 0) for key in COUNT_KEYS if key != "citizens"}
        return cls(citizens=state["players"]-sum(counts.values()), **counts, rules=complete_rules(state["rules"]))

    def draft(self):
        return SetupDraft({key: str(getattr(self, key)) for key in COUNT_KEYS}, "1" if self.rules.allow_self_bite else "0",self.rules.initial_seer)


@dataclass(frozen=True)
class SetupDraft:
    counts: dict[str, str]
    allow_self_bite: str
    initial_seer: str = "random_white"

    @classmethod
    def from_form(cls, form):
        def raw(key, default):
            values = form.getlist(key)
            return " / ".join(values) if values else default
        counts = {key: raw(key, "1" if key == "wolves" else "0") for key in COUNT_KEYS}
        if "citizens" not in form:
            try:
                counts["citizens"] = str(setup_count(raw("players", ""))-sum(setup_count(counts[key]) for key in COUNT_KEYS if key != "citizens"))
            except ValueError:
                counts["citizens"] = ""
        return cls(counts, raw("allow_self_bite", "0"),raw("initial_seer","random_white"))

    @property
    def cast_preset(self):
        try:
            counts = {key: setup_count(value) for key, value in self.counts.items()}
        except ValueError:
            return "custom"
        return next((key for key, p in CAST_PRESETS.items() if counts == p["values"]), "custom")

    @property
    def rule_preset(self):
        if self.allow_self_bite not in ("0", "1") or self.initial_seer not in ("normal","random_white","none"):
            return "custom"
        values = asdict(complete_rules({"allow_self_bite": self.allow_self_bite == "1","initial_seer":self.initial_seer}))
        return next((key for key, p in preset_data()["rules"].items() if values == p["values"]), "custom")

    @property
    def summary(self):
        try:
            counts = {key: setup_count(value) for key, value in self.counts.items()}
            return {"village": sum(value for key, value in counts.items() if key != "wolves"), "wolves": counts["wolves"], "total": sum(counts.values())}
        except ValueError:
            return dict(village="—", wolves="—", total="—")
