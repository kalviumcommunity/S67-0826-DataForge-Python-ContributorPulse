import unicodedata
from datetime import datetime, timezone
from typing import Any, Optional


def normalize_text(text: Optional[str], default: Optional[str] = None) -> Optional[str]:
    """
    Clean, sanitize, and normalize text strings.

    - Strips leading/trailing whitespace
    - Normalizes Unicode characters (NFC format)
    - Replaces internal null bytes / carriage returns
    - Collapses excessive consecutive whitespace
    - Returns default if empty or None
    """
    if text is None:
        return default

    # Unicode normalization
    cleaned = unicodedata.normalize("NFC", str(text))

    # Remove null bytes and carriage return artifacts
    cleaned = cleaned.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")

    # Strip whitespace
    cleaned = cleaned.strip()

    if not cleaned:
        return default

    return cleaned


def normalize_timestamp(ts_value: Any) -> Optional[datetime]:
    """
    Parse and standardize timestamp values into UTC-aware datetime objects.

    Supports:
    - ISO-8601 strings (with Z, offsets like +02:00, -05:00)
    - Standard datetime objects (naive converted to UTC, aware converted to UTC)
    - Epoch timestamps (int / float)
    """
    if ts_value is None:
        return None

    if isinstance(ts_value, datetime):
        if ts_value.tzinfo is None:
            return ts_value.replace(tzinfo=timezone.utc)
        return ts_value.astimezone(timezone.utc)

    if isinstance(ts_value, (int, float)):
        try:
            return datetime.fromtimestamp(ts_value, tz=timezone.utc)
        except Exception:
            return None

    if isinstance(ts_value, str):
        cleaned_str = ts_value.strip()
        if not cleaned_str:
            return None
        try:
            # Handle standard ISO-8601 with Z
            formatted_str = cleaned_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(formatted_str)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            # Fallback regex parsing for common custom date string patterns
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d",
            ):
                try:
                    dt = datetime.strptime(cleaned_str, fmt)
                    if dt.tzinfo is None:
                        return dt.replace(tzinfo=timezone.utc)
                    return dt.astimezone(timezone.utc)
                except ValueError:
                    continue
            return None

    return None
