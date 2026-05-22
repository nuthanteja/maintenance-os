from enum import Enum


class Severity(str, Enum):
    BASELINE = "baseline"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IsoZone(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
