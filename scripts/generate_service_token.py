"""Generate a secure random service token for X-Service-Token auth."""

import secrets


def generate_token(length: int = 48) -> str:
    """Generate a URL-safe random token."""
    return secrets.token_urlsafe(length)


if __name__ == "__main__":
    token = generate_token()
    print(f"Generated X-Service-Token ({len(token)} chars):")
    print(f"  {token}")
    print(f"\nAdd to .env:")
    print(f"  X_SERVICE_TOKEN={token}")
