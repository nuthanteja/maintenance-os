from ..core.enums import IsoZone, Severity


ISO_ZONE_BY_SEVERITY: dict[Severity, IsoZone] = {
    Severity.BASELINE: IsoZone.A,
    Severity.LOW: IsoZone.B,
    Severity.MEDIUM: IsoZone.C,
    Severity.HIGH: IsoZone.D,
}

ISO_ZONE_LABELS: dict[IsoZone, str] = {
    IsoZone.A: "Zone A (Good)",
    IsoZone.B: "Zone B (Acceptable)",
    IsoZone.C: "Zone C (Warning — Unsatisfactory)",
    IsoZone.D: "Zone D (Alert — Unacceptable)",
}


def severity_to_zone(severity: str) -> tuple[IsoZone, str]:
    sev = Severity(severity.strip().lower())
    zone = ISO_ZONE_BY_SEVERITY[sev]
    return zone, ISO_ZONE_LABELS[zone]
