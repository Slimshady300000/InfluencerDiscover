from base64 import b64decode
import secrets

from fastapi.responses import Response


def is_authorized_basic_header(
    authorization_header: str | None,
    access_username: str,
    access_password: str,
) -> bool:
    if not access_username or not access_password:
        return True
    if not authorization_header or not authorization_header.startswith("Basic "):
        return False

    encoded = authorization_header.removeprefix("Basic ").strip()
    try:
        decoded = b64decode(encoded, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False

    username, separator, password = decoded.partition(":")
    if not separator:
        return False
    return secrets.compare_digest(username, access_username) and secrets.compare_digest(
        password,
        access_password,
    )


def basic_auth_challenge() -> Response:
    return Response(
        content="Authentication required",
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="Influencer Discovery"'},
    )
