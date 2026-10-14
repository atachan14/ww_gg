"""Owner-specific night records; no individual success notification."""
from dataclasses import dataclass


@dataclass(frozen=True,order=True)
class WolfAttack:
    night: int
    target: int

    def __post_init__(self):
        if any(type(x)is not int or x<1 for x in (self.night,self.target)):
            raise ValueError('Invalid private attack history')


def merge_night_records(records,known):
    """Merge validated owner evidence without removing unspecified records."""
    merged={record.night:record for record in records}
    merged.update({record.night:record for record in known})
    return tuple(merged[night] for night in sorted(merged))
