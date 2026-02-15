from datetime import datetime, timezone

MIN = datetime.min.replace(tzinfo=timezone.utc)
MAX = datetime.max.replace(tzinfo=timezone.utc)

def now() -> datetime:
    """

    Now UTC

    """
    return datetime.now(tz=timezone.utc)
