INVALID_COOKIE_NAME_CHARS = set('()<>@,;:\\"/[]?={} \t\r\n')


def is_valid_cookie_name(name: str) -> bool:
    if not name or not isinstance(name, str):
        return False
    if any(ord(ch) < 33 or ord(ch) > 126 for ch in name):
        return False
    if any(ch in INVALID_COOKIE_NAME_CHARS for ch in name):
        return False
    return True


def sanitize_cookies(cookies: dict[object, object] | None) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for raw_key, raw_value in (cookies or {}).items():
        if not isinstance(raw_key, str):
            continue
        key = raw_key.strip()
        if not is_valid_cookie_name(key):
            continue
        sanitized[key] = "" if raw_value is None else str(raw_value).strip()
    return sanitized
