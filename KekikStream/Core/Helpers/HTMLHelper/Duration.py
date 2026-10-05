# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.


"""HTML duration işlemleri."""

import re

_RE_ISO_DURATION  = re.compile(
    r"^P(?:(?P<days>\d+(?:\.\d+)?)D)?(?:T(?:(?P<hours>\d+(?:\.\d+)?)H)?(?:(?P<minutes>\d+(?:\.\d+)?)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$",
    re.I,
)


def iso8601_duration_minutes(value: object) -> int | None:
    """ISO-8601 süre değerini dakika cinsine çevir (örn. ``PT1H32M`` -> 92)."""
    if not isinstance(value, str):
        return None
    match = _RE_ISO_DURATION.fullmatch(value.strip())
    if not match:
        return None

    parts = match.groupdict()
    if not any(parts.values()):
        return None

    total_seconds = (
        float(parts["days"] or 0) * 86_400
        + float(parts["hours"] or 0) * 3_600
        + float(parts["minutes"] or 0) * 60
        + float(parts["seconds"] or 0)
    )
    return int((total_seconds + 59) // 60)


def json_ld_duration_minutes(schema: object) -> int | None:
    """JSON-LD medya şemasındaki gerçek ``duration``/``timeRequired`` alanını oku."""
    if not isinstance(schema, dict):
        return None
    return iso8601_duration_minutes(schema.get("duration") or schema.get("timeRequired"))
