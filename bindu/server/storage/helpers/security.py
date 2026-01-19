import re


def mask_database_url(url: str) -> str:
    try:
        if "://" in url and "@" in url:
            scheme, rest = url.split("://", 1)
            if "@" in rest:
                auth, host_part = rest.rsplit("@", 1)
                if ":" in auth:
                    user, _ = auth.split(":", 1)
                    return f"{scheme}://{user}:***@{host_part}"
        return url
    except Exception:
        return url


def sanitize_identifier(identifier: str) -> str:
    if not re.match(r'^[a-zA-Z0-9_]+$', identifier):
        raise ValueError(f"Invalid identifier: {identifier}. Must contain only alphanumeric characters and underscores.")
    return identifier
