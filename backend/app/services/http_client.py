"""One pooled HTTP client for all upstream NASA requests.

Opening a new client per request repeats the DNS lookup and TLS handshake
every time. The map view makes dozens of NASA POWER calls in a row, so
connections are kept alive and reused instead.
"""
import httpx

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client

    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(90.0, connect=15.0),
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=60.0,
            ),
            headers={"User-Agent": "hulaw-backend/0.1"},
        )

    return _client


async def close_client() -> None:
    global _client

    if _client is not None and not _client.is_closed:
        await _client.aclose()

    _client = None
