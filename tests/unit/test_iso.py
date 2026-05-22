import pytest

from pmos.core.enums import IsoZone
from pmos.inference.iso import severity_to_zone


@pytest.mark.parametrize(
    "severity,expected",
    [
        ("baseline", IsoZone.A),
        ("LOW", IsoZone.B),
        (" Medium ", IsoZone.C),
        ("high", IsoZone.D),
    ],
)
def test_severity_to_zone(severity, expected):
    zone, label = severity_to_zone(severity)
    assert zone is expected
    assert label.startswith(f"Zone {expected.value}")


def test_severity_to_zone_unknown():
    with pytest.raises(ValueError):
        severity_to_zone("catastrophic")
